import os
import re
import json
import tempfile
import asyncio
from concurrent.futures import ThreadPoolExecutor, wait
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import random
import cv2
import numpy as np
import pytesseract
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)
import pdfplumber
from pdf2image import convert_from_bytes, convert_from_path
from pdf2image.exceptions import PDFInfoNotInstalledError
import requests
import time
from core.resume_parser import parse_resume
from core.services.hybrid_question_service import (
    generate_questions as generate_ai_questions
)
try:
    import fitz
except ImportError:
    fitz = None

try:
    import edge_tts
except ImportError:
    edge_tts = None

try:
    from pymongo import MongoClient
except ImportError:
    MongoClient = None



# ---------------------------------------------------------------------------
# Shared JSON parser — used by both Groq and Gemini responses
# ---------------------------------------------------------------------------
def _parse_questions_json(raw):

    raw = re.sub(
        r"```(?:json)?",
        "",
        raw
    ).strip()

    match = re.search(
        r"\{.*\}",
        raw,
        re.DOTALL
    )

    if not match:

        raise ValueError(
            "Response did not contain JSON"
        )

    data = json.loads(match.group())

    result = {}

    for skill, qs in data.items():

        if not isinstance(qs, list):
            continue

        cleaned = []

        for q in qs:

            if isinstance(q, str):

                cleaned.append({

                    "question": q.strip(),

                    "difficulty": "medium",

                    "type": "conceptual"
                })

            elif isinstance(q, dict):

                cleaned.append({

                    "question": q.get(
                        "question",
                        ""
                    ).strip(),

                    "difficulty": q.get(
                        "difficulty",
                        "medium"
                    ),

                    "type": q.get(
                        "type",
                        "conceptual"
                    )
                })

        result[skill] = cleaned

    return result


# ---------------------------------------------------------------------------
# Question generation — shared prompt builder
# ---------------------------------------------------------------------------
def _build_question_prompt(skills: List[str], total: int) -> Tuple[str, str]:
    """Returns (system_prompt, user_prompt) for question generation."""
    skills_str = ", ".join(skills)
    system = (
        "You are an expert technical interviewer. "
        "Generate unique, non-repetitive interview questions. "
        "Return ONLY a valid JSON object — no explanation, no markdown fences. "
        "Format: {\"SkillName\": [\"question1\", \"question2\", ...], ...}"
    )
    user = (
        f"The candidate has the following skills: {skills_str}.\n\n"
        f"Generate a total of exactly {total} interview questions spread across all skills. "
        f"Distribute them proportionally — skills the candidate emphasises more get more questions. "
        f"For each skill include a mix of technical, conceptual, and situational questions. "
        f"Every question must be unique. Do not repeat any question across skills.\n\n"
        f"Return JSON only."
    )
    return system, user



# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
from core.openrouter_service import (

    generate_questions_openrouter,

    OPENROUTER_API_KEY,

    MODEL
)

def _normalize_skill_questions(questions, limit):

    normalized = []
    seen = set()

    for question in questions:

        if isinstance(question, str):
            text = question.strip()
            difficulty = "medium"
            question_type = "conceptual"

        elif isinstance(question, dict):
            text = str(
                question.get(
                    "question",
                    ""
                )
            ).strip()
            difficulty = question.get(
                "difficulty",
                "medium"
            )
            question_type = question.get(
                "type",
                "conceptual"
            )

        else:
            continue

        key = text.casefold()

        if not text or key in seen:
            continue

        seen.add(key)
        normalized.append({
            "question": text,
            "difficulty": difficulty,
            "type": question_type
        })

        if len(normalized) >= limit:
            break

    return normalized


