"""Conservative, deterministic resume parsing for onboarding suggestions.

Resume text is untrusted input. This module extracts only a small allowlist of
job-search preferences and never executes or follows instructions in the file.
"""
from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path
from typing import Any

from docx import Document
from pypdf import PdfReader

MAX_RESUME_BYTES = 5 * 1024 * 1024
MAX_PDF_PAGES = 10
MAX_EXTRACTED_CHARS = 100_000
MAX_DOCX_UNCOMPRESSED_BYTES = 20 * 1024 * 1024
MAX_DOCX_ENTRIES = 1_000
SUPPORTED_EXTENSIONS = {".pdf", ".docx"}

# Deliberately conservative vocabulary. Unknown terms are left for the user to add.
SKILLS = (
    "Python", "Django", "FastAPI", "Flask", "JavaScript", "TypeScript",
    "React", "React Native", "Next.js", "Node.js", "Express", "Java",
    "Spring Boot", "SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis",
    "Docker", "Kubernetes", "AWS", "Azure", "Google Cloud", "Firebase",
    "Git", "Linux", "CI/CD", "Jenkins", "REST API", "GraphQL",
    "HTML", "CSS", "Figma", "UI/UX", "Machine Learning", "PyTorch",
    "TensorFlow", "Pandas", "NumPy", "OpenCV", "Selenium", "Playwright",
)
ROLES = (
    "Software Engineer", "Software Developer", "Full Stack Developer",
    "Frontend Developer", "Backend Developer", "Python Developer",
    "Java Developer", "React Developer", "React Native Developer",
    "Mobile App Developer", "DevOps Engineer", "QA Engineer",
    "Automation Engineer", "Data Analyst", "Data Scientist",
    "Machine Learning Engineer", "UI/UX Designer", "Product Designer",
    "Product Manager", "Business Analyst",
)
LOCATIONS = (
    "Bengaluru", "Bangalore", "Hyderabad", "Pune", "Mumbai", "Delhi",
    "New Delhi", "Gurugram", "Gurgaon", "Noida", "Chennai", "Kolkata",
    "Ahmedabad", "Jaipur", "Chandigarh", "Ambala", "Kochi", "Indore",
)


class ResumeParseError(ValueError):
    """Safe, user-displayable resume validation or extraction error."""


def _extract_text(filename: str, content: bytes) -> str:
    suffix = Path(filename or "").suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ResumeParseError("Upload a PDF or DOCX resume.")
    if not content or len(content) > MAX_RESUME_BYTES:
        raise ResumeParseError("Resume must be non-empty and no larger than 5 MB.")

    try:
        if suffix == ".pdf":
            if not content.startswith(b"%PDF-"):
                raise ResumeParseError("The uploaded file is not a valid PDF.")
            reader = PdfReader(io.BytesIO(content), strict=True)
            if reader.is_encrypted:
                raise ResumeParseError("Password-protected PDFs are not supported.")
            if len(reader.pages) > MAX_PDF_PAGES:
                raise ResumeParseError("PDF resumes must contain 10 pages or fewer.")
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
        else:
            if not content.startswith(b"PK") or not zipfile.is_zipfile(io.BytesIO(content)):
                raise ResumeParseError("The uploaded file is not a valid DOCX document.")
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                entries = archive.infolist()
                if len(entries) > MAX_DOCX_ENTRIES or sum(item.file_size for item in entries) > MAX_DOCX_UNCOMPRESSED_BYTES:
                    raise ResumeParseError("This DOCX file expands beyond the supported document limits.")
                if any(item.file_size > 0 and item.compress_size == 0 for item in entries):
                    raise ResumeParseError("This DOCX file contains an invalid compressed entry.")
                if any(item.compress_size and item.file_size / item.compress_size > 200 for item in entries):
                    raise ResumeParseError("This DOCX file has an unsafe compression ratio.")
            document = Document(io.BytesIO(content))
            parts = [paragraph.text for paragraph in document.paragraphs]
            for table in document.tables:
                for row in table.rows:
                    parts.extend(cell.text for cell in row.cells)
            text = "\n".join(parts)
    except ResumeParseError:
        raise
    except Exception:
        raise ResumeParseError("We could not read this resume. Try a text-based PDF or DOCX file.") from None

    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = text[:MAX_EXTRACTED_CHARS]
    if not text.strip():
        raise ResumeParseError("No readable text was found. Try a text-based PDF or DOCX resume.")
    return text


def _find_terms(text: str, terms: tuple[str, ...]) -> list[str]:
    found: list[str] = []
    for term in terms:
        if re.search(rf"(?<![A-Za-z0-9+#]){re.escape(term)}(?![A-Za-z0-9+#])", text, re.I):
            found.append(term)
    return found


def _experience_years(text: str) -> float | None:
    patterns = (
        r"(?:total|overall|professional)\s+(?:work\s+)?experience\s*[:\-]?\s*(\d{1,2}(?:\.\d)?)\s*\+?\s*years?",
        r"(\d{1,2}(?:\.\d)?)\s*\+?\s*years?\s+(?:of\s+)?(?:total|overall|professional)\s+(?:work\s+)?experience",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            value = float(match.group(1))
            if 0 <= value <= 30:
                return value
    return None


def parse_resume(filename: str, content: bytes) -> dict[str, Any]:
    """Return editable suggestions; caller must obtain user confirmation to save."""
    text = _extract_text(filename, content)
    roles = _find_terms(text, ROLES)
    skills = _find_terms(text, SKILLS)
    locations = _find_terms(text, LOCATIONS)
    experience = _experience_years(text)
    # Only opt into remote-only when the resume explicitly states exclusivity.
    remote_only = bool(re.search(
        r"\b(remote[- ]only|fully remote|work from home only|wfh only)\b", text, re.I
    ))
    suggestions = {
        "target_roles": roles[:10],
        "skills": skills[:30],
        "locations": locations[:10],
        "candidate_experience_years": experience,
        "remote_only": remote_only,
    }
    return {
        "suggestions": suggestions,
        "found_fields": [key for key, value in suggestions.items() if value not in ([], None, False)],
        "missing_required_fields": [key for key in ("target_roles", "locations") if not suggestions[key]],
        "requires_confirmation": True,
    }
