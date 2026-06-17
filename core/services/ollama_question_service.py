"""
core/services/ollama_question_service.py

Generates interview questions using a locally running Ollama model.
Ollama runs 100% offline — no API key, no internet needed.

Setup (one-time):
    1. Install Ollama: https://ollama.com/download
    2. Pull a model (choose ONE based on your RAM):
         ollama pull mistral          # 4GB RAM  — best quality
         ollama pull llama3.2         # 2GB RAM  — good balance
         ollama pull phi3             # 2GB RAM  — fast + smart
         ollama pull tinyllama        # 1GB RAM  — minimum spec
    3. Ollama runs automatically at http://localhost:11434
"""

import requests
import json
import os

# ── CONFIG ────────────────────────────────────────────────────────
# Change OLLAMA_MODEL to whichever model you pulled.
# Priority recommendation: mistral > llama3.2 > phi3 > tinyllama
OLLAMA_HOST  = os.getenv("OLLAMA_HOST",  "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
OLLAMA_TIMEOUT = 120  # seconds — local inference can be slow on CPU

# ── BAD PATTERN FILTER ────────────────────────────────────────────
# Shared bad patterns — same strictness as the old MT5 filter
BAD_PATTERNS = [
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
    "mainframe",
    "necessary response",
    "what type of experience",
    "personal information",
    "candidate name",
    "email address",
    "phone number",
    "which company",
    "where did you",
]


def _is_valid_question(q: str) -> bool:
    """Return True if the question passes quality checks."""
    q = q.strip()
    if len(q.split()) < 6:
        return False
    if not q.endswith("?"):
        # Allow questions that don't end with ? but are clearly questions
        lower = q.lower()
        if not any(lower.startswith(w) for w in [
            "explain", "describe", "how", "what", "why", "when",
            "compare", "discuss", "demonstrate", "write", "implement",
            "can you", "could you", "give an example"
        ]):
            return False
    q_lower = q.lower()
    if any(bad in q_lower for bad in BAD_PATTERNS):
        return False
    return True


def _parse_questions(raw_text: str, count: int) -> list:
    """
    Parse numbered or bulleted question list from Ollama output.
    Returns up to `count` clean question strings.
    """
    questions = []
    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue

        # Strip numbering: "1.", "1)", "Q1.", "- ", "* ", "• "
        import re
        line = re.sub(r'^(Q?\d+[\.\)]\s*|[-\*•]\s*)', '', line).strip()

        if _is_valid_question(line):
            questions.append(line)

        if len(questions) >= count:
            break

    return questions


def generate_ollama_questions(
    skill: str,
    resume_context: str,
    count: int = 5
) -> list:
    """
    Generate `count` interview questions for `skill` using local Ollama.

    Returns a list of dicts:
        [{"question": "...", "difficulty": "medium", "type": "conceptual"}, ...]

    Raises requests.exceptions.ConnectionError if Ollama is not running.
    """

    prompt = f"""You are a senior technical interviewer conducting a software engineering interview.

Candidate background (from resume):
{resume_context[:800]}

Generate EXACTLY {count} interview questions for the skill: {skill}

Rules:
- Every question must be directly about {skill}
- Mix question types: conceptual, practical, scenario-based, debugging
- Questions must be clear and answerable in an interview setting
- Base some questions on the candidate's actual projects/experience above
- Do NOT ask about personal details, company names, or unrelated technologies
- Do NOT include answers, explanations, or any extra text
- Output ONLY a numbered list of questions, nothing else

Example format:
1. Explain how {skill} handles memory management internally.
2. Describe a situation where you used {skill} to solve a real problem.
3. What are the key differences between {skill} and its alternatives?

Now generate {count} questions for {skill}:"""

    try:
        response = requests.post(
            url=f"{OLLAMA_HOST}/api/generate",
            headers={"Content-Type": "application/json"},
            data=json.dumps({
                "model":  OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature":   0.7,
                    "top_p":         0.9,
                    "top_k":         40,
                    "repeat_penalty": 1.2,
                    "num_predict":   512,
                }
            }),
            timeout=OLLAMA_TIMEOUT
        )
        response.raise_for_status()
        result = response.json()
        raw_text = result.get("response", "").strip()

        if not raw_text:
            raise ValueError("Ollama returned empty response")

        print(f"[Ollama] Raw output for '{skill}':\n{raw_text[:300]}")

        questions = _parse_questions(raw_text, count)

        if not questions:
            raise ValueError(f"Ollama output had no valid questions for '{skill}'")

        # Normalize into the same dict format used by OpenRouter
        normalized = []
        for q in questions:
            q_lower = q.lower()
            # Guess type from question wording
            if any(w in q_lower for w in ["debug", "fix", "error", "issue", "problem"]):
                qtype = "debugging"
            elif any(w in q_lower for w in ["implement", "write", "code", "build"]):
                qtype = "coding"
            elif any(w in q_lower for w in ["project", "experience", "used", "worked"]):
                qtype = "project-based"
            elif any(w in q_lower for w in ["scenario", "situation", "if you", "would you"]):
                qtype = "scenario"
            else:
                qtype = "conceptual"

            normalized.append({
                "question":   q,
                "difficulty": "medium",
                "type":       qtype,
            })

        return normalized

    except requests.exceptions.ConnectionError:
        print(
            f"[Ollama] NOT RUNNING — start Ollama with: ollama serve\n"
            f"         Then pull a model: ollama pull {OLLAMA_MODEL}"
        )
        raise

    except requests.exceptions.Timeout:
        print(f"[Ollama] Timeout after {OLLAMA_TIMEOUT}s for skill '{skill}'")
        raise

    except Exception as e:
        print(f"[Ollama] Error for skill '{skill}': {e}")
        raise


def is_ollama_available() -> bool:
    """Quick health check — returns True if Ollama is running."""
    try:
        r = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=3)
        return r.status_code == 200
    except Exception:
        return False