def _build_skill_fallback_questions(skill):

    prompts = [
        (
            f"Explain the core concepts of {skill}.",
            "easy",
            "conceptual"
        ),
        (
            f"Describe a project where you used {skill}.",
            "medium",
            "project-based"
        ),
        (
            f"What are the common challenges when working with {skill}?",
            "medium",
            "scenario"
        ),
        (
            f"How would you debug an issue related to {skill}?",
            "medium",
            "scenario"
        ),
        (
            f"Write a small example demonstrating your knowledge of {skill}.",
            "medium",
            "coding"
        ),
        (
            f"What are the best practices for using {skill}?",
            "medium",
            "conceptual"
        ),
        (
            f"How would you improve the performance of a system using {skill}?",
            "hard",
            "scenario"
        ),
        (
            f"Compare {skill} with a relevant alternative.",
            "hard",
            "conceptual"
        ),
        (
            f"How would you test a feature implemented with {skill}?",
            "medium",
            "coding"
        ),
        (
            f"Describe an advanced use case for {skill}.",
            "hard",
            "project-based"
        ),
    ]

    return [
        {
            "question": question,
            "difficulty": difficulty,
            "type": question_type
        }
        for question, difficulty, question_type in prompts
    ]


def _generate_skill_question_pool(

    skill,

    resume_context,

    questions_per_skill
):

    questions = []

    for attempt in range(1):

        try:
            skill_context = f"""
            Generate professional technical interview questions
            for the skill: {skill}

            Candidate Resume Information:
            {resume_context}

            Focus ONLY on:

            * {skill}
            * practical usage
            * technical concepts
            * project experience
            * debugging knowledge
            * interview assessment

            Avoid:

            * company-history questions
            * factual extraction questions
            * generic HR questions
            * personal information questions

            Return only technical interview questions.
            """
            generated = generate_ai_questions(
                skill,
                skill_context,
                count=questions_per_skill
            )

            questions.extend(
                generated
            )

            normalized = _normalize_skill_questions(
                questions,
                questions_per_skill
            )

            if len(normalized) >= questions_per_skill:
                return normalized

        except Exception as e:

            print(
                f"Question generation attempt "
                f"{attempt + 1} failed for {skill}:",
                e
            )
            time.sleep(2)
    questions.extend(
        _build_skill_fallback_questions(
            skill
        )
    )

    return _normalize_skill_questions(
        questions,
        questions_per_skill
    )
def generate_questions(

    skills,

    projects,

    experience,

    max_questions=10
):

    questions_per_skill = 5
    selected_skills = []
    seen = set()
    ignored_skills = [

        "microsoft excel",
        "microsoft word",
        "excel",
        "word",
    ]
    for skill in skills:

        cleaned = str(skill).strip()
        if cleaned.lower() in ignored_skills:
            continue
        key = cleaned.casefold()

        if cleaned and key not in seen:
            selected_skills.append(
                cleaned
            )
            seen.add(key)

    if not selected_skills:
        selected_skills = [
            "General Programming"
        ]

    resume_context = (
        f"Projects:\n{projects}\n\n"
        f"Experience:\n{experience}"
    )
    generated = {}

    executor = ThreadPoolExecutor(
        max_workers=3
    )

    futures = {
        executor.submit(
            _generate_skill_question_pool,
            skill,
            resume_context,
            questions_per_skill
        ): skill
        for skill in selected_skills[:7]
    }

    completed, pending = wait(
        futures,
        timeout=180
    )

    for future in completed:

        skill = futures[future]

        try:
            generated[skill] = future.result()

        except Exception as e:
            print(
                f"Question generation failed "
                f"for {skill}:",
                e
            )
            generated[skill] = []

    timed_out_skills = []
    for future in pending:
        skill = futures[future]
        future.cancel()
        print(f"Question generation timed out for {skill} — will retry")
        timed_out_skills.append(skill)

    executor.shutdown(wait=False, cancel_futures=True)

    # Retry timed-out skills one at a time (sequential, no competition)
    if timed_out_skills:
        print(f"[INFO] Retrying {len(timed_out_skills)} timed-out skill(s) sequentially...")
        for skill in timed_out_skills:
            try:
                generated[skill] = _generate_skill_question_pool(
                    skill,
                    resume_context,
                    questions_per_skill
                )
                print(f"[RETRY SUCCESS] {skill}")
            except Exception as e:
                print(f"[RETRY FAILED] {skill}: {e}")
                generated[skill] = []

    return {
        skill: generated[skill]
        for skill in selected_skills[:7]
        if skill in generated
    } 
# ---------------------------------------------------------------------------
# OCR helpers
# ---------------------------------------------------------------------------
def extract_text_from_image(image_path: str) -> str:
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"Could not open image: {image_path}")
    return extract_text_from_image_array(image)

