"""
tests/test_certificate_generator.py - Unit tests for the PDF generation module.

These tests exercise the generator in isolation, without any HTTP or database
layer. They verify:
  - A valid call produces a real PDF file at the returned path.
  - The generated file is a valid PDF (starts with %PDF header).
  - CertificateGenerationError is raised when output cannot be written.
"""
import os
import pytest
from pathlib import Path

from app.certificate_generator import generate_certificate, CertificateGenerationError


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------

def test_generate_certificate_creates_pdf_file(tmp_path: Path) -> None:
    """
    A successful call should return a path to a file that exists on disk.
    """
    file_path = generate_certificate(
        record_id="test-record-001",
        recipient_name="Alice Johnson",
        recipient_email="alice@example.com",
        course_name="Advanced Python Programming",
        event_name="TechConf 2024",
        issuer_name="Aereo Academy",
        issue_date="2024-11-15",
        output_dir=tmp_path,
    )

    assert os.path.exists(file_path), "Generated file should exist on disk."


def test_generate_certificate_returns_absolute_path(tmp_path: Path) -> None:
    """The returned path should be an absolute (not relative) path."""
    file_path = generate_certificate(
        record_id="test-record-002",
        recipient_name="Bob Smith",
        recipient_email="bob@example.com",
        course_name="Cloud Architecture",
        event_name="TechConf 2024",
        issuer_name="Aereo Academy",
        issue_date="2024-11-15",
        output_dir=tmp_path,
    )

    assert os.path.isabs(file_path), "Returned path should be absolute."


def test_generate_certificate_produces_valid_pdf(tmp_path: Path) -> None:
    """
    The generated file should begin with the PDF magic bytes (%PDF),
    confirming it is a real PDF and not an empty or corrupt file.
    """
    file_path = generate_certificate(
        record_id="test-record-003",
        recipient_name="Carol White",
        recipient_email="carol@example.com",
        course_name="Data Science Foundations",
        event_name="DataConf 2024",
        issuer_name="Test Institute",
        issue_date="2024-06-01",
        output_dir=tmp_path,
    )

    with open(file_path, "rb") as f:
        header = f.read(4)

    assert header == b"%PDF", f"Expected PDF header, got: {header!r}"


def test_generate_certificate_filename_uses_record_id(tmp_path: Path) -> None:
    """
    The generated file should be named after the record_id to prevent
    filename collisions in bulk generation.
    """
    record_id = "unique-record-id-xyz"
    file_path = generate_certificate(
        record_id=record_id,
        recipient_name="Dave Brown",
        recipient_email="dave@example.com",
        course_name="Machine Learning",
        event_name="AI Summit",
        issuer_name="Tech Corp",
        issue_date="2024-09-20",
        output_dir=tmp_path,
    )

    assert Path(file_path).stem == record_id, (
        f"Filename stem should be the record_id, got: {Path(file_path).stem}"
    )


def test_generate_certificate_creates_output_directory(tmp_path: Path) -> None:
    """
    The generator should create the output directory if it does not exist.
    """
    nested_dir = tmp_path / "nested" / "output" / "dir"
    assert not nested_dir.exists(), "Directory should not exist before generation."

    generate_certificate(
        record_id="test-nested-dir",
        recipient_name="Eve Davis",
        recipient_email="eve@example.com",
        course_name="DevOps Mastery",
        event_name="DevConf",
        issuer_name="Org Name",
        issue_date="2024-03-10",
        output_dir=nested_dir,
    )

    assert nested_dir.exists(), "Output directory should have been created."


# ---------------------------------------------------------------------------
# Failure tests
# ---------------------------------------------------------------------------

def test_generate_certificate_raises_on_invalid_output_dir() -> None:
    """
    Passing an output_dir that cannot be created (e.g., a path that is a
    file, not a directory) should raise CertificateGenerationError.
    """
    import tempfile

    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
        file_as_dir = Path(f.name)

    try:
        # Try to use a file path as if it were a directory
        invalid_dir = file_as_dir / "subdir"
        with pytest.raises(CertificateGenerationError):
            generate_certificate(
                record_id="fail-test",
                recipient_name="Frank Green",
                recipient_email="frank@example.com",
                course_name="Networking Basics",
                event_name="NetConf",
                issuer_name="Net Org",
                issue_date="2024-01-01",
                output_dir=invalid_dir,
            )
    finally:
        os.unlink(file_as_dir)


def test_generate_multiple_certificates_no_collision(tmp_path: Path) -> None:
    """
    Generating multiple certificates to the same directory should produce
    separate files without overwriting each other.
    """
    ids = ["id-alpha", "id-beta", "id-gamma"]
    paths = []

    for record_id in ids:
        path = generate_certificate(
            record_id=record_id,
            recipient_name=f"Recipient {record_id}",
            recipient_email=f"{record_id}@example.com",
            course_name="Shared Course",
            event_name="Bulk Event",
            issuer_name="Bulk Org",
            issue_date="2024-07-04",
            output_dir=tmp_path,
        )
        paths.append(path)

    # All paths should be distinct
    assert len(set(paths)) == len(ids), "Each certificate should be a separate file."
    # All files should exist
    for path in paths:
        assert os.path.exists(path), f"File should exist: {path}"
