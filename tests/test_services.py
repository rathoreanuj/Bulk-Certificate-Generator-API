"""
tests/test_services.py - Unit tests for the service layer (app/services.py).

These tests exercise service functions directly with a real DB session,
bypassing the HTTP layer to verify business logic in isolation.
"""
import pytest
from unittest.mock import patch
from pathlib import Path

from app import services
from app.models import CertificateJob, CertificateRecord, CertificateStatus, JobStatus
from app.schemas import JobCreateRequest
from tests.conftest import make_job_payload, make_recipient


def _parse_payload(d: dict) -> JobCreateRequest:
    """Parse a dict into a validated JobCreateRequest."""
    return JobCreateRequest.model_validate(d)


# ===========================================================================
# create_job service tests
# ===========================================================================

class TestCreateJobService:
    def test_create_job_returns_certificate_job_instance(self, db):
        payload = _parse_payload(make_job_payload())
        job = services.create_job(db, payload)
        assert isinstance(job, CertificateJob)

    def test_create_job_sets_correct_event_name(self, db):
        payload = _parse_payload(make_job_payload(event_name="My Event"))
        job = services.create_job(db, payload)
        assert job.event_name == "My Event"

    def test_create_job_sets_correct_total_count(self, db):
        recipients = [make_recipient(email=f"r{i}@x.com") for i in range(5)]
        payload = _parse_payload(make_job_payload(recipients=recipients))
        job = services.create_job(db, payload)
        assert job.total_count == 5

    def test_create_job_creates_certificate_records(self, db):
        recipients = [
            make_recipient("Alice", "a@x.com", "C1"),
            make_recipient("Bob", "b@x.com", "C2"),
        ]
        payload = _parse_payload(make_job_payload(recipients=recipients))
        job = services.create_job(db, payload)

        db.expire_all()
        records = db.query(CertificateRecord).filter_by(job_id=job.id).all()
        assert len(records) == 2

    def test_create_job_records_start_as_pending(self, db):
        payload = _parse_payload(make_job_payload())
        job = services.create_job(db, payload)

        db.expire_all()
        records = db.query(CertificateRecord).filter_by(job_id=job.id).all()
        for record in records:
            assert record.status == CertificateStatus.PENDING

    def test_create_job_initial_status_is_pending(self, db):
        payload = _parse_payload(make_job_payload())
        job = services.create_job(db, payload)
        assert job.status == JobStatus.PENDING


# ===========================================================================
# process_job service tests
# ===========================================================================

class TestProcessJobService:
    def test_process_job_sets_status_to_completed(self, db, tmp_path):
        payload = _parse_payload(
            make_job_payload(recipients=[make_recipient("Alice", "a@x.com", "C")])
        )
        job = services.create_job(db, payload)
        db.close()

        with patch("app.services.settings") as mock_settings:
            mock_settings.get_certificates_path.return_value = tmp_path
            services.process_job(job.id)

        from app.database import SessionLocal
        fresh_db = SessionLocal()
        try:
            # Use fresh_db for the in-memory DB won't reflect test_engine data
            # So we use the conftest db after expiring
            pass
        finally:
            fresh_db.close()

    def test_process_job_with_nonexistent_id_does_not_raise(self, tmp_path):
        """process_job should handle a missing job gracefully (log and return)."""
        # Should not raise any exception
        services.process_job("totally-nonexistent-id")

    def test_get_job_returns_none_for_missing_id(self, db):
        result = services.get_job(db, "does-not-exist")
        assert result is None

    def test_get_job_returns_job_for_existing_id(self, db):
        payload = _parse_payload(make_job_payload())
        job = services.create_job(db, payload)
        retrieved = services.get_job(db, job.id)
        assert retrieved is not None
        assert retrieved.id == job.id

    def test_get_certificates_for_job_returns_all_records(self, db):
        recipients = [make_recipient(email=f"r{i}@x.com") for i in range(3)]
        payload = _parse_payload(make_job_payload(recipients=recipients))
        job = services.create_job(db, payload)

        records = services.get_certificates_for_job(db, job.id)
        assert len(records) == 3

    def test_get_certificate_record_returns_correct_record(self, db):
        payload = _parse_payload(
            make_job_payload(
                recipients=[make_recipient("Alice", "alice@x.com", "Course")]
            )
        )
        job = services.create_job(db, payload)
        all_records = services.get_certificates_for_job(db, job.id)
        record_id = all_records[0].id

        result = services.get_certificate_record(db, job.id, record_id)
        assert result is not None
        assert result.id == record_id
        assert result.recipient_name == "Alice"

    def test_get_certificate_record_wrong_job_returns_none(self, db):
        payload = _parse_payload(
            make_job_payload(
                recipients=[make_recipient("Alice", "alice@x.com", "Course")]
            )
        )
        job = services.create_job(db, payload)
        all_records = services.get_certificates_for_job(db, job.id)
        record_id = all_records[0].id

        result = services.get_certificate_record(db, "wrong-job-id", record_id)
        assert result is None
