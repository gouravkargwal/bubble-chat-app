"""
Profile optimizer prompts for generating dating profile blueprints.

These prompts and schema are used by the Gemini call in the blueprint
generation service.
"""

# Absolute maximum slots — kept in sync with the JSON schema and Pydantic model.
MAX_BLUEPRINT_SLOTS = 6

# Allowlist guards against prompt injection via the lang query parameter.
ALLOWED_LANGS: frozenset[str] = frozenset(
    {
        "English",
        "Hindi",
        "Hinglish",
        "Gen-Z Slang",
        "Spanish",
        "French",
        "Portuguese",
        "Tamil",
        "Telugu",
    }
)

PROFILE_BLUEPRINT_SCHEMA: dict = {
    "type": "OBJECT",
    "properties": {
        "slots": {
            "type": "ARRAY",
            "minItems": 1,
            "maxItems": MAX_BLUEPRINT_SLOTS,
            "items": {
                "type": "OBJECT",
                "properties": {
                    "photo_id": {"type": "STRING"},
                    "slot_number": {
                        "type": "INTEGER",
                        "minimum": 1,
                        "maximum": MAX_BLUEPRINT_SLOTS,
                    },
                    "role": {"type": "STRING"},
                    "caption": {"type": "STRING"},
                    "contextual_hook": {"type": "STRING"},
                    "hinge_prompt": {"type": "STRING"},
                    "aisle_prompt": {"type": "STRING"},
                    "coach_reasoning": {"type": "STRING"},
                },
                "required": [
                    "photo_id",
                    "slot_number",
                    "role",
                    "caption",
                    "contextual_hook",
                    "hinge_prompt",
                    "aisle_prompt",
                    "coach_reasoning",
                ],
            },
        },
        "overall_theme": {"type": "STRING"},
        "bio": {
            "type": "STRING",
            "maxLength": 500,
        },
        "universal_prompts": {
            "type": "ARRAY",
            "minItems": 3,
            "maxItems": 3,
            "items": {
                "type": "OBJECT",
                "properties": {
                    "category": {"type": "STRING"},
                    "suggested_text": {"type": "STRING"},
                },
                "required": ["category", "suggested_text"],
            },
        },
    },
    "required": [
        "slots",
        "overall_theme",
        "bio",
        "universal_prompts",
    ],
}


def build_blueprint_system_prompt(lang: str) -> str:
    """Build the system prompt for profile blueprint generation."""
    return (
        "You are an elite Cross-Platform Dating Profile Architect (Tinder, Bumble, Hinge, Aisle).\n"
        f"DIALECT ENFORCEMENT: The requested language/dialect is {lang}. You MUST write the `caption`, `hinge_prompt`, `aisle_prompt`, `bio`, and `universal_prompts` entirely in this exact dialect.\n"
        "* If Hinglish: Weave Romanized Hindi into EVERY single sentence (e.g., yaar, bhai, matlab, samajh, waisa, bilkul, desi). ZERO purely standard-English sentences are allowed. If a generated prompt can be read naturally by an American, you failed.\n"
        "* If Gen-Z Slang: Use modern TikTok-era phrasing.\n"
        "* Match cultural tone exactly. Never use corporate or AI-sounding filler."
    )


def build_blueprint_user_prompt(available_count: int, photos_json: str) -> str:
    """Build the user prompt for profile blueprint generation with the given photos."""
    return (
        "CRITICAL CONSTRAINT:\n"
        "* You CANNOT see the photos. This call includes no image pixels — only the JSON metadata below.\n"
        "* You MUST rely entirely on each entry's `score`, `tier`, and `brutal_feedback`. Do not invent faces, poses, lighting, outfits, or settings you were not told about.\n"
        "* Any copy must be grounded in those fields only; never hallucinate visual facts.\n\n"
        f"Design a dating profile blueprint using these {available_count} audited photos.\n\n"
        "RULES:\n"
        f"* Use ALL {available_count} photos. `slot_number` MUST be 1 to {available_count} (no gaps/repeats).\n"
        "* `photo_id`: For every slot, set `photo_id` to the EXACT `id` string copied verbatim from one object in AUDITED PHOTOS JSON below. Do NOT invent, truncate, reformat, or guess IDs — only the provided UUID strings are valid. Each listed `id` must appear exactly once across slots.\n"
        "* Slot 1 (`slot_number` 1): Assign to the photo with the highest `score`. If multiple photos share the top score, pick the one whose `brutal_feedback` best indicates an attractive, clear-face, or strong first-impression shot (infer only from that text, not from imagined images).\n"
        "* Vibe: High-status, charismatic, social proof. No try-hard/desperate energy.\n"
        '* Context: Use `brutal_feedback` as creative fuel — spin it into confident, playful framing in captions and prompts; do not fabricate a "better angle" you cannot see.\n\n'
        "SLOT REQUIREMENTS:\n"
        "* `caption`: Short, high-status.\n"
        "* `contextual_hook`: Short label (e.g., 'Parent Approval', 'Adventure Flex').\n"
        "* `hinge_prompt`: Ready-to-paste, conversational (max 150 chars). Include prompt + answer (e.g., 'My most controversial opinion → Brunch is just breakfast for people who overslept.').\n"
        "* `aisle_prompt`: Ready-to-paste, relationship-focused. Warm, genuine, showing depth.\n"
        "* `coach_reasoning`: Brief explanation for this slot choice.\n\n"
        "GLOBAL REQUIREMENTS:\n"
        "* `overall_theme`: 1-sentence vibe summary.\n"
        "* `bio`: Punchy cross-platform bio (max 500 chars). Blend 2-3 specific fun facts with a confident, low-investment tone.\n"
        "* `universal_prompts`: Exactly 3 hooks usable on ANY app. Each needs a `category` (e.g., 'Low-Key Flex') and concrete `suggested_text`.\n\n"
        "AUDITED PHOTOS JSON:\n"
        f"{photos_json}"
    )
