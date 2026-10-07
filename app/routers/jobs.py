"""
app/routers/jobs.py - API endpoints for certificate generation jobs.

Endpoints:
  POST   /jobs                             → Create a new bulk generation job
  GET    /jobs/{job_id}                    → Get job status and progress
  GET    /jobs/{job_id}/certificates       → List all certificates in a job (supports pagination & status filter)
  GET    /jobs/{job_id}/certificates/{id}  → Get a single certificate record
  GET    /jobs/{job_id}/certificates/{id}/download  → Download the PDF file (path traversal protected)
"""
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CertificateStatus, JobStatus
from app.config import settings
from app.schemas import (
    CertificateRecordOut,
    JobCreateRequest,
    JobCreateResponse,
    JobRetryResponse,
    JobStatusResponse,
)
from app import services

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["Certificate Jobs"])


@router.post(
    "",
    response_model=JobCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create a bulk certificate generation job",
    description=(
        "Submit a list of recipients for certificate generation. "
        "The job is accepted immediately (HTTP 202) and certificates are "
        "generated asynchronously in the background. "
        "Use GET /jobs/{job_id} to poll the job status."
    ),
)
def create_job(
    payload: JobCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> JobCreateResponse:
    """
    Accept a bulk certificate generation request.

    1. Validates the request body against constraints.
    2. Persists the job and recipient records to the database in a batch.
    3. Enqueues the generation task as a FastAPI BackgroundTask.
    4. Returns HTTP 202 Accepted immediately with job_id for polling.
    """
    job = services.create_job(db, payload)
    background_tasks.add_task(services.process_job, job.id)
    logger.info("Accepted job %s → enqueued background processing.", job.id)

    return JobCreateResponse(
        job_id=job.id,
        status=job.status,
        total_count=job.total_count,
        message=(
            f"Job accepted. {job.total_count} certificate(s) will be generated. "
            f"Poll GET /jobs/{job.id} for progress."
        ),
    )


@router.get(
    "/{job_id}",
    response_model=JobStatusResponse,
    summary="Get job status and progress",
    description="Returns the current status, progress counters, and metadata for a job.",
)
def get_job_status(
    job_id: str,
    db: Session = Depends(get_db),
) -> JobStatusResponse:
    """Return current status and counters for the specified job."""
    job = services.get_job(db, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found.",
        )

    pending_count = job.total_count - job.success_count - job.failed_count

    return JobStatusResponse(
        id=job.id,
        event_name=job.event_name,
        issuer_name=job.issuer_name,
        issue_date=job.issue_date,
        status=job.status,
        total_count=job.total_count,
        success_count=job.success_count,
        failed_count=job.failed_count,
        pending_count=pending_count,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.get(
    "/{job_id}/certificates",
    response_model=list[CertificateRecordOut],
    summary="List certificate records for a job",
    description=(
        "Returns certificate records associated with the job. "
        "Supports optional status filtering (success, pending, failed) and "
        "pagination via limit and offset parameters."
    ),
)
def list_certificates(
    job_id: str,
    certificate_status: Optional[CertificateStatus] = Query(
        None,
        alias="status",
        description="Filter records by generation status (success, pending, failed)",
    ),
    limit: Optional[int] = Query(
        None,
        ge=1,
        le=settings.MAX_PAGE_SIZE,
        description="Max number of records to return",
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Number of records to skip for pagination",
    ),
    db: Session = Depends(get_db),
) -> list[CertificateRecordOut]:
    """List certificate records with optional status filtering and pagination."""
    job = services.get_job(db, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found.",
        )
    return services.get_certificates_for_job(  # type: ignore[return-value]
        db,
        job_id,
        status_filter=certificate_status,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{job_id}/certificates/{certificate_id}",
    response_model=CertificateRecordOut,
    summary="Get a single certificate record",
    description="Returns the status and metadata for one certificate within a job.",
)
def get_certificate(
    job_id: str,
    certificate_id: str,
    db: Session = Depends(get_db),
) -> CertificateRecordOut:
    """Return a single certificate record by job_id and certificate_id."""
    record = services.get_certificate_record(db, job_id, certificate_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate '{certificate_id}' not found in job '{job_id}'.",
        )
    return record  # type: ignore[return-value]


@router.get(
    "/{job_id}/certificates/{certificate_id}/download",
    summary="Download a generated certificate PDF",
    description=(
        "Streams the generated PDF file for a successfully completed certificate. "
        "Returns HTTP 404 if the certificate does not exist, and HTTP 409 if it "
        "has not yet been generated successfully. Includes path traversal security."
    ),
    response_class=FileResponse,
)
def download_certificate(
    job_id: str,
    certificate_id: str,
    db: Session = Depends(get_db),
) -> FileResponse:
    """
    Stream the PDF file for a successfully generated certificate.

    Returns HTTP 409 (Conflict) instead of 404 when the certificate exists
    but is still pending or failed, giving the client an actionable error.
    """
    record = services.get_certificate_record(db, job_id, certificate_id)

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate '{certificate_id}' not found in job '{job_id}'.",
        )

    if record.status != CertificateStatus.SUCCESS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Certificate is not available for download "
                f"(current status: '{record.status.value}'). "
                + (f"Error: {record.error_message}" if record.error_message else "")
            ),
        )

    file_path = Path(record.file_path).resolve()

    # Integrity & Path Traversal Guards:
    # 1. Filename must strictly match the certificate record's UUID .pdf format
    # 2. Must not contain suspicious directory traversal components
    expected_filename = f"{record.id}.pdf"
    if file_path.name != expected_filename or file_path.suffix.lower() != ".pdf":
        logger.warning("Invalid certificate file target detected: %s", file_path)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to the requested file path is forbidden.",
        )

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate file not found on disk. It may have been deleted.",
        )

    safe_name = "".join(c for c in record.recipient_name if c.isalnum() or c in (" ", "_", "-")).strip()
    safe_name = safe_name.replace(" ", "_") or "recipient"
    filename = f"certificate_{safe_name}.pdf"

    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=filename,
    )


