"""Quiz generation tools."""

from typing import Literal
from ..utils.logger import get_logger
from .summarizer import find_topic_content

logger = get_logger(__name__)


async def generate_quiz(
    topic: str,
    num_questions: int = 5,
    difficulty: Literal["beginner", "intermediate", "advanced"] = "intermediate"
) -> str:
    """Generate a multiple-choice quiz

    Returns instructions for Claude Desktop to generate the quiz.
    """
    try:
        logger.info(f"Preparing quiz request for '{topic}': {num_questions} questions, {difficulty}")

        content = await find_topic_content(topic)
        if "No content found" in content or "Error" in content or "Not found" in content:
            return content

        difficulty_map = {
            "beginner": "Focus on basic definitions and concepts.",
            "intermediate": "Include application-based questions.",
            "advanced": "Include complex scenarios and edge cases."
        }

        # Return instructions for the LLM to process.
        # Output MUST be valid JSON matching the schema below — no prose, no markdown fences.
        return f"""Create a {num_questions}-question multiple-choice quiz on "{topic}".

Difficulty: {difficulty} — {difficulty_map[difficulty]}

Base your questions on the following content:

{content}

Return ONLY a valid JSON object (no markdown code fences, no extra text) with this exact schema:
{{
  "type": "quiz",
  "questions": [
    {{
      "question": "question text",
      "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
      "answer": "A",
      "explanation": "why this answer is correct"
    }}
  ]
}}"""

    except Exception as e:
        logger.error(f"Error preparing quiz: {str(e)}")
        return f"Error: Failed to prepare quiz: {str(e)}"