def extract_text_with_layout(pdf_bytes):
    import io
    full_text = []

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:

            words = page.extract_words(
                x_tolerance=3,
                y_tolerance=3,
                keep_blank_chars=False
            )

            if not words:
                text = page.extract_text()
                if text:
                    full_text.append(text)
                continue

            # Group words into lines by y-position
            lines = []
            current_line = []
            current_top = None

            for w in sorted(words, key=lambda x: (round(x['top'] / 8), x['x0'])):
                if current_top is None or abs(w['top'] - current_top) < 8:
                    current_line.append(w)
                    current_top = w['top']
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = [w]
                    current_top = w['top']
            if current_line:
                lines.append(current_line)

            # For each line detect if it has two columns
            page_mid = page.width / 2
            result_lines = []

            for line_words in lines:
                left = [w for w in line_words if w['x0'] < page_mid - 20]
                right = [w for w in line_words if w['x0'] >= page_mid - 20]

                if left and right:
                    left_text = ' '.join(w['text'] for w in sorted(left, key=lambda x: x['x0']))
                    right_text = ' '.join(w['text'] for w in sorted(right, key=lambda x: x['x0']))
                    # Keep on same line separated by tab so parser can read both
                    result_lines.append(left_text + '    ' + right_text)
                    # Also append right text on its own line so section headings are detected
                    result_lines.append(right_text)
                else:
                    # Single column line
                    result_lines.append(
                        ' '.join(w['text'] for w in sorted(line_words, key=lambda x: x['x0']))
                    )

            full_text.append('\n'.join(result_lines))

    return '\n'.join(full_text)
def _fix_merged_words(text: str) -> str:
    import re
    try:
        import wordninja
    except ImportError:
        wordninja = None

    def fix_line(line: str) -> str:
        words = line.split(" ")
        fixed_words = []
        for word in words:
            if len(word) >= 15 and word.isalpha() and wordninja:
                split = wordninja.split(word)
                # Only use split result if it produced multiple real words
                if len(split) > 1:
                    fixed_words.append(" ".join(split))
                    continue
            fixed_words.append(word)
        return " ".join(fixed_words)

    return "\n".join(fix_line(line) for line in text.split("\n"))
