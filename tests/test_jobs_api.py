"""
tests/test_jobs_api.py - Integration tests for the certificate job API endpoints.

These tests exercise the full HTTP stack: routing, validation, service layer,
and database persistence. A TestClient + in-memory SQLite DB is used so that:
  - Tests do not depend on external services.
  - Each test starts with a clean database (see conftest.py).
  - Background tasks are executed synchronously by TestClient.

Covered scenarios:
  1.  Creating a generation job (happy path)
  2.  Input validation (missing fields, invalid email, empty recipients)
  3.  Job status / progress polling
  4.  Listing certificates within a job
  5.  Retrieving a single certificate record
  6.  Handling an individual certificate failure
  7.  Downloading a generated certificate PDF
  8.  404 responses for non-existent resources
"""
import io
import os
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from tests.conftest import VALID_JOB_PAYLOAD, make_job_payload, make_recipient
from app.models import CertificateStatus, JobStatus


# ===========================================================================
# 1. Creating a generation job
# ===========================================================================

class TestCreateJob:
    def test_create_job_returns_202(self, client, tmp_path):
        """POST /jobs should return HTTP 202 Accepted."""
        with patch("app.services.settings") as mock_settings:
            mock_settings.get_certificates_path.return_value = tmp_path
            response = client.post("/api/v1/jobs", json=VALID_JOB_PAYLOAD)

        assert response.status_code == 202

    def test_create_job_response_contains_job_id(self, client, tmp_path):
        """Response body should contain a non-empty job_id."""
        with patch("app.services.settings") as mock_settings:
            mock_settings.get_certificates_path.return_value = tmp_path
            response = client.post("/api/v1/jobs", json=VALID_JOB_PAYLOAD)

        data = response.json()
        assert "job_id" in data
        assert len(data["job_id"]) > 0

    def test_create_job_response_total_count_matches_recipients(self, client, tmp_path):
        """The total_count in the response should equal the number of recipients."""
        with patch("app.services.settings") as mock_settings:
            mock_settings.get_certificates_path.return_value = tmp_path
            response = client.post("/api/v1/jobs", json=VALID_JOB_PAYLOAD)

        data = response.json()
        assert data["total_count"] == len(VALID_JOB_PAYLOAD["recipients"])

    def test_create_job_initial_status_is_pending_or_processing(self, client, tmp_path):
        """
        The job status immediately after creation should be PENDING or PROCESSING
        (TestClient may execute background tasks synchronously, so COMPLETED is
        also acceptable in the immediate response).
        """
        with patch("app.services.settings") as mock_settings:
            mock_settings.get_certificates_path.return_value = tmp_path
            response = client.post("/api/v1/jobs", json=VALID_JOB_PAYLOAD)

        data = response.json()
        # The response captures the status at the moment of acceptance (PENDING).
        assert data["status"] in [
            JobStatus.PENDING.value,
            JobStatus.PROCESSING.value,
            JobStatus.COMPLETED.value,
        ]

    def test_create_job_persists_to_database(self, client, db, tmp_path):
        """After creation, the job should be retrievable from the database."""
        from app.models import CertificateJob

        with patch("app.services.settings") as mock_settings:
            mock_settings.get_certificates_path.return_value = tmp_path
            response = client.post("/api/v1/jobs", json=VALID_JOB_PAYLOAD)

        job_id = response.json()["job_id"]
        db.expire_all()
        job = db.get(CertificateJob, job_id)
        assert job is not None
        assert job.event_name == VALID_JOB_PAYLOAD["event_name"]


# ===========================================================================
# 2. Input validation
# ===========================================================================

