"""
data/clean_dataset.py

Cleans UpdatedResumeDataSet.csv and produces a structured CSV with columns:
    Category, Raw_Resume, Skills, Skill_Details, Education,
    Company, Job_Title, Experience_Text, Clean_Text

Usage:
    python data/clean_dataset.py

Input  : data/raw/UpdatedResumeDataSet.csv
Output : data/cleaned_resumes.csv
"""

import os
import re
import pandas as pd

INPUT_PATH  = "data/raw/UpdatedResumeDataSet.csv"
OUTPUT_PATH = "data/cleaned_resumes.csv"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _clean_whitespace(text: str) -> str:
    """Normalise line endings and collapse blank lines."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _fix_encoding(text: str) -> str:
    """Fix common mojibake patterns left by OCR."""
    replacements = {
        "NaÃ¯ve": "Naive",
        "â¢":     "•",
        "Ã©":     "é",
        "Ã":      "à",
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)
    return text


def extract_skills_section(text: str) -> str:
    """
    Extract the top-level 'Skills' bullet block that appears at the
    very start of many resumes  (before 'Education Details').
    e.g.  'Skills * Programming Languages: Python ...'
    """
    # Pattern 1: starts with 'Skills *' or 'Skills\n'
    m = re.search(
        r"(?:^|\n)Skills[\s\*:]+(.+?)(?=Education Details|Skill Details|Company Details|$)",
        text, re.DOTALL | re.IGNORECASE
    )
    if m:
        raw = m.group(1).strip()
        # Flatten bullets into comma list
        items = re.split(r"[\*\n]+", raw)
        items = [i.strip(" ,.:") for i in items if i.strip()]
        return ", ".join(items)

    # Pattern 2: 'Technical Skills' or 'TECHNICAL SKILLS' block
    m = re.search(
        r"(?:TECHNICAL SKILLS|Technical Skills)\s*[\n:]+(.+?)(?=\n[A-Z][A-Z\s]{3,}|\Z)",
        text, re.DOTALL
    )
    if m:
        return _clean_whitespace(m.group(1))

    return ""


def extract_skill_details(text: str) -> str:
    """
    Extract 'Skill Details' section — structured as:
        SkillName- Exprience - N months
    Returns a clean comma-separated list of skill names.
    """
    m = re.search(
        r"Skill Details\s*\n(.+?)(?=Company Details|Education Details|\Z)",
        text, re.DOTALL
    )
    if not m:
        return ""

    block = m.group(1)
    # Each line: "Python- Exprience - 24 months"
    skill_names = []
    for line in block.splitlines():
        line = line.strip()
        if not line:
            continue
        # Extract skill name before the dash
        name_match = re.match(r"^([^-\n]+?)\s*-\s*Exprience", line, re.IGNORECASE)
        if name_match:
            skill_names.append(name_match.group(1).strip())
    return ", ".join(skill_names)


def extract_education(text: str) -> str:
    """
    Extract 'Education Details' section.
    Captures degree, institution, and year if present.
    """
    m = re.search(
        r"Education Details\s*\n(.+?)(?=Skill Details|Company Details|[A-Z ]{4,}\n|\Z)",
        text, re.DOTALL
    )
    if not m:
        # Try inline: 'Education Details \r\n BE ...'
        m = re.search(r"Education Details\s+(.+?)(?=Skill Details|Company Details|\Z)",
                      text, re.DOTALL)
    if m:
        return _clean_whitespace(m.group(1))
    return ""


def extract_company_and_title(text: str) -> tuple:
    """
    Extract company name and job title from 'Company Details' block.
    Returns (company_name, job_title).
    """
    company = ""
    title   = ""

    # Company Details block
    m = re.search(r"Company Details\s*\n(.*?)(?=\n[A-Z]|\Z)", text, re.DOTALL)
    if m:
        block = m.group(1)
        cm = re.search(r"company\s*[-–]\s*(.+)", block, re.IGNORECASE)
        if cm:
            company = cm.group(1).strip()

    # Job title: line that ends with '\r\n\r\n' after a designation pattern
    # e.g.  "Data Science Assurance Associate \r\n\r\n"
    tm = re.search(r"\n([A-Z][a-zA-Z\s]{3,50})\s*\n\n", text)
    if tm:
        title = tm.group(1).strip()

    return company, title


def extract_experience_text(text: str) -> str:
    """
    Extract the main work experience body — the narrative paragraphs after
    Company Details (project descriptions, responsibilities, tools used).
    """
    m = re.search(
        r"Company Details.+?description\s*-\s*[^\n]+\n(.+)",
        text, re.DOTALL | re.IGNORECASE
    )
    if m:
        return _clean_whitespace(m.group(1))
    return ""


def build_clean_text(row: pd.Series) -> str:
    """
    Reassemble a readable, flat resume text from the extracted columns.
    Used as the 'Clean_Text' column for model training.
    """
    parts = []
    if row["Job_Title"]:
        parts.append(f"Job Title: {row['Job_Title']}")
    if row["Skills"]:
        parts.append(f"Skills: {row['Skills']}")
    if row["Skill_Details"]:
        parts.append(f"Technical Skills: {row['Skill_Details']}")
    if row["Education"]:
        parts.append(f"Education: {row['Education']}")
    if row["Company"]:
        parts.append(f"Company: {row['Company']}")
    if row["Experience_Text"]:
        parts.append(f"Experience:\n{row['Experience_Text']}")
    return "\n\n".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def clean_dataset():
    print(f"Reading {INPUT_PATH} ...")
    df = pd.read_csv(INPUT_PATH)
    print(f"  Loaded {len(df)} rows, columns: {df.columns.tolist()}")

    # Keep raw resume for reference
    df["Raw_Resume"] = df["Resume"]

    # Fix encoding first
    df["Resume"] = df["Resume"].astype(str).apply(_fix_encoding).apply(_clean_whitespace)

    print("Extracting structured columns ...")

    df["Skills"]          = df["Resume"].apply(extract_skills_section)
    df["Skill_Details"]   = df["Resume"].apply(extract_skill_details)
    df["Education"]       = df["Resume"].apply(extract_education)

    company_title         = df["Resume"].apply(extract_company_and_title)
    df["Company"]         = company_title.apply(lambda x: x[0])
    df["Job_Title"]       = company_title.apply(lambda x: x[1])

    df["Experience_Text"] = df["Resume"].apply(extract_experience_text)
    df["Clean_Text"]      = df.apply(build_clean_text, axis=1)

    # Drop the intermediate Resume column (Raw_Resume preserved)
    df = df.drop(columns=["Resume"])

    # Reorder columns nicely
    df = df[[
        "Category",
        "Job_Title",
        "Company",
        "Skills",
        "Skill_Details",
        "Education",
        "Experience_Text",
        "Clean_Text",
        "Raw_Resume",
    ]]

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"\nSaved cleaned dataset → {OUTPUT_PATH}")

    # Summary
    print(f"\n{'='*50}")
    print(f"Total rows        : {len(df)}")
    print(f"Categories        : {df['Category'].nunique()}")
    print(f"Has Skills        : {(df['Skills'] != '').sum()}")
    print(f"Has Skill Details : {(df['Skill_Details'] != '').sum()}")
    print(f"Has Education     : {(df['Education'] != '').sum()}")
    print(f"Has Company       : {(df['Company'] != '').sum()}")
    print(f"Has Job Title     : {(df['Job_Title'] != '').sum()}")
    print(f"{'='*50}")

    # Show sample
    print("\nSample cleaned row:")
    sample = df[df["Skills"] != ""].iloc[0]
    print(f"  Category   : {sample['Category']}")
    print(f"  Job Title  : {sample['Job_Title']}")
    print(f"  Company    : {sample['Company']}")
    print(f"  Skills     : {sample['Skills'][:120]}")
    print(f"  Skill Det. : {sample['Skill_Details'][:120]}")
    print(f"  Education  : {sample['Education'][:120]}")
    print(f"  Clean Text : {sample['Clean_Text'][:200]}")


if __name__ == "__main__":
    clean_dataset()