"""
core/resume_parser.py

Parses a raw resume text (from OCR) into structured sections:
  - Personal Info (name, email, phone, linkedin)
  - Summary / Objective
  - Skills
  - Experience / Projects
  - Education
  - Certifications
  - Achievements / Awards

Returns a dict with each heading as a key and content as value.
"""

import re
from typing import Dict, List, Optional

import re
from core.skill_extractor import extract_skills as nlp_extract_skills
def extract_name(text):

    lines = [
        line.strip()
        for line in text.split('\n')
        if line.strip()
    ]

    SKIP_WORDS = {
        'resume', 'cv', 'curriculum', 'vitae', 'profile',
        'contact', 'address', 'career', 'objective', 'summary',
        'email', 'phone', 'mobile', 'linkedin', 'github',
        'portfolio', 'declaration', 'reference'
    }

    for line in lines[:10]:

        # skip if contains email
        if '@' in line:
            continue

        # skip if contains phone number
        if re.search(r'\d{5,}', line):
            continue

        # skip if contains url
        if 'http' in line.lower() or 'www.' in line.lower():
            continue

        # skip if contains skip words
        lower = line.lower()
        if any(w in lower for w in SKIP_WORDS):
            continue

        # skip if contains special chars like : / |
        if re.search(r'[:/|\\]', line):
            continue

        # clean and check word count
        words = line.split()
        clean_words = [w.replace('.', '').replace(',', '') for w in words]

        if (
            2 <= len(clean_words) <= 5
            and all(
                w.isalpha() and len(w) >= 1
                for w in clean_words
            )
        ):
            return line.title()

    return "Unknown Candidate"
# ── Section heading patterns ──────────────────────────────────────────────────
# Order matters — more specific patterns first
SECTION_PATTERNS = [

    (
        "summary",
        r"^(summary|profile|objective|career objective|about me|professional summary)\s*[:\-]?$"
    ),

    (
        "education",
        r"^(education|academic details|qualification|academics?|educational background)\s*[:\-]?$"
    ),

    (
        "skills",
        r"^(skills?|technical skills?|additional skills?|tools|libraries|frameworks?|core subjects?|database|key skills|competencies)\s*[:\-]?$"
    ),

    (
        "experience",
        r"^(experience|work experience|professional experience|internships?|training|employment|work history|job experience|hands on experience|hands on experience|Teaching Experience|Research Experience|Research & Teaching Experience|PROFESSIONAL EXPERIENCE)\s*[:\-]?$"
    ),

    (
        "projects",
        r"^(projects?|portfolio|applications?|personal projects?|academic projects?)\s*[:\-]?$"
    ),

    (
        "certifications",
        r"^(certifications?|courses?|certificates?|training|online courses?)\s*[:\-]?$"
    ),

    (
        "achievements",
        r"^(achievements?|awards?|honours?|honors?|accomplishments?)\s*[:\-]?$"
    ),

    (
        "languages",
        r"^(languages?|language proficiency)\s*[:\-]?$"
    ),
]
# ── Universal date range pattern ──────────────────────────────────────
# Matches: "Sep 2022 – Dec 2022", "2020-present", "2021-2025",
#          "Dec. 2024 - Present", standalone "2023"
DATE_RANGE_RE = re.compile(
    r'(?:'
        r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*\d{4}'
        r'|\d{4}'
    r')'
    r'\s*[-–—]\s*'
    r'(?:'
        r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*\d{4}'
        r'|\d{4}'
        r'|present|now|current'
    r')'
    r'|\b\d{4}\b(?!\s*[-–—])',
    re.IGNORECASE
)

