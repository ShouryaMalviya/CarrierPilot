"""Deterministic text extraction for PDF and DOCX documents.

Separates file format validation from extraction. Handles scanned documents,
encrypted files, and corrupt structures with actionable warnings rather than
fake extraction results or unhandled exceptions.
"""

import io
import re
from dataclasses import asdict, dataclass, field
from typing import List
import docx
import pypdf
from pypdf.errors import PdfReadError

PARSER_VERSION_STRING = f"pypdf-{pypdf.__version__} / python-docx-{docx.__version__}"


@dataclass
class ExtractionResult:
    """Standardized text extraction result envelope."""

    text: str = ""
    page_count: int = 0
    warnings: List[str] = field(default_factory=list)
    parser_version: str = PARSER_VERSION_STRING
    status: str = "completed"  # 'completed', 'warning', 'failed'

    def to_dict(self) -> dict:
        """Convert dataclass to dictionary for JSON persistence."""
        return asdict(self)


def normalize_extracted_text(text: str) -> str:
    """Normalize extracted text while preserving section boundaries and line breaks."""
    if not text:
        return ""

    # Normalize line endings and non-breaking spaces
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\xa0", " ").replace("\u200b", "")

    # Strip trailing whitespace on each line
    lines = [re.sub(r"[ \t]+$", "", line) for line in text.split("\n")]

    # Collapse more than two consecutive empty lines into two (paragraph break)
    normalized = "\n".join(lines)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)

    return normalized.strip()


def extract_text_from_pdf(content: bytes) -> ExtractionResult:
    """Extract deterministic text from PDF bytes with scanned/encrypted detection."""
    result = ExtractionResult(parser_version=f"pypdf-{pypdf.__version__}")

    try:
        reader = pypdf.PdfReader(io.BytesIO(content))

        # Check for encrypted / password-protected PDF
        if reader.is_encrypted:
            # Attempt empty password decrypt
            try:
                decrypted = reader.decrypt("")
                if decrypted == 0:
                    result.status = "failed"
                    result.warnings.append(
                        "PDF is password-protected or encrypted. Please upload an unprotected file."
                    )
                    return result
            except Exception:
                result.status = "failed"
                result.warnings.append(
                    "PDF is password-protected or encrypted. Please upload an unprotected file."
                )
                return result

        page_count = len(reader.pages)
        result.page_count = page_count

        if page_count == 0:
            result.status = "failed"
            result.warnings.append("The PDF document contains 0 pages.")
            return result

        extracted_pages = []
        for i, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text() or ""
                extracted_pages.append(page_text)
            except Exception as page_err:
                result.warnings.append(f"Warning: page {i + 1} extraction encountered an issue: {str(page_err)}")

        full_text = "\n\n".join(extracted_pages)
        normalized = normalize_extracted_text(full_text)
        result.text = normalized

        # Scanned / Image-only detection
        # If the document has pages but less than 20 characters of extractable text
        if len(normalized) < 20:
            result.status = "warning"
            result.warnings.append(
                "Document appears to be a scanned image or contains no selectable text. "
                "OCR is not currently supported; please upload a text-based PDF or Word document."
            )
        else:
            result.status = "completed"

    except PdfReadError as e:
        result.status = "failed"
        result.warnings.append(f"Corrupt or malformed PDF structure: {str(e)}")
    except Exception as e:
        result.status = "failed"
        result.warnings.append(f"Unexpected error parsing PDF document: {str(e)}")

    return result


def extract_text_from_docx(content: bytes) -> ExtractionResult:
    """Extract deterministic text from DOCX OpenXML archive bytes."""
    result = ExtractionResult(parser_version=f"python-docx-{docx.__version__}")

    try:
        doc = docx.Document(io.BytesIO(content))

        paragraphs = []
        for p in doc.paragraphs:
            stripped = p.text.strip()
            if stripped:
                paragraphs.append(stripped)

        # Also extract structured table text if present
        table_lines = []
        for table in doc.tables:
            for row in table.rows:
                cells = [c.text.strip() for c in row.cells if c.text.strip()]
                if cells:
                    table_lines.append(" | ".join(cells))

        combined = paragraphs + table_lines
        result.page_count = max(1, len(doc.sections))

        full_text = "\n\n".join(combined)
        normalized = normalize_extracted_text(full_text)
        result.text = normalized

        if len(normalized) < 5:
            result.status = "warning"
            result.warnings.append("Word document contains no extractable text.")
        else:
            result.status = "completed"

    except Exception as e:
        result.status = "failed"
        result.warnings.append(f"Failed to parse DOCX document: {str(e)}")

    return result


def extract_text_from_file(file_path: str, extension: str) -> ExtractionResult:
    """Read file bytes from private storage and perform deterministic text extraction."""
    clean_ext = extension.lstrip(".").lower()

    try:
        with open(file_path, "rb") as f:
            content = f.read()
    except OSError as e:
        return ExtractionResult(
            status="failed",
            warnings=[f"Failed to read file from storage: {str(e)}"],
        )

    if clean_ext == "pdf":
        return extract_text_from_pdf(content)
    elif clean_ext == "docx":
        return extract_text_from_docx(content)
    else:
        return ExtractionResult(
            status="failed",
            warnings=[f"Unsupported file format '{clean_ext}' for text extraction."],
        )