def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """
    Extract text from PDF bytes with smart two-column layout detection.
    Dynamically finds the actual column boundary instead of assuming page midpoint.
    Falls back to Tesseract OCR if pdfplumber gives empty/garbage text.
    """
    import pdfplumber
    import io

    full_text = []

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:

                words = page.extract_words(
                    x_tolerance=3,
                    y_tolerance=3,
                    keep_blank_chars=False
                )

                if not words:
                    # ── OCR fallback for scanned/image PDFs ──────────
                    try:
                        import pytesseract

                        TESSERACT_PATH = os.getenv(
                            "TESSERACT_PATH",
                            r"C:\Program Files\Tesseract-OCR\tesseract.exe"
                        )
                        pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

                        img = page.to_image(resolution=300).original
                        ocr_text = pytesseract.image_to_string(img, lang="eng")
                        if ocr_text.strip():
                            full_text.append(ocr_text.strip())

                    except Exception as ocr_err:
                        print(f"[OCR] Tesseract fallback failed: {ocr_err}")
                    continue

                # ── Detect if two-column layout ───────────────────────
                # ── Detect if two-column layout ───────────────────────
                # A real two-column resume has MANY lines where BOTH
                # left and right sides have text at the SAME y-position.
                # A single-column resume with right-aligned dates only
                # has occasional words on the right, not full text blocks.
                page_mid = page.width / 2

                # Group words into rows by y-position
                rows = {}
                for w in words:
                    row_key = round(w["top"] / 5)
                    rows.setdefault(row_key, []).append(w)

                two_col_rows = 0
                total_rows   = len(rows)

                for row_words in rows.values():
                    left_in_row  = [w for w in row_words if w["x0"] < page_mid - 30]
                    right_in_row = [w for w in row_words if w["x0"] > page_mid + 30]

                    # A row counts as "two-column" only if BOTH sides
                    # have substantial text (3+ words), not just 1-2
                    # words (which is just a right-aligned date/label)
                    if len(left_in_row) >= 3 and len(right_in_row) >= 3:
                        two_col_rows += 1

                # Real two-column layout = majority of rows have
                # independent text blocks on both sides
                is_two_col = (
                    total_rows > 0
                    and (two_col_rows / total_rows) > 0.6
                )

                # ── Try simple single-column extraction FIRST ────────
                single = page.extract_text(x_tolerance=3, y_tolerance=3) or ""

                # Only attempt column-split if single-column result
                # looks suspicious (e.g. way shorter than expected,
                # or has many very long lines that suggest column merge)
                avg_line_len = (
                    sum(len(l) for l in single.split("\n")) / max(len(single.split("\n")), 1)
                )

                looks_merged = avg_line_len > 110  # unusually long lines = likely merged columns

                if is_two_col and looks_merged:
                    # Find the actual gap between columns
                    x_coords    = sorted([w["x0"] for w in words])
                    middle_zone = [
                        x for x in x_coords
                        if page.width * 0.3 < x < page.width * 0.7
                    ]

                    col_boundary = page_mid
                    if middle_zone:
                        max_gap = 0
                        for i in range(1, len(middle_zone)):
                            gap = middle_zone[i] - middle_zone[i - 1]
                            if gap > max_gap:
                                max_gap      = gap
                                col_boundary = (middle_zone[i] + middle_zone[i - 1]) / 2

                    left_text = page.within_bbox(
                        (0, 0, col_boundary, page.height)
                    ).extract_text(x_tolerance=3, y_tolerance=3) or ""

                    right_text = page.within_bbox(
                        (col_boundary, 0, page.width, page.height)
                    ).extract_text(x_tolerance=3, y_tolerance=3) or ""

                    combined = []
                    if left_text.strip():
                        combined.append(left_text.strip())
                    if right_text.strip():
                        combined.append(right_text.strip())
                    full_text.append("\n\n".join(combined))

                elif single.strip():
                    full_text.append(single.strip())

                else:
                    # ── OCR fallback for scanned/image PDFs ──────────
                    try:
                        import pytesseract

                        TESSERACT_PATH = os.getenv(
                            "TESSERACT_PATH",
                            r"C:\Program Files\Tesseract-OCR\tesseract.exe"
                        )
                        pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

                        img = page.to_image(resolution=300).original
                        ocr_text = pytesseract.image_to_string(img, lang="eng")
                        if ocr_text.strip():
                            full_text.append(ocr_text.strip())

                    except Exception as ocr_err:
                        print(f"[OCR] Tesseract fallback failed: {ocr_err}")

    except Exception as e:
        print(f"[PDF] pdfplumber failed: {e}")

    result = "\n\n".join(full_text).strip()
    result = _fix_merged_words(result)
    return result

   


def _fix_broken_lines(text: str) -> str:
    """
    Fix common OCR/PDF extraction issues:
    - Lines broken mid-sentence get joined
    - Preserve intentional paragraph breaks
    - Remove garbage characters
    """
    import re

    lines   = text.split("\n")
    output  = []
    buffer  = ""

    # Patterns that indicate a line is COMPLETE (don't join to next)
    COMPLETE_LINE = re.compile(
        r'[.!?:]\s*$'           # ends with punctuation
        r'|\d{4}\s*$'           # ends with year
        r'|^\s*$',              # blank line
        re.IGNORECASE
    )

    # Patterns that indicate start of a NEW section/entry (don't merge)
    NEW_ENTRY = re.compile(
        r'^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)'
        r'|^\d{4}'              # starts with year
        r'|^[A-Z][A-Z\s]{4,}$' # ALL CAPS heading
        r'|^(education|experience|skills|projects|certifications|'
        r'summary|objective|profile|achievements)',
        re.IGNORECASE
    )

    for line in lines:
        stripped = line.strip()

        # Blank line → flush buffer as paragraph break
        if not stripped:
            if buffer:
                output.append(buffer.strip())
                buffer = ""
            output.append("")
            continue

        # New section heading or entry → flush and start fresh
        if NEW_ENTRY.match(stripped) and buffer:
            output.append(buffer.strip())
            buffer = stripped
            continue

        # If buffer is empty, start it
        if not buffer:
            buffer = stripped
            continue

        # If current buffer ends with punctuation or is a complete thought
        if COMPLETE_LINE.search(buffer):
            output.append(buffer.strip())
            buffer = stripped
            continue

        # Otherwise join to buffer (broken line continuation)
        buffer = buffer + " " + stripped

    # Flush remaining
    if buffer:
        output.append(buffer.strip())

    # Clean up multiple blank lines
    result = "\n".join(output)
    result = re.sub(r'\n{3,}', '\n\n', result)

    return result.strip()