class TestInputValidation:
    def test_missing_event_name_returns_422(self, client):
        """event_name is required; omitting it should return HTTP 422."""
        payload = make_job_payload()
        del payload["event_name"]
        response = client.post("/api/v1/jobs", json=payload)
        assert response.status_code == 422

    def test_missing_issuer_name_returns_422(self, client):
        payload = make_job_payload()
        del payload["issuer_name"]
        response = client.post("/api/v1/jobs", json=payload)
        assert response.status_code == 422

    def test_missing_issue_date_returns_422(self, client):
        payload = make_job_payload()
        del payload["issue_date"]
        response = client.post("/api/v1/jobs", json=payload)
        assert response.status_code == 422

    def test_invalid_date_format_returns_422(self, client):
        """issue_date must be a valid date; a nonsense string should fail."""
        payload = make_job_payload(issue_date="not-a-date")
        response = client.post("/api/v1/jobs", json=payload)
        assert response.status_code == 422

    def test_empty_recipients_list_returns_422(self, client):
        """At least one recipient is required."""
        payload = make_job_payload(recipients=[])
        response = client.post("/api/v1/jobs", json=payload)
        assert response.status_code == 422

    def test_missing_recipients_field_returns_422(self, client):
        payload = make_job_payload()
        del payload["recipients"]
        response = client.post("/api/v1/jobs", json=payload)
        assert response.status_code == 422

    def test_invalid_recipient_email_returns_422(self, client):
        """recipient_email must be a valid email address."""
        payload = make_job_payload(
            recipients=[make_recipient(email="not-an-email")]
        )
        response = client.post("/api/v1/jobs", json=payload)
        assert response.status_code == 422

    def test_empty_recipient_name_returns_422(self, client):
        """recipient_name cannot be an empty string."""
        payload = make_job_payload(
            recipients=[make_recipient(name="")]
        )
        response = client.post("/api/v1/jobs", json=payload)
        assert response.status_code == 422

    def test_whitespace_only_recipient_name_returns_422(self, client):
        """A name that is only whitespace should fail after stripping."""
        payload = make_job_payload(
            recipients=[make_recipient(name="   ")]
        )
        response = client.post("/api/v1/jobs", json=payload)
        assert response.status_code == 422

    def test_empty_course_name_returns_422(self, client):
        payload = make_job_payload(
            recipients=[make_recipient(course="")]
        )
        response = client.post("/api/v1/jobs", json=payload)
        assert response.status_code == 422

    def test_missing_recipient_name_returns_422(self, client):
        payload = make_job_payload(
            recipients=[{"recipient_email": "a@b.com", "course_name": "X"}]
        )
        response = client.post("/api/v1/jobs", json=payload)
        assert response.status_code == 422

    def test_missing_recipient_email_returns_422(self, client):
        payload = make_job_payload(
            recipients=[{"recipient_name": "Alice", "course_name": "X"}]
        )
        response = client.post("/api/v1/jobs", json=payload)
        assert response.status_code == 422

    def test_empty_event_name_returns_422(self, client):
        payload = make_job_payload(event_name="")
        response = client.post("/api/v1/jobs", json=payload)
        assert response.status_code == 422


# ===========================================================================
# 3. Job status / progress
# ===========================================================================

class TestJobStatus:
    def test_get_job_status_returns_200(self, client, tmp_path):
        """GET /jobs/{job_id} should return 200 for an existing job."""
        with patch("app.services.settings") as mock_settings:
            mock_settings.get_certificates_path.return_value = tmp_path
            create_resp = client.post("/api/v1/jobs", json=VALID_JOB_PAYLOAD)

        job_id = create_resp.json()["job_id"]
        status_resp = client.get(f"/api/v1/jobs/{job_id}")
        assert status_resp.status_code == 200

    def test_get_job_status_contains_all_required_fields(self, client, tmp_path):
        """The status response should include all expected fields."""
        with patch("app.services.settings") as mock_settings:
            mock_settings.get_certificates_path.return_value = tmp_path
            create_resp = client.post("/api/v1/jobs", json=VALID_JOB_PAYLOAD)

        job_id = create_resp.json()["job_id"]
        data = client.get(f"/api/v1/jobs/{job_id}").json()

        for field in ["id", "event_name", "issuer_name", "issue_date",
                      "status", "total_count", "success_count",
                      "failed_count", "pending_count"]:
            assert field in data, f"Field '{field}' missing from status response."

    def test_get_job_status_counters_add_up(self, client, tmp_path):
        """success + failed + pending should equal total_count."""
        with patch("app.services.settings") as mock_settings:
            mock_settings.get_certificates_path.return_value = tmp_path
            create_resp = client.post("/api/v1/jobs", json=VALID_JOB_PAYLOAD)

        job_id = create_resp.json()["job_id"]
        data = client.get(f"/api/v1/jobs/{job_id}").json()

        assert (
            data["success_count"] + data["failed_count"] + data["pending_count"]
            == data["total_count"]
        )

    def test_get_job_status_completed_after_processing(self, client, tmp_path):
        """
        After the background task runs (TestClient runs it synchronously),
        the job status should be COMPLETED.
        """
        with patch("app.services.settings") as mock_settings:
            mock_settings.get_certificates_path.return_value = tmp_path
            create_resp = client.post("/api/v1/jobs", json=VALID_JOB_PAYLOAD)

        job_id = create_resp.json()["job_id"]
        data = client.get(f"/api/v1/jobs/{job_id}").json()
        assert data["status"] == JobStatus.COMPLETED.value

    def test_get_nonexistent_job_returns_404(self, client):
        """GET /jobs/{job_id} for an unknown ID should return 404."""
        response = client.get("/api/v1/jobs/nonexistent-job-id")
        assert response.status_code == 404


