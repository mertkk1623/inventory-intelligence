"""Low-level Excel reading utilities.

This module only reads a workbook into DataFrames. All business rules live
in :mod:`core.validation` so the reading layer stays small and replaceable.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import BinaryIO

import pandas as pd

from utils.i18n import LocalisedMessage


class ExcelReadError(Exception):
    """Raised when a workbook cannot be opened or parsed."""


def read_workbook(
    source: str | Path | BinaryIO | bytes,
    *,
    filename: str | None = None,
) -> dict[str, pd.DataFrame]:
    """Read every sheet of an ``.xlsx`` workbook into a DataFrame mapping.

    Column headers are stripped of accidental leading/trailing whitespace so
    that a stray space does not block a valid upload. Sheet names are kept
    exactly as they appear in the workbook.
    """

    workbook_name = filename or getattr(source, "name", None) or "workbook.xlsx"

    try:
        if isinstance(source, bytes):
            source = BytesIO(source)
        elif hasattr(source, "seek"):
            source.seek(0)

        sheets = pd.read_excel(source, sheet_name=None, engine="openpyxl")
    except Exception as exc:  # pandas/openpyxl raise several unrelated types
        raise ExcelReadError(
            LocalisedMessage(
                "'{filename}' could not be read as an Excel workbook. Make sure "
                "the file is a valid .xlsx file and is not password protected.",
                filename=workbook_name,
            )
        ) from exc

    cleaned: dict[str, pd.DataFrame] = {}
    for name, frame in sheets.items():
        frame = frame.copy()
        frame.columns = [str(column).strip() for column in frame.columns]
        cleaned[name] = frame

    return cleaned
