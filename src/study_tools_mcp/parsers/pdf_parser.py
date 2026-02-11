"""PDF document parser."""

from pathlib import Path
from typing import Optional

import PyPDF2

from ..utils.logger import get_logger

logger = get_logger(__name__)


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract all text from PDF file"""
    try:
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""

            for page in reader.pages:
                try:
                    text += page.extract_text() + "\n\n"
                except Exception as e:
                    logger.warning(f"Error on page: {str(e)}")
                    continue

        logger.info(f"Extracted {len(text)} chars from {pdf_path.name}")
        return text.strip()

    except Exception as e:
        logger.error(f"Error reading PDF {pdf_path.name}: {str(e)}")
        raise


def extract_section(pdf_path: Path, section_title: str) -> Optional[str]:
    """Extract a specific section from PDF"""
    try:
        full_text = extract_text_from_pdf(pdf_path)
        lines = full_text.split('\n')
        section_text = []
        in_section = False

        for line in lines:
            line_stripped = line.strip()

            if section_title.lower() in line_stripped.lower():
                in_section = True
                section_text.append(line)
                continue

            if in_section:
                # Stop at next heading
                if (line_stripped.isupper() and len(line_stripped) > 5) or \
                   (line_stripped and len(line_stripped) < 50 and line_stripped[0].isupper()):
                    break
                section_text.append(line)

        result = '\n'.join(section_text) if section_text else None
        if result:
            logger.info(f"Found section '{section_title}' in {pdf_path.name}")
        return result

    except Exception as e:
        logger.error(f"Error extracting section: {str(e)}")
        return None


def get_pdf_metadata(pdf_path: Path) -> dict:
    """Extract metadata from PDF"""
    try:
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            metadata = reader.metadata or {}

            result = {
                'title': metadata.get('/Title', 'Unknown'),
                'author': metadata.get('/Author', 'Unknown'),
                'pages': len(reader.pages),
            }

            logger.info(f"Metadata from {pdf_path.name}: {result['pages']} pages")
            return result

    except Exception as e:
        logger.error(f"Error getting PDF metadata: {str(e)}")
        raise
