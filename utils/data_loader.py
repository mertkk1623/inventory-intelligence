"""Load demo and user-uploaded workbooks into session state."""

from __future__ import annotations

from datetime import date
from io import BytesIO

from config import DEMO_FILE, DEMO_SOURCE, SAMPLE_SOURCE, UPLOAD_SOURCE
from core.validation import (
    ERROR,
    ValidationIssue,
    ValidationResult,
    validate_excel,
    validate_excel_file,
)
from utils.sample_data import sample_filename, sample_workbook_bytes
from utils.session_state import set_dataset


def load_demo_dataset() -> ValidationResult:
    """Validate and activate the bundled demo workbook."""

    if not DEMO_FILE.exists():
        return ValidationResult(
            filename=DEMO_FILE.name,
            source=DEMO_SOURCE,
            issues=[
                ValidationIssue(
                    severity=ERROR,
                    code="demo_missing",
                    message=(
                        "The bundled demo workbook could not be found at "
                        f"'{DEMO_FILE}'. Restore the templates folder and try again."
                    ),
                )
            ],
        )

    result = validate_excel_file(DEMO_FILE, source_kind=DEMO_SOURCE)
    if result.is_valid and result.dataset is not None:
        set_dataset(result.dataset)
    return result


def load_sample_dataset(
    key: str,
    *,
    reference: date | None = None,
) -> ValidationResult:
    """Generate a sample scenario workbook, validate it and activate it.

    The bytes come from the same generator that powers the download button, so
    the dataset a user explores is identical to the file they can download. The
    workbook is validated by the real engine rather than trusted blindly: if
    the generator ever drifts from the schema, this surfaces as a normal
    validation error instead of a broken dashboard.
    """

    result = validate_excel(
        BytesIO(sample_workbook_bytes(key, reference=reference)),
        filename=sample_filename(key),
        source_kind=SAMPLE_SOURCE,
    )
    if result.is_valid and result.dataset is not None:
        set_dataset(result.dataset)
    return result


def load_uploaded_dataset(uploaded_file) -> ValidationResult:
    """Validate and activate a Streamlit ``UploadedFile``."""

    payload = uploaded_file.getvalue()
    result = validate_excel(
        BytesIO(payload),
        filename=uploaded_file.name,
        source_kind=UPLOAD_SOURCE,
    )
    if result.is_valid and result.dataset is not None:
        set_dataset(result.dataset)
    return result
