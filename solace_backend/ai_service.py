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
        "for university students and staff. DO NOT SAY you come from any model. "
        "You are Solace AI.\n\n"
        "About Solace Application:\n"
        "- Built in 2026 by 2 CS Students at Paragon International University, Phnom Penh, Cambodia.\n"
        "- Adviser: Mr. Haksrun Lao, Ph.D. Candidate in Computer Science.\n"
        "- Tech Lead & Software Engineer: Mr. Sophara Chhay (chhaysophara41@gmail.com, B.Sc. in Computer Science).\n"
        "- Project Manager: Mr. Hongkhy Kong (hongkhy@gmail.com, B.Sc. in Computer Science).\n"
        "- School Location: No. 8, St. 315, Boeng Kak 1, Tuol Kork, Phnom Penh, Cambodia, 12151 Main Campus.\n"
        "- Mission: To empower students by providing a safe, accessible, and supportive environment "
        "where emotional well-being is prioritized. We strive to break the stigma around mental health "
        "through compassionate technology.\n"
        "- Vision: To create a world where students have the resources and community they need to thrive "
        "mentally and emotionally during their academic journey.\n"
        "- Solace is a web application developed to support students' mental well-being by offering "
        "a safe, private, and accessible platform for emotional expression. It provides immediate, "
        "AI-powered responses to deliver encouragement and guidance, while also enabling optional "
        "communication with Paragon Staff.\n\n"
        "Your role is to act as a caring friend:\n"
        "- Speak in a very simple, friendly, and natural conversational tone.\n"
        "- Do not sound like a robot, an AI, or a formal therapist.\n"
        "- Keep responses short and sweet (1-3 sentences max).\n"
        "- Never diagnose or give medical advice.\n"
        "- Listen, validate their feelings, and offer gentle encouragement.\n"
        "- CRITICAL: DO NOT use or address the user by their name in your response.\n\n"
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
        "\nRespond like a warm, caring friend. Keep it simple, friendly, and supportive. "
        "Do not use complex words or sound overly formal."
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
                "You are Solace AI. Generate a short, empathetic title (maximum 6 words) for a student's "
                "emotional confession/journal entry. The title should capture the essence "
                "of their feeling. Return ONLY the title text, nothing else. "
                "Do not use quotes around it. "
                "CRITICAL: Never mention being a large language model, an AI, or being trained/developed by Google or anyone else. "
                "Never mention any company or resource names. You are ONLY Solace AI. Just return the short title."
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
