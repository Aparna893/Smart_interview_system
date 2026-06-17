"""
core/services/hybrid_question_service.py

Question generation pipeline:
    1. Ollama (local free model — primary, no API key needed)
    2. FLAN-T5 (local trained model — fallback)
    3. OpenRouter / GPT-4o-mini (API fallback — last resort)

Nothing else in this file changes from the original.
"""

from core.services.ollama_question_service import (
    generate_ollama_questions,
    is_ollama_available,
)
from core.services.flan_question_service import (
    generate_flan_question,
)
from core.openrouter_service import (
    generate_questions_openrouter,
)
from core.services.question_filter import (
    filter_questions,
)

print("HYBRID QUESTION SERVICE LOADED")

# ── SHARED BAD PATTERNS ───────────────────────────────────────────
# Applied after both Ollama and FLAN outputs
_BAD_PATTERNS = [
    "why does",
    "why is",
    "java.lang",
    "undefined",
    "stacktrace",
    "not working",
    "exception in",
    "error in",
    "what is the skill",
    "what skill",
    "company limited",
    "digital infrastructure",
    "what type",
    "mainframe",
    "necessary response",
    "project fail",
    "not being used",
    "what is the best way",
    "personal information",
    "candidate name",
    "email address",
    "phone number",
    "which company",
    "where did",
]


def _filter_raw(questions: list, is_dict: bool = False) -> list:
    """
    Filter a list of question strings or dicts against bad patterns.
    - is_dict=True  → questions are dicts with a 'question' key (Ollama output)
    - is_dict=False → questions are plain strings (FLAN output)
    """
    valid = []
    for q in questions:
        text   = q["question"] if is_dict else q
        lower  = text.lower()

        if len(text.split()) < 5:
            continue
        if any(bad in lower for bad in _BAD_PATTERNS):
            continue

        valid.append(q)
    return valid


# ─────────────────────────────────────────────────────────────────
def generate_questions(
    skill: str,
    context: str,
    count: int = 5,
) -> list:
    """
    Main entry point called by ocr_service / views.

    Always returns a list of dicts:
        [{"question": "...", "difficulty": "...", "type": "..."}, ...]

    Tries Ollama → FLAN-T5 → OpenRouter in order.
    """

    # ─────────────────────────────────────────────────────────────
    # STAGE 1 — OLLAMA (local, free, no API key)
    # ─────────────────────────────────────────────────────────────
    try:
        print(f"\n[INFO] Trying Ollama for skill: '{skill}' ...")

        # Fast pre-check so we don't wait 60s on a dead server
        if not is_ollama_available():
            raise ConnectionError("Ollama server not reachable at localhost:11434")

        ollama_results = generate_ollama_questions(
            skill=skill,
            resume_context=context,
            count=count,
        )

        valid_ollama = _filter_raw(ollama_results, is_dict=True)

        if len(valid_ollama) >= 1:
            print(
                f"[SUCCESS] Ollama generated {len(valid_ollama)} "
                f"question(s) for '{skill}'"
            )
            return valid_ollama[:count]

        print("[INFO] Ollama returned weak/empty questions — trying FLAN-T5")

    except ConnectionError as e:
        print(f"[INFO] Ollama not available: {e}")

    except Exception as e:
        print(f"[WARN] Ollama failed for '{skill}': {e}")

    # ─────────────────────────────────────────────────────────────
    # STAGE 2 — FLAN-T5 (local trained model)
    # ─────────────────────────────────────────────────────────────
    try:
        print(f"\n[INFO] Trying FLAN-T5 for skill: '{skill}' ...")

        skill_context = f"""
Skill: {skill}

Relevant resume details:
{context}

Generate interview questions ONLY for: {skill}

Focus on:
- technical concepts
- practical usage
- debugging scenarios
- project-based questions
- interview scenarios

Avoid:
- company history questions
- random unrelated technologies
- factual extraction questions
"""

        flan_raw = generate_flan_question(
            skill=skill,
            context=skill_context,
            count=count,
        )

        valid_flan = _filter_raw(flan_raw, is_dict=False)

        if len(valid_flan) >= 1:
            print(
                f"[SUCCESS] FLAN-T5 generated {len(valid_flan)} "
                f"question(s) for '{skill}'"
            )
            # Normalise FLAN plain strings → dict format
            return [
                {
                    "question":   q,
                    "difficulty": "medium",
                    "type":       "conceptual",
                }
                for q in valid_flan[:count]
            ]

        print("[INFO] FLAN-T5 returned weak questions — falling back to OpenRouter")

    except Exception as e:
        print(f"[WARN] FLAN-T5 failed for '{skill}': {e}")

    # ─────────────────────────────────────────────────────────────
    # STAGE 3 — OPENROUTER (API fallback, last resort)
    # ─────────────────────────────────────────────────────────────
    print(f"\n[INFO] Using OpenRouter fallback for skill: '{skill}' ...")

    return generate_questions_openrouter(
        skill,
        context,
        count=count,
    )
