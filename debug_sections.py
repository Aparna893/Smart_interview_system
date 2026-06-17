"""
Drop this file in your project root and run:
    python debug_sections.py path/to/resume.pdf

It prints the raw OCR text and then shows what each section heading
scanner finds, so we can see exactly why Projects/Experience are empty.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.ocr_service import extract_text_from_pdf, extract_section_lines

if len(sys.argv) < 2:
    print("Usage: python debug_sections.py <resume.pdf>")
    sys.exit(1)

text = extract_text_from_pdf(sys.argv[1])

print("=" * 60)
print("RAW OCR OUTPUT (first 3000 chars)")
print("=" * 60)
print(text[:3000])
print()

print("=" * 60)
print("HEADING LINES DETECTED (lines with <= 5 words, ALL CAPS or Title)")
print("=" * 60)
for i, line in enumerate(text.splitlines()):
    stripped = line.strip()
    if not stripped:
        continue
    upper = stripped.upper()
    KEYWORDS = [
        "EDUCATION","ACADEMIC","PROJECTS","PROJECT","EXPERIENCE","EMPLOYMENT",
        "WORK HISTORY","WORK EXPERIENCE","SKILLS","TECHNICAL SKILLS",
        "CERTIFICATIONS","CERTIFICATES","COURSES","TRAINING","ACHIEVEMENTS",
        "AWARDS","HONORS","LANGUAGES","TOOLS","SOFTWARE","TECHNOLOGIES",
        "SUMMARY","OBJECTIVE","PROFILE","INTERNSHIP","INTERNSHIPS",
    ]
    for kw in KEYWORDS:
        if kw in upper and len(stripped.split()) <= 5:
            print(f"  Line {i:3d}: {stripped!r}  [matched: {kw}]")
            break

print()
print("=" * 60)
print("SECTION EXTRACTION RESULTS")
print("=" * 60)

tests = [
    ("PROJECTS",       ["PROJECTS","PROJECT","PERSONAL PROJECTS","ACADEMIC PROJECTS","KEY PROJECTS","INTERNSHIP","INTERNSHIPS"]),
    ("EXPERIENCE",     ["EXPERIENCE","EMPLOYMENT","WORK HISTORY","WORK EXPERIENCE","PROFESSIONAL EXPERIENCE","INTERNSHIP","INTERNSHIPS"]),
    ("EDUCATION",      ["EDUCATION","ACADEMIC"]),
    ("CERTIFICATIONS", ["CERTIFICATIONS","CERTIFICATES","COURSES","TRAINING"]),
    ("LANGUAGES",      ["LANGUAGES","LANGUAGE PROFICIENCY"]),
    ("ACHIEVEMENTS",   ["ACHIEVEMENTS","AWARDS","HONORS"]),
]
for label, names in tests:
    result = extract_section_lines(text, names)
    print(f"\n{label}:")
    if result:
        for item in result:
            print(f"  • {item}")
    else:
        print("  (empty)")