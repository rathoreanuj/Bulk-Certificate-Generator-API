"""
app/models.py - SQLAlchemy ORM models representing the database schema.

Two tables:
  - CertificateJob   : one row per bulk generation request
  - CertificateRecord: one row per individual recipient within a job

Performance & Scalability:
  - Explicit indexes on foreign keys, status enums, and timestamps.
  - Composite index on (job_id, status) for fast filtered pagination.
"""
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Integer, DateTime, Enum as SAEnum,
    ForeignKey, Text, Index
)
from sqlalchemy.orm import relationship

from app.database import Base


def _utcnow() -> datetime:
    """Return the current UTC datetime (timezone-aware)."""
    return datetime.now(timezone.utc)


class JobStatus(str, enum.Enum):
    """Lifecycle states for a bulk certificate generation job."""
    PENDING = "pending"       # Job created, generation not yet started
    PROCESSING = "processing" # Generation is actively running
    COMPLETED = "completed"   # All recipients processed (some may have failed)
    FAILED = "failed"         # Catastrophic failure before processing began


class CertificateStatus(str, enum.Enum):
    """Lifecycle states for a single certificate within a job."""
    PENDING = "pending"       # Queued, not yet generated
    SUCCESS = "success"       # PDF generated successfully
    FAILED = "failed"         # Generation failed for this recipient


class CertificateJob(Base):
    """
    Represents a single bulk certificate generation request.

    A job groups together all CertificateRecord rows that were submitted
    in one API call, making it easy to track overall progress.
    """
    __tablename__ = "certificate_jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    event_name = Column(String(255), nullable=False)
    issuer_name = Column(String(255), nullable=False)
    issue_date = Column(String(20), nullable=False)  # stored as ISO date string
    status = Column(
        SAEnum(JobStatus), nullable=False, default=JobStatus.PENDING, index=True
    )
    total_count = Column(Integer, nullable=False, default=0)
    success_count = Column(Integer, nullable=False, default=0)
    failed_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    # One job → many certificate records
    certificates = relationship(
        "CertificateRecord", back_populates="job", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<CertificateJob id={self.id} status={self.status}>"


class CertificateRecord(Base):
    """
    Represents a single certificate for one recipient within a job.

    Stores the recipient data, generation status, path to the generated PDF,
    and an error message if generation failed.
    """
    __tablename__ = "certificate_records"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String, ForeignKey("certificate_jobs.id"), nullable=False, index=True)

    # Recipient-specific data
    recipient_name = Column(String(255), nullable=False)
    recipient_email = Column(String(255), nullable=False)
    course_name = Column(String(255), nullable=False)

    status = Column(
        SAEnum(CertificateStatus), nullable=False, default=CertificateStatus.PENDING, index=True
    )
    file_path = Column(String(512), nullable=True)   # absolute path to the PDF
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    # Many records → one job
    job = relationship("CertificateJob", back_populates="certificates")

    __table_args__ = (
        Index("ix_cert_records_job_status", "job_id", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<CertificateRecord id={self.id} "
            f"recipient={self.recipient_name} status={self.status}>"
        )