# ===========================================================================
# 4. Listing certificates within a job
# ===========================================================================

class TestListCertificates:
    def test_list_certificates_returns_200(self, client, tmp_path):
        with patch("app.services.settings") as mock_settings:
            mock_settings.get_certificates_path.return_value = tmp_path
            create_resp = client.post("/api/v1/jobs", json=VALID_JOB_PAYLOAD)

        job_id = create_resp.json()["job_id"]
        response = client.get(f"/api/v1/jobs/{job_id}/certificates")
        assert response.status_code == 200

    def test_list_certificates_count_matches_recipients(self, client, tmp_path):
        """Number of certificate records should equal the number of recipients."""
        with patch("app.services.settings") as mock_settings:
            mock_settings.get_certificates_path.return_value = tmp_path
            create_resp = client.post("/api/v1/jobs", json=VALID_JOB_PAYLOAD)

        job_id = create_resp.json()["job_id"]
        records = client.get(f"/api/v1/jobs/{job_id}/certificates").json()
        assert len(records) == len(VALID_JOB_PAYLOAD["recipients"])

    def test_list_certificates_returns_correct_recipient_names(self, client, tmp_path):
        """The returned records should contain the submitted recipient names."""
        with patch("app.services.settings") as mock_settings:
            mock_settings.get_certificates_path.return_value = tmp_path
            create_resp = client.post("/api/v1/jobs", json=VALID_JOB_PAYLOAD)

        job_id = create_resp.json()["job_id"]
        records = client.get(f"/api/v1/jobs/{job_id}/certificates").json()

        expected_names = {r["recipient_name"] for r in VALID_JOB_PAYLOAD["recipients"]}
        returned_names = {r["recipient_name"] for r in records}
        assert expected_names == returned_names

    def test_list_certificates_for_nonexistent_job_returns_404(self, client):
        response = client.get("/api/v1/jobs/bad-job-id/certificates")
        assert response.status_code == 404


# ===========================================================================
# 5. Retrieving a single certificate record
# ===========================================================================

