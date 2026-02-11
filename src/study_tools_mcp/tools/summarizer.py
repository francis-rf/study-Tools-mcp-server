"""Summarization tools for study materials."""

from pathlib import Path
from typing import Literal

from ..utils.logger import get_logger
from ..parsers.pdf_parser import extract_text_from_pdf, extract_section

logger = get_logger(__name__)

# Default notes path - can be overridden
NOTES_PATH = Path("./data/notes")


async def find_topic_content(topic: str) -> str:
    """Find content related to a topic in notes directory"""
    try:
        if not NOTES_PATH.exists():
            return f"Notes directory not found: {NOTES_PATH}. Please create it and add your study materials."

        logger.info(f"Searching for topic '{topic}'")

        # List all files in notes directory
        pdf_files = list(NOTES_PATH.glob("*.pdf"))
        md_files = list(NOTES_PATH.glob("*.md"))

        if not pdf_files and not md_files:
            return f"No PDF or Markdown files found in {NOTES_PATH}. Please add your study materials."

        # Extract content from PDFs
        all_content = []

        for pdf_file in pdf_files:
            try:
                logger.info(f"Processing PDF: {pdf_file.name}")
                # Try to extract specific section first
                section_content = extract_section(pdf_file, topic)
                if section_content:
                    all_content.append(f"## From {pdf_file.name} - Section: {topic}\n\n{section_content}")
                else:
                    # If no specific section, extract full content
                    full_text = extract_text_from_pdf(pdf_file)
                    # Limit content to avoid overwhelming context
                    if len(full_text) > 10000:
                        full_text = full_text[:10000] + "\n\n[Content truncated...]"
                    all_content.append(f"## From {pdf_file.name}\n\n{full_text}")
            except Exception as e:
                logger.error(f"Error processing {pdf_file.name}: {str(e)}")
                continue

        # Process markdown files
        for md_file in md_files:
            try:
                content = md_file.read_text(encoding='utf-8')
                all_content.append(f"## From {md_file.name}\n\n{content}")
            except Exception as e:
                logger.error(f"Error reading {md_file.name}: {str(e)}")
                continue

        if not all_content:
            return f"Could not extract content from files in {NOTES_PATH}. Please check the files are readable."

        combined_content = "\n\n---\n\n".join(all_content)
        logger.info(f"Extracted {len(combined_content)} characters from {len(all_content)} file(s)")

        return combined_content

    except Exception as e:
        logger.error(f"Error searching for topic: {str(e)}")
        return f"Error searching for topic: {str(e)}"


async def summarize_section(
    topic: str,
    length: Literal["brief", "detailed", "comprehensive"] = "brief"
) -> str:
    """Create a summary of a topic from study materials

    Returns the content for Claude Desktop to summarize.
    """
    try:
        logger.info(f"Preparing content for summarizing '{topic}' ({length})")

        content = await find_topic_content(topic)
        if "No content found" in content or "Error" in content or "Not found" in content:
            return content

        length_instructions = {
            "brief": "Create a concise 3-5 sentence summary highlighting the key points.",
            "detailed": "Create a comprehensive summary covering all main concepts, with 2-3 paragraphs.",
            "comprehensive": "Create an extensive summary that covers all details, examples, and nuances."
        }

        # Return instructions for Claude Desktop to process
        return f"""# Summarization Request for: {topic.replace('_', ' ').title()}

**Instructions:** {length_instructions[length]}

**Content to summarize:**

{content}

Please provide a well-structured summary with key concepts, formulas, and practical insights."""

    except Exception as e:
        logger.error(f"Error preparing summary for '{topic}': {str(e)}")
        return f"Error: Failed to prepare summary: {str(e)}"


async def summarize_chapter(chapter_name: str) -> str:
    """Create a comprehensive chapter summary

    Returns the content for Claude Desktop to summarize.
    """
    try:
        content = await find_topic_content(chapter_name)
        if "No content found" in content or "Error" in content or "Not found" in content:
            return content

        # Return instructions for Claude Desktop to process
        return f"""# Chapter Summary Request: {chapter_name.replace('_', ' ').title()}

**Instructions:** Create a comprehensive chapter summary with the following structure:

1. Overview (2-3 sentences)
2. Key Concepts (bullet points)
3. Important Formulas/Algorithms
4. Practical Applications
5. Common Pitfalls

**Content to summarize:**

{content}"""

    except Exception as e:
        logger.error(f"Error preparing chapter summary: {str(e)}")
        return f"Error: Failed to prepare chapter summary: {str(e)}"
