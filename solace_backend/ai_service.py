"""
AI Service — calls OpenRouter (ChatCompletion-compatible) for supportive responses.
"""
import logging
from decouple import config
import requests

logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = config('OPENROUTER_API_KEY')
OPENROUTER_MODEL = config('OPENROUTER_MODEL')
OPENROUTER_URL = config('OPENROUTER_URL')


def _call_openrouter(messages: list[dict], max_tokens: int = 512) -> str:
    """Low-level call to OpenRouter. Returns the assistant message text."""
    if not OPENROUTER_API_KEY:
        logger.warning('OPENROUTER_API_KEY not set – returning fallback message.')
        return "I'm here for you. Please share what's on your mind."

    headers = {
        'Authorization': f'Bearer {OPENROUTER_API_KEY}',
        'Content-Type': 'application/json',
    }
    payload = {
        'model': OPENROUTER_MODEL,
        'messages': messages,
        'max_tokens': max_tokens,
        'temperature': 0.7,
    }

    try:
        resp = requests.post(OPENROUTER_URL, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data['choices'][0]['message']['content'].strip()
    except Exception as e:
        logger.exception('OpenRouter API call failed: %s', e)
        return "I'm here to listen. Could you tell me more about how you're feeling?"


def generate_supportive_response(
    user_name: str,
    user_role: str,
    user_positions: list[str],
    confession_states: list[str],
    confession_positions: list[str],
    is_anonymous: bool,
    conversation_history: list[dict],
) -> str:
    """
    Generate a supportive AI response given the full context.

    conversation_history: list of {"role": "user"|"assistant", "content": "..."}
    """
    system_prompt = (
        "You are Solace AI, a compassionate and supportive mental wellness assistant "
        "for university students and staff. Your role is to:\n"
        "- Listen empathetically and validate feelings\n"
        "- Provide gentle, constructive guidance\n"
        "- Never diagnose or prescribe — suggest professional help when appropriate\n"
        "- Keep responses concise (2-4 sentences) but warm and caring\n"
        "- Use a conversational, supportive tone\n\n"
        f"Student info:\n"
        f"- Name: {'Anonymous' if is_anonymous else user_name}\n"
        f"- Role in system: {user_role}\n"
    )

    if user_positions:
        system_prompt += f"- Positions: {', '.join(user_positions)}\n"

    if confession_states:
        system_prompt += f"- Current mental states: {', '.join(confession_states)}\n"

    if confession_positions:
        system_prompt += (
            f"- Wants to connect with: {', '.join(confession_positions)}\n"
        )

    system_prompt += (
        "\nRespond with empathy. Acknowledge their feelings first, then offer "
        "a brief supportive perspective or gentle suggestion."
    )

    messages = [{'role': 'system', 'content': system_prompt}]
    messages.extend(conversation_history)

    return _call_openrouter(messages, max_tokens=300)


def generate_confession_title(first_message: str) -> str:
    """
    Auto-generate a short, descriptive title for a confession
    based on the student's first message.
    """
    messages = [
        {
            'role': 'system',
            'content': (
                "Generate a short, empathetic title (maximum 6 words) for a student's "
                "emotional confession/journal entry. The title should capture the essence "
                "of their feeling. Return ONLY the title text, nothing else. "
                "Do not use quotes around it."
            ),
        },
        {
            'role': 'user',
            'content': first_message,
        },
    ]

    title = _call_openrouter(messages, max_tokens=20)
    # Clean up: remove quotes, limit length
    title = title.strip().strip('"').strip("'")
    if len(title) > 255:
        title = title[:252] + '...'
    return title