class TestGetCertificate:
    def _get_first_certificate_id(self, client, tmp_path) -> tuple[str, str]:
        """Helper: create a job and return (job_id, first_certificate_id)."""
        with patch("app.services.settings") as mock_settings:
            mock_settings.get_certificates_path.return_value = tmp_path
            create_resp = client.post("/api/v1/jobs", json=VALID_JOB_PAYLOAD)

        job_id = create_resp.json()["job_id"]
        records = client.get(f"/api/v1/jobs/{job_id}/certificates").json()
        return job_id, records[0]["id"]

    def test_get_certificate_returns_200(self, client, tmp_path):
        job_id, cert_id = self._get_first_certificate_id(client, tmp_path)
        response = client.get(f"/api/v1/jobs/{job_id}/certificates/{cert_id}")
        assert response.status_code == 200

    def test_get_certificate_contains_expected_fields(self, client, tmp_path):
        job_id, cert_id = self._get_first_certificate_id(client, tmp_path)
        data = client.get(f"/api/v1/jobs/{job_id}/certificates/{cert_id}").json()

        for field in ["id", "job_id", "recipient_name", "recipient_email",
                      "course_name", "status"]:
            assert field in data, f"Field '{field}' missing from certificate response."

    def test_get_certificate_wrong_job_returns_404(self, client, tmp_path):
        """A certificate queried against the wrong job_id should return 404."""
        job_id, cert_id = self._get_first_certificate_id(client, tmp_path)
        response = client.get(f"/api/v1/jobs/wrong-job-id/certificates/{cert_id}")
        assert response.status_code == 404

    def test_get_nonexistent_certificate_returns_404(self, client, tmp_path):
        with patch("app.services.settings") as mock_settings:
            mock_settings.get_certificates_path.return_value = tmp_path
            create_resp = client.post("/api/v1/jobs", json=VALID_JOB_PAYLOAD)

        job_id = create_resp.json()["job_id"]
        response = client.get(f"/api/v1/jobs/{job_id}/certificates/no-such-id")
        assert response.status_code == 404


# ===========================================================================
# 6. Handling an individual certificate failure
# ===========================================================================

class TestCertificateFailure:
    def test_individual_failure_does_not_block_other_certificates(
        self, client, tmp_path
    ):
        """
        When one recipient's certificate generation fails, the others should
        still be generated successfully. The job should still reach COMPLETED.
        """
        recipients = [
            make_recipient("Alice", "alice@example.com", "Python 101"),
            make_recipient("FAIL_ME", "fail@example.com", "Will Fail"),
            make_recipient("Bob", "bob@example.com", "Java 101"),
        ]
        payload = make_job_payload(recipients=recipients)

        original_generate = __import__(
            "app.certificate_generator", fromlist=["generate_certificate"]
        ).generate_certificate

        def patched_generate(**kwargs):
            if kwargs["recipient_name"] == "FAIL_ME":
                from app.certificate_generator import CertificateGenerationError
                raise CertificateGenerationError("Simulated failure for FAIL_ME")
            return original_generate(**kwargs)

        with patch("app.services.generate_certificate", side_effect=patched_generate):
            with patch("app.services.settings") as mock_settings:
                mock_settings.get_certificates_path.return_value = tmp_path
                create_resp = client.post("/api/v1/jobs", json=payload)

        job_id = create_resp.json()["job_id"]

        # Re-fetch job status
        status_data = client.get(f"/api/v1/jobs/{job_id}").json()
        assert status_data["status"] == JobStatus.COMPLETED.value
        assert status_data["success_count"] == 2, "Alice and Bob should succeed."
        assert status_data["failed_count"] == 1, "FAIL_ME should fail."

    def test_failed_certificate_has_error_message(self, client, tmp_path):
        """A failed certificate record should contain a non-empty error_message."""
        payload = make_job_payload(
            recipients=[make_recipient("FAIL_ME", "fail@example.com", "Failing Course")]
        )

        def always_fail(**kwargs):
            from app.certificate_generator import CertificateGenerationError
            raise CertificateGenerationError("Test failure")

        with patch("app.services.generate_certificate", side_effect=always_fail):
            with patch("app.services.settings") as mock_settings:
                mock_settings.get_certificates_path.return_value = tmp_path
                create_resp = client.post("/api/v1/jobs", json=payload)

        job_id = create_resp.json()["job_id"]
        records = client.get(f"/api/v1/jobs/{job_id}/certificates").json()

        assert len(records) == 1
        assert records[0]["status"] == CertificateStatus.FAILED.value
        assert records[0]["error_message"] is not None
        assert len(records[0]["error_message"]) > 0

    def test_failed_certificate_status_is_failed(self, client, tmp_path):
        """A failed certificate record's status field should be 'failed'."""
        payload = make_job_payload(
            recipients=[make_recipient("FAIL_ME", "fail@example.com", "Course")]
        )

        def always_fail(**kwargs):
            from app.certificate_generator import CertificateGenerationError
            raise CertificateGenerationError("Test failure")

        with patch("app.services.generate_certificate", side_effect=always_fail):
            with patch("app.services.settings") as mock_settings:
                mock_settings.get_certificates_path.return_value = tmp_path
                create_resp = client.post("/api/v1/jobs", json=payload)

        job_id = create_resp.json()["job_id"]
        records = client.get(f"/api/v1/jobs/{job_id}/certificates").json()

        assert records[0]["status"] == CertificateStatus.FAILED.value


