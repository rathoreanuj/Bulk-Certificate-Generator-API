"""
app/routers/verify.py - Public certificate verification endpoint.

Allows third parties or employers to verify the authenticity of an issued
certificate using the certificate UUID printed on the PDF or physical document.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CertificateStatus
from app.schemas import CertificateVerificationResponse
from app import services

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/verify", tags=["Certificate Verification"])


@router.get(
    "/{certificate_id}",
    response_model=CertificateVerificationResponse,
    summary="Verify an authentic certificate by ID",
    description=(
        "Public endpoint to verify the authenticity and issuance metadata of "
        "a certificate using the unique Certificate UUID."
    ),
)
def verify_certificate(
    certificate_id: str,
    db: Session = Depends(get_db),
) -> CertificateVerificationResponse:
    """Verify a certificate record against the central database."""
    record = services.get_certificate_by_id(db, certificate_id)

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate ID '{certificate_id}' not found in verification registry.",
        )

    is_valid = record.status == CertificateStatus.SUCCESS

    return CertificateVerificationResponse(
        valid=is_valid,
        certificate_id=record.id,
        recipient_name=record.recipient_name,
        course_name=record.course_name,
        event_name=record.job.event_name if record.job else "Unknown Event",
        issuer_name=record.job.issuer_name if record.job else "Unknown Issuer",
        issue_date=record.job.issue_date if record.job else "",
        status=record.status,
        created_at=record.created_at,
    )
