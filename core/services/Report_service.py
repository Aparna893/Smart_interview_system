"""
core/services/report_service.py

Generates a clean professional resume summary report as PDF.
Layout:
  - Header: Name + Position + Contact
  - One-Line Summary (Ollama generated)
  - Skills grid
  - Work Experience
  - Projects
  - Education
  - Certifications (if any)
"""

import io
import json
from annotated_types import doc
import requests
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, black
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    HRFlowable, Table, TableStyle, ListFlowable, ListItem
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY, TA_RIGHT
from wandb import summary

from core.services.ollama_question_service import (
    OLLAMA_HOST,
    OLLAMA_MODEL,
    OLLAMA_TIMEOUT,
    is_ollama_available,
)

# ── COLORS ────────────────────────────────────────────────────────
BLUE       = HexColor("#2563eb")
DARK       = HexColor("#111827")
GRAY       = HexColor("#6b7280")
LIGHT_GRAY = HexColor("#f3f4f6")
MID_GRAY   = HexColor("#d1d5db")
GREEN      = HexColor("#16a34a")
WHITE      = HexColor("#ffffff")
LIGHT_BLUE = HexColor("#eff6ff")


# ── SUMMARY GENERATION ───────────────────────────────────────────

def _generate_summary_ollama(interview: dict) -> str:
    """Generate structured bullet-point summary."""

    name       = interview.get("name", "Candidate")
    skills     = interview.get("skills", [])
    experience = interview.get("experience", [])
    projects   = interview.get("projects", [])
    education  = interview.get("education", [])

    # Build education string
    edu_str = education[0] if education else "Not specified"

    # Build experience string
    exp_str = experience[0] if experience else "Fresher"

    # Build projects string
    proj_str = ", ".join(projects[:3]) if projects else "None"

    # Split skills into categories
    FRAMEWORKS = {"flask", "django", "react", "angular", "vue", "spring", "express"}
    LIBRARIES  = {"numpy", "pandas", "matplotlib", "seaborn", "scikit-learn",
                  "tensorflow", "keras", "pytorch"}
    DATABASES  = {"mysql", "mongodb", "postgresql", "sqlite", "oracle", "redis"}

    tech_skills = []
    frameworks  = []
    libraries   = []
    databases   = []

    for s in skills:
        sl = s.lower()
        if sl in FRAMEWORKS:
            frameworks.append(s.title())
        elif sl in LIBRARIES:
            libraries.append(s.title())
        elif sl in DATABASES:
            databases.append(s.title())
        else:
            tech_skills.append(s.title())

    prompt = (
        f"Generate a structured resume summary in this EXACT format:\n\n"
        f"Name: {name}\n"
        f"Education: [degree and university in one line]\n"
        f"Technical Skills: [comma separated core skills]\n"
        f"Frameworks: [comma separated frameworks if any]\n"
        f"Libraries: [comma separated libraries if any]\n"
        f"Database: [comma separated databases if any]\n"
        f"Experience: [job title and company in one line]\n"
        f"Projects: [comma separated project names]\n\n"
        f"Use ONLY this data — do not add anything extra:\n"
        f"Name: {name}\n"
        f"Education: {edu_str}\n"
        f"Technical Skills: {', '.join(tech_skills[:6])}\n"
        f"Frameworks: {', '.join(frameworks)}\n"
        f"Libraries: {', '.join(libraries)}\n"
        f"Database: {', '.join(databases)}\n"
        f"Experience: {exp_str}\n"
        f"Projects: {proj_str}\n\n"
        f"Output ONLY the formatted lines above, nothing else."
    )

    try:
        response = requests.post(
            url=f"{OLLAMA_HOST}/api/generate",
            headers={"Content-Type": "application/json"},
            data=json.dumps({
                "model":  OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature":    0.1,
                    "repeat_penalty": 1.2,
                    "num_predict":    200,
                }
            }),
            timeout=OLLAMA_TIMEOUT
        )
        response.raise_for_status()
        text = response.json().get("response", "").strip()
        if text and len(text) > 30:
            return text
    except Exception as e:
        print(f"[ReportService] Ollama summary failed: {e}")

    return _generate_summary_template(interview)