# ===========================================================================
# 7. Downloading a generated certificate
# ===========================================================================

class TestDownloadCertificate:
    def _create_job_and_get_cert_id(self, client, tmp_path) -> tuple[str, str]:
        with patch("app.services.settings") as mock_settings:
            mock_settings.get_certificates_path.return_value = tmp_path
            create_resp = client.post(
                "/api/v1/jobs",
                json=make_job_payload(
                    recipients=[make_recipient("Downloader", "dl@example.com", "Course")]
                ),
            )
        job_id = create_resp.json()["job_id"]
        records = client.get(f"/api/v1/jobs/{job_id}/certificates").json()
        return job_id, records[0]["id"]

    def test_download_successful_certificate_returns_200(self, client, tmp_path):
        job_id, cert_id = self._create_job_and_get_cert_id(client, tmp_path)
        response = client.get(
            f"/api/v1/jobs/{job_id}/certificates/{cert_id}/download"
        )
        assert response.status_code == 200

    def test_download_certificate_content_type_is_pdf(self, client, tmp_path):
        job_id, cert_id = self._create_job_and_get_cert_id(client, tmp_path)
        response = client.get(
            f"/api/v1/jobs/{job_id}/certificates/{cert_id}/download"
        )
        assert "application/pdf" in response.headers["content-type"]

    def test_download_certificate_has_pdf_header(self, client, tmp_path):
        """Response body should begin with PDF magic bytes."""
        job_id, cert_id = self._create_job_and_get_cert_id(client, tmp_path)
        response = client.get(
            f"/api/v1/jobs/{job_id}/certificates/{cert_id}/download"
        )
        assert response.content[:4] == b"%PDF"

    def test_download_failed_certificate_returns_409(self, client, tmp_path):
        """Attempting to download a FAILED certificate should return 409 Conflict."""
        payload = make_job_payload(
            recipients=[make_recipient("FAIL", "fail@example.com", "X")]
        )

        def always_fail(**kwargs):
            from app.certificate_generator import CertificateGenerationError
            raise CertificateGenerationError("fail")

        with patch("app.services.generate_certificate", side_effect=always_fail):
            with patch("app.services.settings") as mock_settings:
                mock_settings.get_certificates_path.return_value = tmp_path
                create_resp = client.post("/api/v1/jobs", json=payload)

        job_id = create_resp.json()["job_id"]
        records = client.get(f"/api/v1/jobs/{job_id}/certificates").json()
        cert_id = records[0]["id"]

        response = client.get(
            f"/api/v1/jobs/{job_id}/certificates/{cert_id}/download"
        )
        assert response.status_code == 409

    def test_download_nonexistent_certificate_returns_404(self, client, tmp_path):
        with patch("app.services.settings") as mock_settings:
            mock_settings.get_certificates_path.return_value = tmp_path
            create_resp = client.post("/api/v1/jobs", json=VALID_JOB_PAYLOAD)

        job_id = create_resp.json()["job_id"]
        response = client.get(
            f"/api/v1/jobs/{job_id}/certificates/no-such-cert/download"
        )
        assert response.status_code == 404


# ===========================================================================
# 8. Health check
# ===========================================================================

class TestHealthCheck:
    def test_health_check_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_check_returns_ok_status(self, client):
        data = client.get("/health").json()
        assert data["status"] == "ok"


# ===========================================================================
# 9. Scalability: Pagination and Status Filtering
# ===========================================================================

