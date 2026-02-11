"""Markdown document parser."""

from pathlib import Path
from typing import Optional
import re

from ..utils.logger import get_logger

logger = get_logger(__name__)


def extract_text_from_md(md_path: Path) -> str:
    """Extract text from Markdown file"""
    try:
        if not md_path.exists():
            raise FileNotFoundError(f"Markdown not found: {md_path}")

        with open(md_path, 'r', encoding='utf-8') as file:
            content = file.read()

        logger.info(f"Extracted {len(content)} chars from {md_path.name}")
        return content

    except Exception as e:
        logger.error(f"Error reading Markdown {md_path.name}: {str(e)}")
        raise


def extract_section(md_path: Path, section_title: str) -> Optional[str]:
    """Extract a specific section from Markdown file"""
    try:
        content = extract_text_from_md(md_path)
        lines = content.split('\n')
        section_lines = []
        in_section = False
        section_level = 0

        for line in lines:
            heading_match = re.match(r'^(#{1,6})\s+(.+)', line)

            if heading_match:
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()

                if section_title.lower() in title.lower() and not in_section:
                    in_section = True
                    section_level = level
                    section_lines.append(line)
                    continue

                if in_section and level <= section_level:
                    break

            if in_section:
                section_lines.append(line)

        result = '\n'.join(section_lines) if section_lines else None
        if result:
            logger.info(f"Found section '{section_title}' in {md_path.name}")
        return result

    except Exception as e:
        logger.error(f"Error extracting section: {str(e)}")
        return None


def extract_all_sections(md_path: Path) -> dict[str, str]:
    """Extract all sections from Markdown file"""
    try:
        content = extract_text_from_md(md_path)
        lines = content.split('\n')
        sections = {}
        current_section = None
        current_content = []

        for line in lines:
            heading_match = re.match(r'^##\s+(.+)', line)

            if heading_match:
                if current_section:
                    sections[current_section] = '\n'.join(current_content).strip()
                current_section = heading_match.group(1).strip()
                current_content = []
            elif current_section:
                current_content.append(line)

        if current_section and current_content:
            sections[current_section] = '\n'.join(current_content).strip()

        logger.info(f"Extracted {len(sections)} sections from {md_path.name}")
        return sections

    except Exception as e:
        logger.error(f"Error extracting sections: {str(e)}")
        return {}


def get_headings(md_path: Path) -> list[tuple[int, str]]:
    """Extract all headings from Markdown file"""
    try:
        content = extract_text_from_md(md_path)
        headings = []

        for line in content.split('\n'):
            match = re.match(r'^(#{1,6})\s+(.+)', line)
            if match:
                level = len(match.group(1))
                title = match.group(2).strip()
                headings.append((level, title))

        logger.info(f"Found {len(headings)} headings in {md_path.name}")
        return headings

    except Exception as e:
        logger.error(f"Error extracting headings: {str(e)}")
        return []