def _clean(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(
        r'([a-z])\.([A-Z])',
        r'\1.\n\2',
        text
    )
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_personal_info(text: str) -> Dict[str, str]:
    """Extract name, email, phone, linkedin from top of resume."""
    info = {}

    # Email
    email_match = re.search(r"[\w.\-+]+@[\w.\-]+\.\w{2,}", text)
    if email_match:
        info["email"] = email_match.group()

    # Phone
    phone_match = re.search(r"(\+?\d[\d\s\-\(\)]{8,14}\d)", text)
    if phone_match:
        raw = phone_match.group().strip()
        if len(re.sub(r"\D", "", raw)) >= 7:
            info["phone"] = raw

    # LinkedIn
    linkedin = re.search(r"linkedin\.com/in/[\w\-]+", text, re.IGNORECASE)
    if linkedin:
        info["linkedin"] = linkedin.group()

    # GitHub
    github = re.search(r"github\.com/[\w\-]+", text, re.IGNORECASE)
    if github:
        info["github"] = github.group()

    # Name — first non-empty line that looks like a name (2-4 words, Title Case)
    # Name extraction

    for line in text.splitlines()[:10]:

        line = line.strip()

        if (

            line

            and "@" not in line
            and ":" not in line
            and not any(

             word in line.lower()

                for word in [

                    "resume",
                    "cv",
                    "curriculum",
                    "vitae",
                    "profile",
                    "contact",
                    "address",
                    "career",
                    "objective",
                    "summary",
                    "profile",
                    "resume",
                    "contact"
                ]
            )

            and 1 < len(line.split()) <= 4
        ):

            info["name"] = line.title()
            break

    return info


def _split_into_sections(text: str) -> Dict[str, str]:
    """
    Split resume text into sections by detecting heading lines.
    Returns {section_key: content_text}
    """
    lines  = text.splitlines()
    result = {}

    # Build a flat regex that matches any heading
    all_pattern = "|".join(
        f"(?P<{key}>{pat})" for key, pat in SECTION_PATTERNS
    )
    heading_re = re.compile(
        r"^\s*(" + all_pattern + r")\s*[:\-]?\s*$",
        re.IGNORECASE
    )

    current_section = "header"
    current_lines: List[str] = []

    for raw_line in lines:
        line = raw_line.strip()

        line = line.replace(
            "–",
            "-"
        )

        line = re.sub(
            r"\s+",
            " ",
            line
        )
        normalized = line.lower().strip()

        normalized = re.sub(
            r'[^a-z0-9\s:\-\+]',
            '',
            normalized
        )
        # Strip decorators like ---, ===, ●, *, |, ─ from both ends
        normalized = re.sub(r'^[\s\-=_\*\|•─►]+', '', normalized)
        normalized = re.sub(r'[\s\-=_\*\|•─►]+$', '', normalized)
        normalized = normalized.strip()
        # Normalize "hands-on" variations
        normalized = normalized.replace("hands-on", "hands on")
        match = heading_re.match(normalized)

        # Handle inline heading: "Skills: Python, Java, C++"
        if not match:
            inline_found = False
            for key, pat in SECTION_PATTERNS:
                inline = re.match(
                    pat.replace('$', r'\s*[:\-]\s*(.+)$'),
                    normalized,
                    re.IGNORECASE
                )
                if inline:
                    content = "\n".join(current_lines).strip()
                    if content:
                        if current_section in result:
                            result[current_section] += "\n" + content
                        else:
                            result[current_section] = content
                    current_section = key
                    current_lines = [inline.group(inline.lastindex)]
                    inline_found = True
                    break
            if not inline_found:
                current_lines.append(raw_line.strip())
            continue
        if match:
            # Save previous section
            content = "\n".join(current_lines).strip()
            if content:
                if current_section in result:
                    result[current_section] += "\n" + content
                else:
                    result[current_section] = content

            # Find which group matched
            for key, _ in SECTION_PATTERNS:
                if match.group(key):
                    current_section = key
                    current_lines   = []
                    break
        else:
            current_lines.append(
                raw_line.strip()
            )

    # Save last section
    content = "\n".join(current_lines).strip()
    if content:
        if current_section in result:
            result[current_section] += "\n" + content
        else:
            result[current_section] = content

    return result

def _extract_projects(text: str) -> list:
    """
    Parse projects section into structured entries.
    Splits projects based on detecting a NEW project title line —
    identified by a line containing a date range (since every
    project title in practice ends with "Month YYYY – Month YYYY").
    """
    if not text:
        return []


    lines = [l.strip() for l in text.split('\n') if l.strip()]

    entries  = []
    current  = None

    for line in lines:
        # Clean bullet symbols
        cleaned = re.sub(r'^[∗–—•\-\*\+►→▪▸]\s*', '', line).strip()
        cleaned = re.sub(r'^[e¢©@]\s+', '', cleaned).strip()
        if not cleaned:
            continue

        lower = cleaned.lower()
        date_match = DATE_RANGE_RE.search(cleaned)

        # A line with a date range AND it's not an "Instructor:" line
        # is treated as a NEW project title
        is_new_project = (
            date_match is not None
            and "instructor" not in lower
            and not lower.startswith("tools used")
        )

        if is_new_project:
            # Save previous project
            if current:
                entries.append(current)

            date = date_match.group(0).strip()
            name = DATE_RANGE_RE.sub('', cleaned).strip(" ,–-:")

            current = {
                "name":        name,
                "date":        date,
                "tools":       "",
                "link":        "",
                "description": "",
            }
            continue

        if current is None:
            # First line before any date-bearing title — treat as name
            current = {
                "name":        cleaned,
                "date":        "",
                "tools":       "",
                "link":        "",
                "description": "",
            }
            continue

        # Instructor line — skip, not useful for display
        if "instructor" in lower:
            continue

        # Tools used line
        if "tools used" in lower or lower.startswith("tools:") or lower.startswith("tech:"):
            if ":" in cleaned:
                current["tools"] = cleaned.split(":", 1)[1].strip()
            continue

        # GitHub or URL line
        if "github.com" in lower or "http" in lower:
            current["link"] = cleaned
            continue

        # Everything else → description (append, joined with space)
        if current["description"]:
            current["description"] += " " + cleaned
        else:
            current["description"] = cleaned

    if current:
        entries.append(current)

    # Filter out garbage entries
    filtered = []
    for e in entries:
        name = e.get("name", "").strip()
        if (
            name
            and len(name) > 3
            and len(name) < 150
            and "@" not in name
            and "github.com" not in name.lower()
        ):
            filtered.append(e)

    return filtered
def _parse_experience_structured(text: str) -> list:
    """
    Parse experience section into structured entries.
    Uses the same date-based splitting strategy as _extract_projects:
    a new entry starts whenever a line contains a date range.
    """
    if not text:
        return []


    lines = [l.strip() for l in text.split('\n') if l.strip()]

    entries = []
    current = None

    for line in lines:
        cleaned = re.sub(r'^[∗–—•\-\*\+►→▪▸]\s*', '', line).strip()
        cleaned = re.sub(r'^[e¢©@]\s+', '', cleaned).strip()
        if not cleaned:
            continue

        date_match = DATE_RANGE_RE.search(cleaned)

        if date_match:
            date  = date_match.group(0).strip()
            text_part = DATE_RANGE_RE.sub('', cleaned).strip(" ,–-:")

            # If current entry exists but has no bullets yet and no title set,
            # this date line is likely a sub-role under the same company
            # (e.g. company line already set, this is "Producer/Writer 2025-present")
            if (
                current
                and current.get("company")
                and not current.get("bullets")
                and not current.get("title")
            ):
                current["title"] = text_part
                current["date"]  = date
                continue

            # Otherwise it's a brand new entry
            if current:
                entries.append(current)

            current = {
                "title":   text_part,
                "company": "",
                "date":    date,
                "bullets": [],
            }
            continue

        if current is None:
            current = {
                "title":   cleaned,
                "company": "",
                "date":    "",
                "bullets": [],
            }
            continue

        # If company hasn't been set yet and this line doesn't look
        # like a bullet point (no prior bullets captured yet), treat
        # it as the company/location line
        if not current["company"] and not current["bullets"]:
            current["company"] = cleaned
            continue

        # Everything else is a bullet/responsibility
        current["bullets"].append(cleaned)

    if current:
        entries.append(current)

    # Filter garbage entries
    filtered = []
    for e in entries:
        title = e.get("title", "").strip()
        if title and len(title) > 2 and len(title) < 150:
            filtered.append(e)

    return filtered

def _parse_education_structured(text: str, ignore_keywords: list = None) -> list:
    """
    Parse education section into structured entries.
    Uses date-based splitting — a new entry starts when a line
    contains a date range OR when a line contains "GPA:" (which
    typically marks the start of a new institution block in this format).
    """
    if not text:
        return []

    ignore_keywords = ignore_keywords or []

    GPA_RE = re.compile(r'GPA\s*:?\s*[\d.]+', re.IGNORECASE)

    lines = [l.strip() for l in text.split('\n') if l.strip()]
    lines = [
        l for l in lines
        if not any(kw.lower() in l.lower() for kw in ignore_keywords)
        and len(l) > 1
    ]

    entries = []
    current = None

    for line in lines:
        cleaned = re.sub(r'^[∗–—•\-\*\+►→▪▸]\s*', '', line).strip()
        cleaned = re.sub(r'^[e¢©@]\s+', '', cleaned).strip()
        if not cleaned:
            continue

        has_gpa  = bool(GPA_RE.search(cleaned))
        has_date = bool(DATE_RANGE_RE.search(cleaned))

        # A line with GPA marks a new institution entry
        # (matches the pattern: "Worcester Polytechnic Institute GPA: 4")
        if has_gpa and not has_date:
            if current:
                entries.append(current)
            institution = GPA_RE.sub('', cleaned).strip(" ,–-:")
            current = {
                "degree":      "",
                "institution": institution,
                "year":        "",
                "details":     [],
            }
            continue

        # A line with a date range — this is the degree line
        if has_date:
            date_match = DATE_RANGE_RE.search(cleaned)
            year  = date_match.group(0).strip()
            degree = DATE_RANGE_RE.sub('', cleaned).strip(" ,–-:")

            if current and not current.get("degree"):
                # Attach degree+year to the current institution entry
                current["degree"] = degree
                current["year"]   = year
                continue
            else:
                # New entry (no institution line preceded it)
                if current:
                    entries.append(current)
                current = {
                    "degree":      degree,
                    "institution": "",
                    "year":        year,
                    "details":     [],
                }
                continue

        if current is None:
            current = {
                "degree":      "",
                "institution": cleaned,
                "year":        "",
                "details":     [],
            }
            continue

        # Everything else is a detail line
        current["details"].append(cleaned)

    if current:
        entries.append(current)

    return entries
def _join_continuation_lines(text: str, ignore_keywords: list = None) -> list:
    """
    Joins continuation lines that belong to the same bullet point.
    A new entry starts when a line begins with a bullet marker or
    looks like a date/title line.
    Lines that are clearly continuations (no bullet, no date, lowercase start)
    are appended to the previous entry.
    """
    if not text:
        return []

    ignore_keywords = ignore_keywords or []

    # Split into raw lines
    raw_lines = [l.strip() for l in text.split("\n") if l.strip()]

    # Filter ignored keywords
    if ignore_keywords:
        raw_lines = [
            l for l in raw_lines
            if not any(kw.lower() in l.lower() for kw in ignore_keywords)
            and len(l) > 1
        ]

    # Bullet/entry start patterns
    BULLET_MARKERS = re.compile(
        r'^[@©►→▪▸•\-\*\+e¢∗–—]\s+'   # bullet symbols
        r'|^\d+[\.\)]\s+'               # numbered list
        r'|^[A-Z][A-Z\s]{3,}$'         # ALL CAPS heading
        r'|^\w.*\b(19|20)\d{2}\s*[-–]', # year RANGE like "2020-present" or "2021-2025"
        re.IGNORECASE
    )

    entries = []
    current = ""

    for line in raw_lines:
        # Clean OCR bullet artifacts at start: 'e ', '¢ ', '@ ', '© '
        cleaned = re.sub(r'^[e¢©@]\s+', '', line).strip()
        cleaned = re.sub(r'^[•\-\*\+►→▪▸∗–—]\s*', '', cleaned).strip()
        if not cleaned:
            continue

        # Decide if this line starts a new entry
        is_new_entry = bool(BULLET_MARKERS.match(line))

        # Also treat as new entry if it starts with uppercase and
        # previous entry is already long enough
        if (
            not is_new_entry
            and current
            and len(current) > 60
            and cleaned[0].isupper()
            and not cleaned[0].isdigit()
        ):
            is_new_entry = True

        if is_new_entry:
            if current:
                entries.append(current.strip())
            current = cleaned
        else:
            # Continuation — append to current with a space
            if current:
                current = current + " " + cleaned
            else:
                current = cleaned

    if current:
        entries.append(current.strip())

    # Final cleanup — remove empty or too-short entries
    return [e for e in entries if len(e) > 2]
def parse_resume(text: str) -> Dict:
    """
    Main function. Returns structured resume dict:
    {
      "personal_info": {name, email, phone, linkedin, github},
      "summary":       str,
      "skills":        List[str],
      "experience":    str,
      "projects":      List[{name, description, technologies}],
      "education":     str,
      "certifications":str,
      "achievements":  str,
      "raw_sections":  Dict[str, str],   ← all detected sections raw
    }
    """
    name = extract_name(text)
    text     = _clean(text)
    personal = _extract_personal_info(text)
    sections = _split_into_sections(text)

    # Parse skills into list
    raw_skills = sections.get("skills", "")

    skill_list = []

    # Step 1: Try skillNER on dedicated skills section
    if raw_skills:
        skill_list = nlp_extract_skills(raw_skills)

    # Step 2: If nothing found, try skillNER on full resume text
    if not skill_list:
        skill_list = nlp_extract_skills(text[:2000])

    # Step 3: If skillNER still found nothing, fallback to regex
    if not skill_list:

        if not raw_skills:
            for section_key in ["education", "summary", "header"]:
                section_text = sections.get(section_key, "")
                skill_lines = []
                capture = False
                for line in section_text.splitlines():
                    lower = line.lower()
                    if any(kw in lower for kw in [
                        "technical skills", "tools", "libraries",
                        "framework", "database", "core subject", "skills"
                    ]):
                        if ':' in line:
                            after_colon = line.split(':', 1)[1].strip()
                            if after_colon:
                                skill_lines.append(after_colon)
                                capture = True
                                continue
                        capture = True
                    elif capture:
                        if re.match(
                            r'^[A-Z][a-z]+(\s+[A-Z][a-z]+)*\s*:?\s*$',
                            line
                        ):
                            break
                        skill_lines.append(line)
                if skill_lines:
                    raw_skills = "\n".join(skill_lines)
                    break

        IGNORE = {
            "tools", "libraries", "framework", "database",
            "core subject", "technical skills", "technical skill",
            "@ technical skills", "microsoft excel", "microsoft word"
        }

        if raw_skills:
            cleaned = raw_skills.replace(":", ",")
            parts = re.split(r"[,\n•\*\|]+", cleaned)
            for p in parts:
                p = p.strip(" \t.:()")
                lower = p.lower()
                if 2 < len(p) < 45 and lower not in IGNORE:
                    skill_list.append(p)

    # Parse projects
    project_text = sections.get("projects", "") 
    projects = _extract_projects(project_text) if project_text else []
    return {

        "personal_info": personal,
        "name": name,
        "email": personal.get("email", ""),
        "summary": "\n".join(
            sections.get("summary", [])
        ) if isinstance(
            sections.get("summary", []),
            list
        ) else sections.get(
            "summary",
            ""
        ).strip(),

        "skills": skill_list,

        "skills_raw": raw_skills.strip(),

        "experience": _join_continuation_lines(
            sections.get("experience", "")
        ),
        "experience_structured": _parse_experience_structured(
            sections.get("experience", "")
        ),
        "projects": [
            p.get("name", "")
            for p in projects
            if p.get("name")
        ],
        "projects_structured": [
            p for p in projects
            if p.get("name")
        ],
        "projects_raw": project_text,

        "education": _join_continuation_lines(
            sections.get("education", ""),
            ignore_keywords=[
                "hands-on experience", "technical skills",
                "tools :", "libraries :", "framework", "database :"
            ]
        ),
        "education_structured": _parse_education_structured(
            sections.get("education", ""),
            ignore_keywords=[
                "hands-on experience", "technical skills",
                "tools :", "libraries :", "framework", "database :"
            ]
        ),

        "certifications": [

            line.strip()

            for line in sections.get(
                "certifications",
                ""
            ).split("\n")

            if line.strip()
        ],

        "achievements": [

            line.strip()

            for line in sections.get(
                "achievements",
                ""
            ).split("\n")

            if (

                line.strip()

                and

                "tools used"
                not in line.lower()
            )
        ],

        "languages": [

            line.strip()

            for line in sections.get(
                "languages",
                ""
            ).split("\n")

            if line.strip()
        ],

        "raw_sections": sections
    }