"""
core/skill_extractor.py
Loads skillNER once at startup and exposes extract_skills()
"""

import spacy
from spacy.matcher import PhraseMatcher
from skillNer.general_params import SKILL_DB
from skillNer.skill_extractor_class import SkillExtractor

# ── Load once at module level ─────────────────────────────
# This runs only once when Django starts, not on every request
print("[skillNER] Loading spaCy model...")
_nlp = None
_extractor = None

def _load():
    global _nlp, _extractor
    if _extractor is not None:
        return True
    try:
        _nlp = spacy.load("en_core_web_lg")
        _extractor = SkillExtractor(_nlp, SKILL_DB, PhraseMatcher)
        print("[skillNER] Ready.")
        return True
    except Exception as e:
        print(f"[skillNER] Load failed: {e}")
        return False


def extract_skills(text: str) -> list:
    """
    Extract skills from any text using skillNER.
    Returns deduplicated list of skill strings.
    Falls back to empty list on error.
    """
    if not _load():
        return []

    try:
        annotations = _extractor.annotate(text)
        skills = []
        seen = set()

        # Full matches — high confidence
        for result in annotations['results']['full_matches']:
            skill = result['doc_node_value'].strip()
            if skill.lower() not in seen and len(skill) > 1:
                skills.append(skill)
                seen.add(skill.lower())

        # Partial/ngram matches — only if score > 0.7
        for result in annotations['results']['ngram_scored']:
            skill = result['doc_node_value'].strip()
            score = result.get('score', 0)
            if (
                score > 0.7
                and skill.lower() not in seen
                and len(skill) > 1
            ):
                skills.append(skill)
                seen.add(skill.lower())

        return skills

    except Exception as e:
        print(f"[skillNER] Extraction error: {e}")
        return []