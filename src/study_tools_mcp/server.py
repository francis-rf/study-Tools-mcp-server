"""
MCP Server for Study Tools
"""

from typing import Literal
from pathlib import Path
from mcp.server.fastmcp import FastMCP

from .utils.logger import get_logger
from .tools.summarizer import summarize_section, summarize_chapter, find_topic_content
from .tools.quiz_gen import generate_quiz
from .tools.explainer import explain_concept, compare_concepts
from .tools.flashcards import create_flashcard_deck

logger = get_logger(__name__)

# Initialize FastMCP server
mcp = FastMCP("study-tools-mcp")

# Default notes path
NOTES_PATH = Path("./data/notes")

logger.info("=" * 60)
logger.info("Study Tools MCP Server Initializing")
logger.info(f"Notes path: {NOTES_PATH}")
logger.info("Running via Claude Desktop MCP")
logger.info("=" * 60)


# Summarization Tools
@mcp.tool()
async def summarize_topic(
    topic: str,
    length: Literal["brief", "detailed", "comprehensive"] = "brief"
) -> str:
    """Create a summary of a specific topic from study materials"""
    return await summarize_section(topic, length)


@mcp.tool()
async def summarize_full_chapter(chapter_name: str) -> str:
    """Create a comprehensive summary of an entire chapter"""
    return await summarize_chapter(chapter_name)


# Quiz Tools
@mcp.tool()
async def create_quiz(
    topic: str,
    num_questions: int = 5,
    difficulty: Literal["beginner", "intermediate", "advanced"] = "intermediate"
) -> str:
    """Generate a multiple-choice quiz on a specific topic"""
    return await generate_quiz(topic, num_questions, difficulty)


# Explanation Tools
@mcp.tool()
async def explain_topic(
    term: str,
    level: Literal["beginner", "intermediate", "advanced"] = "beginner"
) -> str:
    """Get an explanation of a concept at a specific difficulty level"""
    return await explain_concept(term, level)


@mcp.tool()
async def compare_two_concepts(concept1: str, concept2: str) -> str:
    """Compare and contrast two related concepts"""
    return await compare_concepts(concept1, concept2)


# Flashcard Tools
@mcp.tool()
async def create_flashcards(topic: str, num_cards: int = 10) -> str:
    """Generate flashcards for a topic"""
    return await create_flashcard_deck(topic, num_cards)


def main():
    """Entry point for the MCP server"""
    try:
        logger.info("Starting Study Tools MCP Server")
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        raise


if __name__ == "__main__":
    main()
