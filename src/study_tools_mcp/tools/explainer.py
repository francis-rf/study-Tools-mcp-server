"""Concept explanation tools."""

from typing import Literal
from ..utils.logger import get_logger
from .summarizer import find_topic_content

logger = get_logger(__name__)


async def explain_concept(
    term: str,
    level: Literal["beginner", "intermediate", "advanced"] = "beginner"
) -> str:
    """Explain a concept at a specific difficulty level

    Returns instructions for Claude Desktop to explain the concept.
    """
    try:
        logger.info(f"Preparing explanation request for '{term}' at {level} level")

        content = await find_topic_content(term)

        level_map = {
            "beginner": "Use simple analogies, avoid jargon, focus on intuition.",
            "intermediate": "Include technical terms with definitions, explain how things work.",
            "advanced": "Include formulas, edge cases, implementation details, and tradeoffs."
        }

        has_content = "No content found" not in content and "Error" not in content and "Not found" not in content

        # Return instructions for Claude Desktop to process
        return f"""# Explanation Request: {term.replace('_', ' ').title()}

**Difficulty Level:** {level}
- {level_map[level]}

**Structure to follow:**
1. Simple definition
2. Detailed explanation
3. Example or analogy
4. Common misconceptions
5. Related concepts

{"**Content from study materials:**" if has_content else "**Note:** No specific study materials found. Use general knowledge."}

{content if has_content else ""}

Please provide a comprehensive explanation now."""

    except Exception as e:
        logger.error(f"Error preparing explanation: {str(e)}")
        return f"Error: Failed to prepare explanation: {str(e)}"


async def compare_concepts(concept1: str, concept2: str) -> str:
    """Compare and contrast two concepts

    Returns instructions for Claude Desktop to compare the concepts.
    """
    try:
        logger.info(f"Preparing comparison request for '{concept1}' vs '{concept2}'")

        content1 = await find_topic_content(concept1)
        content2 = await find_topic_content(concept2)

        has_content1 = "No content found" not in content1 and "Error" not in content1 and "Not found" not in content1
        has_content2 = "No content found" not in content2 and "Error" not in content2 and "Not found" not in content2

        # Return instructions for Claude Desktop to process
        result = f"""# Comparison Request: {concept1.title()} vs {concept2.title()}

**Instructions:** Compare and contrast these two concepts.

**Structure to follow:**
1. Brief overview of each concept
2. Similarities
3. Key differences
4. When to use each
5. Relationship between them

"""

        if has_content1:
            result += f"**Content for {concept1}:**\n\n{content1}\n\n---\n\n"
        else:
            result += f"**Note:** No study materials found for {concept1}. Use general knowledge.\n\n"

        if has_content2:
            result += f"**Content for {concept2}:**\n\n{content2}\n\n---\n\n"
        else:
            result += f"**Note:** No study materials found for {concept2}. Use general knowledge.\n\n"

        result += "Please provide a detailed comparison now."

        return result

    except Exception as e:
        logger.error(f"Error preparing comparison: {str(e)}")
        return f"Error: Failed to prepare comparison: {str(e)}"