def _generate_summary_template(interview: dict) -> str:
    """Structured template fallback."""
    name       = interview.get("name", "Candidate")
    skills     = interview.get("skills", [])
    experience = interview.get("experience", [])
    projects   = interview.get("projects", [])
    education  = interview.get("education", [])

    FRAMEWORKS = {"flask", "django", "react", "angular", "vue", "spring"}
    LIBRARIES  = {"numpy", "pandas", "matplotlib", "seaborn", "scikit-learn",
                  "tensorflow", "keras", "pytorch"}
    DATABASES  = {"mysql", "mongodb", "postgresql", "sqlite", "oracle"}

    tech_skills, frameworks, libraries, databases = [], [], [], []
    for s in skills:
        sl = s.lower()
        if sl in FRAMEWORKS:   frameworks.append(s.title())
        elif sl in LIBRARIES:  libraries.append(s.title())
        elif sl in DATABASES:  databases.append(s.title())
        else:                  tech_skills.append(s.title())

    lines = [f"Name: {name}"]
    if education:
        lines.append(f"Education: {education[0]}")
    if tech_skills:
        lines.append(f"Technical Skills: {', '.join(tech_skills[:6])}")
    if frameworks:
        lines.append(f"Frameworks: {', '.join(frameworks)}")
    if libraries:
        lines.append(f"Libraries: {', '.join(libraries)}")
    if databases:
        lines.append(f"Database: {', '.join(databases)}")
    if experience:
        lines.append(f"Experience: {experience[0]}")
    if projects:
        lines.append(f"Projects: {', '.join(projects[:3])}")

    return "\n".join(lines)

def generate_summary_text(interview: dict) -> str:
    """Public — returns one-line summary as plain text."""
    if is_ollama_available():
        return _generate_summary_ollama(interview)
    return _generate_summary_template(interview)


# ── STYLES HELPER ────────────────────────────────────────────────

def _build_styles():
    base = getSampleStyleSheet()

    styles = {}

    styles["name"] = ParagraphStyle(
        "Name",
        fontSize=22,
        fontName="Helvetica-Bold",
        textColor=DARK,
        spaceAfter=2,
        leading=26,
    )
    styles["position"] = ParagraphStyle(
        "Position",
        fontSize=12,
        fontName="Helvetica",
        textColor=GRAY,
        spaceAfter=2,
        leading=16,
    )
    styles["contact"] = ParagraphStyle(
        "Contact",
        fontSize=9,
        fontName="Helvetica",
        textColor=GRAY,
        spaceAfter=0,
        leading=13,
    )
    styles["section_heading"] = ParagraphStyle(
        "SectionHeading",
        fontSize=11,
        fontName="Helvetica-Bold",
        textColor=BLUE,
        spaceBefore=14,
        spaceAfter=4,
        leading=14,
    )
    styles["summary_box"] = ParagraphStyle(
        "SummaryBox",
        fontSize=10,
        fontName="Helvetica-Oblique",
        textColor=DARK,
        spaceAfter=0,
        leading=16,
        alignment=TA_JUSTIFY,
    )
    styles["exp_title"] = ParagraphStyle(
        "ExpTitle",
        fontSize=10,
        fontName="Helvetica-Bold",
        textColor=DARK,
        spaceAfter=1,
        leading=14,
    )
    styles["exp_sub"] = ParagraphStyle(
        "ExpSub",
        fontSize=9,
        fontName="Helvetica-Oblique",
        textColor=GRAY,
        spaceAfter=3,
        leading=12,
    )
    styles["bullet"] = ParagraphStyle(
        "Bullet",
        fontSize=9,
        fontName="Helvetica",
        textColor=DARK,
        spaceAfter=2,
        leftIndent=10,
        leading=13,
    )
    styles["skill_chip"] = ParagraphStyle(
        "SkillChip",
        fontSize=9,
        fontName="Helvetica",
        textColor=BLUE,
        alignment=TA_CENTER,
        leading=12,
    )
    styles["footer"] = ParagraphStyle(
        "Footer",
        fontSize=8,
        fontName="Helvetica",
        textColor=GRAY,
        alignment=TA_CENTER,
        leading=10,
    )
    styles["ats_label"] = ParagraphStyle(
        "ATSLabel",
        fontSize=9,
        fontName="Helvetica-Bold",
        textColor=WHITE,
        alignment=TA_CENTER,
        leading=12,
    )
    styles["ats_score"] = ParagraphStyle(
        "ATSScore",
        fontSize=18,
        fontName="Helvetica-Bold",
        textColor=WHITE,
        alignment=TA_CENTER,
        leading=22,
    )
    styles["ats_verdict"] = ParagraphStyle(
        "ATSVerdict",
        fontSize=9,
        fontName="Helvetica",
        textColor=WHITE,
        alignment=TA_CENTER,
        leading=12,
    )
    return styles