class TestPaginationAndFiltering:
    def test_list_certificates_pagination_limit(self, client, tmp_path):
        """Testing limit parameter on list certificates."""
        payload = make_job_payload(
            recipients=[
                make_recipient("User 1", "u1@example.com", "Course 1"),
                make_recipient("User 2", "u2@example.com", "Course 2"),
                make_recipient("User 3", "u3@example.com", "Course 3"),
            ]
        )
        with patch("app.services.settings") as mock_settings:
            mock_settings.get_certificates_path.return_value = tmp_path
            create_resp = client.post("/api/v1/jobs", json=payload)

        job_id = create_resp.json()["job_id"]
        records = client.get(f"/api/v1/jobs/{job_id}/certificates?limit=2").json()
        assert len(records) == 2

    def test_list_certificates_pagination_offset(self, client, tmp_path):
        """Testing offset parameter on list certificates."""
        payload = make_job_payload(
            recipients=[
                make_recipient("User 1", "u1@example.com", "Course 1"),
                make_recipient("User 2", "u2@example.com", "Course 2"),
                make_recipient("User 3", "u3@example.com", "Course 3"),
            ]
        )
        with patch("app.services.settings") as mock_settings:
            mock_settings.get_certificates_path.return_value = tmp_path
            create_resp = client.post("/api/v1/jobs", json=payload)

        job_id = create_resp.json()["job_id"]
        records = client.get(f"/api/v1/jobs/{job_id}/certificates?offset=1").json()
        assert len(records) == 2
        assert records[0]["recipient_name"] == "User 2"

    def test_list_certificates_status_filter(self, client, tmp_path):
        """Testing status filter on list certificates."""
        payload = make_job_payload(
            recipients=[
                make_recipient("User 1", "u1@example.com", "Course 1"),
            ]
        )
        with patch("app.services.settings") as mock_settings:
            mock_settings.get_certificates_path.return_value = tmp_path
            create_resp = client.post("/api/v1/jobs", json=payload)

        job_id = create_resp.json()["job_id"]
        success_records = client.get(f"/api/v1/jobs/{job_id}/certificates?status=success").json()
        assert len(success_records) == 1

        failed_records = client.get(f"/api/v1/jobs/{job_id}/certificates?status=failed").json()
        assert len(failed_records) == 0


# ===========================================================================
# 10. Production Security & Observability
# ===========================================================================

