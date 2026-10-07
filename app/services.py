"""
app/services.py - Business logic layer between API routes and the database/generator.

Separating business logic from routes keeps route handlers thin and makes the
logic easier to unit-test without spinning up HTTP infrastructure.

Scalability notes:
  - Batch object persistence via add_all.
  - Idempotent and crash-resilient background processing.
  - Flexible query helpers supporting pagination and status filtering.
"""
import io
import logging
import zipfile
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.certificate_generator import generate_certificate, CertificateGenerationError
from app.config import settings
from app.database import SessionLocal  # module-level import so tests can patch it
from app.models import CertificateJob, CertificateRecord, CertificateStatus, JobStatus
from app.schemas import JobCreateRequest

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Job creation
# ---------------------------------------------------------------------------

def create_job(db: Session, payload: JobCreateRequest) -> CertificateJob:
    """
    Persist a new CertificateJob and all its CertificateRecord rows.

    Called synchronously in the route handler before background processing
    begins, so the client immediately receives a job_id to poll.
    """
    job = CertificateJob(
        event_name=payload.event_name,
        issuer_name=payload.issuer_name,
        issue_date=str(payload.issue_date),
        status=JobStatus.PENDING,
        total_count=len(payload.recipients),
    )
    db.add(job)
    db.flush()  # obtain job.id before creating child records

    records = [
        CertificateRecord(
            job_id=job.id,
            recipient_name=recipient.recipient_name,
            recipient_email=recipient.recipient_email,
            course_name=recipient.course_name,
            status=CertificateStatus.PENDING,
        )
        for recipient in payload.recipients
    ]
    db.add_all(records)
    db.commit()
    db.refresh(job)
    logger.info("Created job %s with %d recipients.", job.id, job.total_count)
    return job


# ---------------------------------------------------------------------------
# Background processing
# ---------------------------------------------------------------------------

def process_job(job_id: str) -> None:
    """
    Generate certificates for every PENDING record in the job.

    This function is called as a background task. It opens its own DB session
    so it is decoupled from the HTTP request context.

    Design notes:
    - Idempotency guard: skips records that are not PENDING.
    - Each record generation result is committed individually so partial success
      is preserved even if the process is interrupted.
    - Captures errors per-record and stores error_message without stopping the batch.
    """
    db: Session = SessionLocal()
    try:
        job: CertificateJob | None = db.get(CertificateJob, job_id)
        if job is None:
            logger.error("process_job: job %s not found.", job_id)
            return

        # Skip if job is already finished
        if job.status in (JobStatus.COMPLETED, JobStatus.FAILED):
            logger.info("process_job: job %s already in terminal state %s.", job_id, job.status)
            return

        # Transition to PROCESSING
        job.status = JobStatus.PROCESSING
        db.commit()
        logger.info("Job %s: started processing %d certificates.", job_id, job.total_count)

        output_dir: Path = settings.get_certificates_path()

        for record in job.certificates:
            if record.status != CertificateStatus.PENDING:
                continue  # skip already-processed records

            try:
                file_path = generate_certificate(
                    record_id=record.id,
                    recipient_name=record.recipient_name,
                    recipient_email=record.recipient_email,
                    course_name=record.course_name,
                    event_name=job.event_name,
                    issuer_name=job.issuer_name,
                    issue_date=job.issue_date,
                    output_dir=output_dir,
                )
                record.status = CertificateStatus.SUCCESS
                record.file_path = file_path
                job.success_count += 1
                logger.debug(
                    "Job %s: certificate generated for %s → %s",
                    job_id,
                    record.recipient_name,
                    file_path,
                )

            except CertificateGenerationError as exc:
                record.status = CertificateStatus.FAILED
                record.error_message = str(exc)
                job.failed_count += 1
                logger.warning(
                    "Job %s: certificate FAILED for %s: %s",
                    job_id,
                    record.recipient_name,
                    exc,
                )

            db.commit()  # commit progress incrementally

        job.status = JobStatus.COMPLETED
        db.commit()
        logger.info(
            "Job %s: COMPLETED — success=%d failed=%d",
            job_id,
            job.success_count,
            job.failed_count,
        )

    except Exception as exc:
        logger.exception("Job %s: unexpected error during processing: %s", job_id, exc)
        try:
            job = db.get(CertificateJob, job_id)
            if job and job.status != JobStatus.COMPLETED:
                job.status = JobStatus.FAILED
                db.commit()
        except Exception:
            pass  # best-effort status update
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

def get_job(db: Session, job_id: str) -> CertificateJob | None:
    """Return the CertificateJob with the given ID, or None if not found."""
    return db.get(CertificateJob, job_id)


def get_certificates_for_job(
    db: Session,
    job_id: str,
    status_filter: Optional[CertificateStatus] = None,
    limit: Optional[int] = None,
    offset: int = 0,
) -> list[CertificateRecord]:
    """
    Return CertificateRecord rows for a given job.

    Supports optional status filtering and pagination for high scalability.
    """
    query = (
        db.query(CertificateRecord)
        .filter(CertificateRecord.job_id == job_id)
    )

    if status_filter is not None:
        query = query.filter(CertificateRecord.status == status_filter)

    query = query.order_by(CertificateRecord.created_at)

    if offset > 0:
        query = query.offset(offset)

    if limit is not None:
        query = query.limit(limit)

    return query.all()


def get_certificate_record(
    db: Session, job_id: str, certificate_id: str
) -> CertificateRecord | None:
    """Return a specific CertificateRecord belonging to a job, or None."""
    return (
        db.query(CertificateRecord)
        .filter(
            CertificateRecord.id == certificate_id,
            CertificateRecord.job_id == job_id,
        )
        .first()
    )


def get_certificate_by_id(db: Session, certificate_id: str) -> CertificateRecord | None:
    """Return a CertificateRecord by its primary key ID across any job."""
    return db.get(CertificateRecord, certificate_id)


def retry_failed_job(db: Session, job_id: str) -> int:
    """
    Reset all FAILED records in a job to PENDING so they can be regenerated.
    Returns the count of reset records.
    """
    job = db.get(CertificateJob, job_id)
    if not job:
        return 0

    failed_records = (
        db.query(CertificateRecord)
        .filter(
            CertificateRecord.job_id == job_id,
            CertificateRecord.status == CertificateStatus.FAILED,
        )
        .all()
    )

    if not failed_records:
        return 0

    for record in failed_records:
        record.status = CertificateStatus.PENDING
        record.error_message = None

    job.failed_count = max(0, job.failed_count - len(failed_records))
    job.status = JobStatus.PENDING
    db.commit()
    logger.info("Job %s: reset %d failed records for retry.", job_id, len(failed_records))
    return len(failed_records)


def create_job_zip_archive(db: Session, job: CertificateJob) -> io.BytesIO:
    """
    Package all completed certificate PDFs for a job into an in-memory ZIP archive.
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for record in job.certificates:
            if record.status == CertificateStatus.SUCCESS and record.file_path:
                pdf_path = Path(record.file_path)
                if pdf_path.exists() and pdf_path.is_file():
                    safe_name = "".join(
                        c for c in record.recipient_name if c.isalnum() or c in (" ", "_", "-")
                    ).strip()
                    safe_name = safe_name.replace(" ", "_") or "recipient"
                    archive_filename = f"{safe_name}_{record.id[:8]}.pdf"
                    zip_file.write(pdf_path, arcname=archive_filename)
    buffer.seek(0)
    return buffer