def extract_text_from_image_array(image: Any) -> str:
    if image is None:
        raise ValueError("Invalid image data")
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    cleaned = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15
    )
    pil_image = cv2.cvtColor(cleaned, cv2.COLOR_GRAY2BGR)
    text = pytesseract.image_to_string(pil_image, lang="eng")
    return text.strip()


def _render_pdf_with_fitz(pdf_source: bytes, dpi: int = 150):
    if fitz is None:
        raise RuntimeError(
            "PDF rendering via PyMuPDF is unavailable. Install with `pip install pymupdf`."
        )
    doc = fitz.open(stream=pdf_source, filetype="pdf")
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    images = []
    for page in doc:
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = np.frombuffer(pix.samples, dtype=np.uint8)
        img = img.reshape(pix.height, pix.width, pix.n)
        if pix.n == 4:
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
        elif pix.n == 1:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        images.append(img)
    return images


def extract_text_from_pdf(pdf_path: str) -> str:
    try:
        pages = convert_from_path(pdf_path, dpi=300)
    except (PDFInfoNotInstalledError, OSError):
        if fitz is not None:
            with open(pdf_path, "rb") as f:
                pages = _render_pdf_with_fitz(f.read(), dpi=150)
        else:
            raise RuntimeError("Poppler not installed and PyMuPDF not available.")
    texts = []
    for page in pages:
        text = pytesseract.image_to_string(page, lang="eng")
        texts.append(text)
    return "\n\n".join(texts).strip()
 
def clean_text(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)

def extract_resume_sections(text):
    return parse_resume(text)

# ---------------------------------------------------------------------------
# TTS
# ---------------------------------------------------------------------------
def create_tts_audio(text: str, output_path: Optional[str] = None) -> str:
    if edge_tts is None:
        raise RuntimeError("edge-tts is not installed. Run: pip install edge-tts")
    if output_path is None:
        output_path = os.path.join(
            tempfile.gettempdir(), f"ocr_tts_{int(datetime.now().timestamp())}.mp3"
        )
    os.makedirs(
        os.path.dirname(output_path),
        exist_ok=True
    )
    communicate = edge_tts.Communicate(
        text,
        "en-US-AriaNeural"
    )
    asyncio.run(
        communicate.save(output_path)
    )
    return output_path


# ---------------------------------------------------------------------------
# MongoDB
# ---------------------------------------------------------------------------
def save_to_mongo(
    record: Dict[str, Any],
    mongo_uri: Optional[str] = None,
    db_name: str = "ocr_qna",
    collection_name: str = "sessions",
) -> str:
    if MongoClient is None:
        raise RuntimeError("pymongo is not installed. Run: pip install pymongo")
    mongo_uri = mongo_uri or os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    collection = client[db_name][collection_name]
    insert_result = collection.insert_one(record)
    return str(insert_result.inserted_id)


def build_session_record(
    filename: str,
    source_type: str,
    extracted_text: str,
    questions: str,
    model_name: str,
    max_questions: int,
    saved_audio_path: Optional[str] = None,
    detected_skills: Optional[List[str]] = None,
) -> Dict[str, Any]:
    record = {
        "filename": filename,
        "source_type": source_type,
        "model_name": model_name,
        "requested_questions": max_questions,
        "extracted_text": extracted_text,
        "generated_questions": questions,
        "detected_skills": detected_skills or [],
        "created_at": datetime.utcnow(),
    }
    if saved_audio_path:
        record["audio_path"] = saved_audio_path
    return record


def format_skill_questions(skill_questions):

    lines = []

    for skill, qs in skill_questions.items():

        lines.append(f"--- {skill} ---")

        for i, q in enumerate(qs, 1):

            lines.append(f"{i}. {q}")

        lines.append("")

    return "\n".join(lines).strip()

