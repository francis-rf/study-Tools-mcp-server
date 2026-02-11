"""Flashcard generation tools."""

from ..utils.logger import get_logger
from .summarizer import find_topic_content

logger = get_logger(__name__)


async def create_flashcard_deck(topic: str, num_cards: int = 10) -> str:
    """Generate flashcards for a topic

    Returns instructions for Claude Desktop to generate flashcards.
    """
    try:
        logger.info(f"Preparing flashcard request for '{topic}': {num_cards} cards")

        content = await find_topic_content(topic)
        if "No content found" in content or "Error" in content or "Not found" in content:
            return content

        # Return instructions for the LLM to process.
        # Output MUST be valid JSON matching the schema below — no prose, no markdown fences.
        return f"""Create {num_cards} flashcards for studying "{topic.replace('_', ' ')}".

Each flashcard needs a clear question/prompt on the front and a concise answer on the back.
Cover key concepts, definitions, formulas, and important facts.

Base your flashcards on the following content:

{content}

Return ONLY a valid JSON object (no markdown code fences, no extra text) with this exact schema:
{{
  "type": "flashcards",
  "cards": [
    {{
      "front": "question or prompt",
      "back": "answer or explanation"
    }}
  ]
}}"""

    except Exception as e:
        logger.error(f"Error preparing flashcards: {str(e)}")
        return f"Error: Failed to prepare flashcards: {str(e)}"