# ── PDF GENERATION ───────────────────────────────────────────────

def generate_report_pdf(interview: dict) -> bytes:
    """
    Build and return the PDF as bytes.
    """
    summary = generate_summary_text(interview)
    buffer  = io.BytesIO()
    s       = _build_styles()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2*cm,
        rightMargin=2*cm,
        topMargin=1.8*cm,
        bottomMargin=1.8*cm,
    )

    story = []

    name        = interview.get("name", "Candidate")
    email       = interview.get("email", "")
    phone       = interview.get("phone", "")
    skills      = interview.get("skills", [])
    experience  = interview.get("experience", [])
    projects    = interview.get("projects", [])
    education   = interview.get("education", [])
    certs       = interview.get("certifications", [])
    ats_score   = interview.get("ats_score", 0)
    generated_on = datetime.now().strftime("%B %d, %Y")

    # ── HEADER ────────────────────────────────────────────────────
    # Name row with ATS score on the right
    ats_color = (GREEN if ats_score >= 70
                 else HexColor("#ea580c") if ats_score >= 50
                 else HexColor("#dc2626"))

    header_data = [[
        Paragraph(name, s["name"]),
        Paragraph(
            f'<font color="#2563eb"><b>{ats_score}%</b></font><br/>'
            f'<font color="#6b7280" size="8">ATS Score</font>',
            ParagraphStyle("ATSRight", fontSize=18, fontName="Helvetica-Bold",
                           textColor=BLUE, alignment=TA_RIGHT, leading=22)
        )
    ]]
    header_table = Table(header_data, colWidths=["75%", "25%"])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN",  (1, 0), (1, 0),  "RIGHT"),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.15*cm))

    # Contact line
    contact_parts = []
    if email: contact_parts.append(email)
    if phone: contact_parts.append(phone)
    contact_parts.append(f"Report: {generated_on}")
    story.append(Paragraph("  |  ".join(contact_parts), s["contact"]))
    story.append(Spacer(1, 0.2*cm))

    # Blue divider
    story.append(HRFlowable(
        width="100%", thickness=2,
        color=BLUE, spaceAfter=10
    ))

    # ── ONE-LINE SUMMARY BOX ──────────────────────────────────────
    # ── ONE-LINE SUMMARY BOX ──────────────────────────────────────
    story.append(Paragraph("Resume Summary", s["section_heading"]))

    formatted_summary = summary

    for heading in [
        "Name:",
        "Education:",
        "Technical Skills:",
        "Frameworks:",
        "Libraries:",
        "Database:",
        "Experience:",
        "Projects:"
    ]:
        formatted_summary = formatted_summary.replace(
            heading,
            f"<b>{heading}</b>"
        )

    formatted_summary = formatted_summary.replace("\n", "<br/>")

    summary_table = Table(
        [[Paragraph(formatted_summary, s["summary_box"])]],
        colWidths=["100%"]
    )
    summary_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), LIGHT_BLUE),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING",   (0, 0), (-1, -1), 14),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 14),
        ("ROUNDEDCORNERS", [6]),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.5*cm))

    story.append(HRFlowable(
        width="100%",
        thickness=1,
        color=BLUE,
        spaceAfter=5
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()
    # # ── SKILLS ────────────────────────────────────────────────────
    # if skills:
    #     story.append(Paragraph("Skills", s["section_heading"]))
    #     story.append(HRFlowable(
    #         width="100%", thickness=0.5,
    #         color=MID_GRAY, spaceAfter=6
    #     ))

    #     # Build skill chips in rows of 4
    #     COLS = 4
    #     rows = []
    #     row  = []
    #     for skill in skills:
    #         chip_table = Table(
    #             [[Paragraph(skill.title(), s["skill_chip"])]],
    #             colWidths=[3.8*cm]
    #         )
    #         chip_table.setStyle(TableStyle([
    #             ("BACKGROUND",    (0, 0), (-1, -1), LIGHT_BLUE),
    #             ("TOPPADDING",    (0, 0), (-1, -1), 4),
    #             ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    #             ("LEFTPADDING",   (0, 0), (-1, -1), 6),
    #             ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
    #         ]))
    #         row.append(chip_table)
    #         if len(row) == COLS:
    #             rows.append(row)
    #             row = []
    #     if row:
    #         while len(row) < COLS:
    #             row.append(Paragraph("", s["bullet"]))
    #         rows.append(row)

    #     skills_grid = Table(rows, colWidths=[4.0*cm]*COLS)
    #     skills_grid.setStyle(TableStyle([
    #         ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    #         ("LEFTPADDING",   (0, 0), (-1, -1), 2),
    #         ("RIGHTPADDING",  (0, 0), (-1, -1), 2),
    #         ("TOPPADDING",    (0, 0), (-1, -1), 2),
    #         ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    #     ]))
    #     story.append(skills_grid)

    # # ── WORK EXPERIENCE ───────────────────────────────────────────
    # if experience:
    #     story.append(Paragraph("Work Experience", s["section_heading"]))
    #     story.append(HRFlowable(
    #         width="100%", thickness=0.5,
    #         color=MID_GRAY, spaceAfter=6
    #     ))
    #     for exp in experience:
    #         exp = exp.strip()
    #         if exp:
    #             story.append(Paragraph(f"• {exp}", s["bullet"]))

    # # ── PROJECTS ──────────────────────────────────────────────────
    # if projects:
    #     story.append(Paragraph("Projects", s["section_heading"]))
    #     story.append(HRFlowable(
    #         width="100%", thickness=0.5,
    #         color=MID_GRAY, spaceAfter=6
    #     ))
    #     for proj in projects:
    #         proj = proj.strip()
    #         if proj:
    #             story.append(Paragraph(f"• {proj}", s["bullet"]))

    # # ── EDUCATION ─────────────────────────────────────────────────
    # if education:
    #     story.append(Paragraph("Education", s["section_heading"]))
    #     story.append(HRFlowable(
    #         width="100%", thickness=0.5,
    #         color=MID_GRAY, spaceAfter=6
    #     ))
    #     for edu in education:
    #         edu = edu.strip()
    #         if edu:
    #             story.append(Paragraph(f"• {edu}", s["bullet"]))

    # # ── CERTIFICATIONS ────────────────────────────────────────────
    # if certs:
    #     story.append(Paragraph("Certifications", s["section_heading"]))
    #     story.append(HRFlowable(
    #         width="100%", thickness=0.5,
    #         color=MID_GRAY, spaceAfter=6
    #     ))
    #     for cert in certs:
    #         cert = cert.strip()
    #         if cert:
    #             story.append(Paragraph(f"• {cert}", s["bullet"]))

    # # ── FOOTER ────────────────────────────────────────────────────
    # story.append(Spacer(1, 0.6*cm))
    # story.append(HRFlowable(
    #     width="100%", thickness=1,
    #     color=BLUE, spaceAfter=5
    # ))
    # story.append(Paragraph(
    #     "Generated by AI Interview System",
    #     s["footer"]
    # ))

    # # ── BUILD ─────────────────────────────────────────────────────
    # doc.build(story)
    # buffer.seek(0)
    # return buffer.read()