class TestSecurityAndTracing:
    def test_request_id_header_propagated(self, client):
        """Ensures X-Request-ID is attached to HTTP responses for log tracing."""
        response = client.get("/health", headers={"X-Request-ID": "trace-uuid-12345"})
        assert response.headers.get("x-request-id") == "trace-uuid-12345"

    def test_versioned_health_endpoint(self, client):
        """Ensures /api/v1/health is operational."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


# ===========================================================================
# 11. Optional Feature: Bulk ZIP Archive Download
# ===========================================================================

class TestDownloadJobZip:
    def test_download_job_zip_returns_200_and_valid_zip(self, client, tmp_path):
        """GET /jobs/{job_id}/download-zip should stream an authentic zip containing PDFs."""
        with patch("app.services.settings") as mock_settings:
            mock_settings.get_certificates_path.return_value = tmp_path
            create_resp = client.post("/api/v1/jobs", json=VALID_JOB_PAYLOAD)

        job_id = create_resp.json()["job_id"]
        response = client.get(f"/api/v1/jobs/{job_id}/download-zip")
        assert response.status_code == 200
        assert "application/zip" in response.headers["content-type"]
        assert "attachment" in response.headers["content-disposition"]

        # Inspect binary ZIP content
        zip_buf = io.BytesIO(response.content)
        with zipfile.ZipFile(zip_buf, "r") as zf:
            namelist = zf.namelist()
            assert len(namelist) == len(VALID_JOB_PAYLOAD["recipients"])
            for name in namelist:
                assert name.endswith(".pdf")
                assert zf.read(name)[:4] == b"%PDF"

    def test_download_job_zip_nonexistent_job_returns_404(self, client):
        response = client.get("/api/v1/jobs/nonexistent-uuid/download-zip")
        assert response.status_code == 404

    def test_download_job_zip_no_success_returns_409(self, client, tmp_path):
        payload = make_job_payload(recipients=[make_recipient("Fail User", "fail@example.com", "Course")])

        def always_fail(**kwargs):
            from app.certificate_generator import CertificateGenerationError
            raise CertificateGenerationError("fail")

        with patch("app.services.generate_certificate", side_effect=always_fail):
            with patch("app.services.settings") as mock_settings:
                mock_settings.get_certificates_path.return_value = tmp_path
                create_resp = client.post("/api/v1/jobs", json=payload)

        job_id = create_resp.json()["job_id"]
        response = client.get(f"/api/v1/jobs/{job_id}/download-zip")
        assert response.status_code == 409


# ===========================================================================
# 12. Optional Feature: Retry Failed Certificates
# ===========================================================================

class TestRetryFailedCertificates:
    def test_retry_failed_certificates_enqueues_and_recovers(self, client, tmp_path):
        """Retrying failed certificates should re-queue them and succeed on subsequent attempt."""
        payload = make_job_payload(recipients=[make_recipient("Retry User", "retry@example.com", "Course")])

        def fail_once(**kwargs):
            from app.certificate_generator import CertificateGenerationError
            raise CertificateGenerationError("forced failure")

        with patch("app.services.generate_certificate", side_effect=fail_once):
            with patch("app.services.settings") as mock_settings:
                mock_settings.get_certificates_path.return_value = tmp_path
                create_resp = client.post("/api/v1/jobs", json=payload)

        job_id = create_resp.json()["job_id"]
        status_before = client.get(f"/api/v1/jobs/{job_id}").json()
        assert status_before["failed_count"] == 1

        # Now trigger retry without the failing mock
        with patch("app.services.settings") as mock_settings:
            mock_settings.get_certificates_path.return_value = tmp_path
            retry_resp = client.post(f"/api/v1/jobs/{job_id}/retry")

        assert retry_resp.status_code == 202
        assert retry_resp.json()["retried_count"] == 1

        # Because TestClient executes background tasks synchronously, status is now completed
        status_after = client.get(f"/api/v1/jobs/{job_id}").json()
        assert status_after["success_count"] == 1
        assert status_after["failed_count"] == 0

    def test_retry_no_failed_returns_zero_retried_count(self, client, tmp_path):
        with patch("app.services.settings") as mock_settings:
            mock_settings.get_certificates_path.return_value = tmp_path
            create_resp = client.post("/api/v1/jobs", json=VALID_JOB_PAYLOAD)

        job_id = create_resp.json()["job_id"]
        retry_resp = client.post(f"/api/v1/jobs/{job_id}/retry")
        assert retry_resp.status_code == 202
        assert retry_resp.json()["retried_count"] == 0


# ===========================================================================
# 13. Optional Feature: Public Certificate Verification Registry
# ===========================================================================

class TestVerifyCertificate:
    def test_verify_valid_certificate_returns_metadata(self, client, tmp_path):
        """GET /api/v1/verify/{certificate_id} returns authentic metadata."""
        with patch("app.services.settings") as mock_settings:
            mock_settings.get_certificates_path.return_value = tmp_path
            create_resp = client.post("/api/v1/jobs", json=VALID_JOB_PAYLOAD)

        job_id = create_resp.json()["job_id"]
        records = client.get(f"/api/v1/jobs/{job_id}/certificates").json()
        cert_id = records[0]["id"]

        response = client.get(f"/api/v1/verify/{cert_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["certificate_id"] == cert_id
        assert data["recipient_name"] == records[0]["recipient_name"]
        assert data["course_name"] == records[0]["course_name"]
        assert data["event_name"] == VALID_JOB_PAYLOAD["event_name"]
        assert data["issuer_name"] == VALID_JOB_PAYLOAD["issuer_name"]

    def test_verify_nonexistent_certificate_returns_404(self, client):
        response = client.get("/api/v1/verify/fake-uuid-not-found")
        assert response.status_code == 404