@router.get(
    "/{job_id}/download-zip",
    summary="Download all completed certificates as a ZIP archive",
    description="Streams an in-memory ZIP archive containing all successfully generated certificates for the job.",
)
@router.get(
    "/{job_id}/download-all",
    summary="Download all completed certificates as a ZIP archive (alias)",
    include_in_schema=False,
)
def download_job_zip(
    job_id: str,
    db: Session = Depends(get_db),
) -> Response:
    """Package and stream all completed certificate PDFs for a job into a ZIP archive."""
    job = services.get_job(db, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found.",
        )

    if job.success_count == 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No completed certificates available to package into ZIP archive yet.",
        )

    zip_buffer = services.create_job_zip_archive(db, job)
    safe_event = "".join(
        c for c in job.event_name if c.isalnum() or c in (" ", "_", "-")
    ).strip().replace(" ", "_") or "certificates"
    zip_filename = f"{safe_event}_{job.id[:8]}.zip"

    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_filename}"'},
    )


@router.post(
    "/{job_id}/retry",
    response_model=JobRetryResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Retry failed certificates in a job",
    description=(
        "Resets all failed certificates in the specified job to pending status "
        "and enqueues background processing to regenerate them."
    ),
)
def retry_failed_certificates(
    job_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> JobRetryResponse:
    """Find and re-queue all failed certificates for a job."""
    job = services.get_job(db, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found.",
        )

    retried_count = services.retry_failed_job(db, job_id)
    if retried_count == 0:
        return JobRetryResponse(
            job_id=job.id,
            retried_count=0,
            message="No failed certificates found in this job to retry.",
        )

    background_tasks.add_task(services.process_job, job.id)
    logger.info("Enqueued retry for %d failed certificate(s) in job %s.", retried_count, job.id)

    return JobRetryResponse(
        job_id=job.id,
        retried_count=retried_count,
        message=f"Queued retry for {retried_count} previously failed certificate(s).",
    )

