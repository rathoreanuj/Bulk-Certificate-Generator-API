"""
app/schemas.py - Pydantic models (schemas) for request/response validation.

Separated from ORM models to keep the API contract independent of the
database representation, allowing them to evolve separately.
"""
from datetime import date, datetime
from typing import List, Optional
import re

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models import CertificateStatus, JobStatus
from app.config import settings


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class RecipientIn(BaseModel):
    """Represents a single recipient in a certificate generation request."""

    recipient_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Full name of the certificate recipient",
        examples=["Alice Johnson"],
    )
    recipient_email: EmailStr = Field(
        ...,
        description="Email address of the recipient (used as a unique identifier)",
        examples=["alice@example.com"],
    )
    course_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Name of the course or achievement the certificate is for",
        examples=["Advanced Python Programming"],
    )

    @field_validator("recipient_name", "course_name", mode="before")
    @classmethod
    def sanitize_text(cls, v: str) -> str:
        """Strip leading/trailing whitespace and collapse internal newline/tabs."""
        if isinstance(v, str):
            cleaned = re.sub(r"[\r\n\t]+", " ", v.strip())
            return cleaned.strip()
        return v


class JobCreateRequest(BaseModel):
    """
    Request body for POST /jobs.

    Contains shared certificate metadata (event, issuer, date) that applies
    to all recipients, plus the list of recipients.
    """

    event_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Name of the event or program the certificates are for",
        examples=["TechConf 2024"],
    )
    issuer_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Name of the issuing organization",
        examples=["Aereo Academy"],
    )
    issue_date: date = Field(
        ...,
        description="Date the certificate is issued (ISO 8601 format: YYYY-MM-DD)",
        examples=["2024-11-15"],
    )
    recipients: List[RecipientIn] = Field(
        ...,
        min_length=1,
        max_length=settings.MAX_RECIPIENTS_PER_JOB,
        description="List of certificate recipients (at least one, capped at scalability limit)",
    )

    @field_validator("event_name", "issuer_name", mode="before")
    @classmethod
    def sanitize_text(cls, v: str) -> str:
        if isinstance(v, str):
            cleaned = re.sub(r"[\r\n\t]+", " ", v.strip())
            return cleaned.strip()
        return v


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class CertificateRecordOut(BaseModel):
    """Response schema for a single certificate record."""

    id: str
    job_id: str
    recipient_name: str
    recipient_email: str
    course_name: str
    status: CertificateStatus
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class JobStatusResponse(BaseModel):
    """Response schema for a job's current status and progress counters."""

    id: str
    event_name: str
    issuer_name: str
    issue_date: str
    status: JobStatus
    total_count: int
    success_count: int
    failed_count: int
    pending_count: int = Field(
        description="Number of certificates still awaiting generation"
    )
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class JobCreateResponse(BaseModel):
    """Response schema returned immediately after a job is accepted."""

    job_id: str
    status: JobStatus
    total_count: int
    message: str


class CertificateVerificationResponse(BaseModel):
    """Schema returned by public certificate verification lookup."""

    valid: bool = Field(..., description="Whether the certificate is authentic and successfully issued")
    certificate_id: str
    recipient_name: str
    course_name: str
    event_name: str
    issuer_name: str
    issue_date: str
    status: CertificateStatus
    created_at: datetime


class JobRetryResponse(BaseModel):
    """Response schema returned when retrying failed certificates in a job."""

    job_id: str
    retried_count: int
    message: str

