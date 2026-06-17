"""
Generates training data for a SINGLE T5-small model doing both:
  Task 1 — Skill Extraction  : input = "extract skills: <resume>"   → output = "Python, Docker, AWS"
  Task 2 — Question Generation: input = "generate question: <skill>" → output = "How have you used Python?"

Sources:
  - Real resumes from data/cleaned_resumes.csv   (primary)
  - Synthetic fallback if CSV not found

Output:
  data/train.json
  data/val.json
"""

import json, random, os, re
import pandas as pd

random.seed(42)

# ── Question templates ────────────────────────────────────────────────────────
TEMPLATES = {
    "lang": [
        "Can you explain the memory management model in {s}?",
        "How do you handle concurrency in {s}?",
        "Describe a challenging problem you solved using {s}.",
        "What are the performance best practices in {s}?",
        "How does {s} handle error handling and exceptions?",
        "What are the key differences between {s} and similar languages?",
    ],
    "framework": [
        "How does {s} handle state management?",
        "Walk me through the request lifecycle in {s}.",
        "What are the main advantages of {s} over alternatives?",
        "How do you optimize performance in a {s} application?",
        "How does {s} handle dependency injection?",
        "Describe how you structure a large {s} project.",
    ],
    "cloud": [
        "How have you used {s} in a production environment?",
        "What are the key components of {s} you have worked with?",
        "How do you ensure security when using {s}?",
        "Describe a deployment pipeline you built using {s}.",
        "How do you monitor and debug issues in {s}?",
    ],
    "db": [
        "When would you choose {s} over other databases?",
        "How do you optimize queries in {s}?",
        "Describe your experience with schema design in {s}.",
        "What indexing strategies have you used in {s}?",
        "How do you handle migrations in {s}?",
    ],
    "ml": [
        "How have you applied {s} in a real project?",
        "What evaluation metrics do you use when working with {s}?",
        "How do you handle overfitting when using {s}?",
        "Describe a pipeline you built involving {s}.",
        "What are the limitations of {s} you have encountered?",
    ],
    "general": [
        "How have you used {s} professionally?",
        "Describe a project where {s} was critical.",
        "What challenges did you face when learning {s}?",
        "What makes {s} valuable in your work?",
        "How do you stay updated with developments in {s}?",
    ],
}

CATEGORY = {
    "Python":"lang","Java":"lang","C++":"lang","JavaScript":"lang",
    "TypeScript":"lang","Go":"lang","Rust":"lang","Kotlin":"lang",
    "React":"framework","Angular":"framework","Vue.js":"framework",
    "Node.js":"framework","Django":"framework","Flask":"framework",
    "FastAPI":"framework","Spring Boot":"framework",
    "Docker":"cloud","Kubernetes":"cloud","AWS":"cloud",
    "Azure":"cloud","GCP":"cloud","Terraform":"cloud","Jenkins":"cloud",
    "PostgreSQL":"db","MySQL":"db","MongoDB":"db",
    "Redis":"db","Elasticsearch":"db","SQLite":"db","Oracle":"db",
    "TensorFlow":"ml","PyTorch":"ml","scikit-learn":"ml",
    "Pandas":"ml","NumPy":"ml","Keras":"ml",
    "Machine Learning":"ml","Deep Learning":"ml","NLP":"ml",
}


def get_question(skill: str) -> str:
    cat = CATEGORY.get(skill, "general")
    return random.choice(TEMPLATES[cat]).format(s=skill)


def parse_skills(raw: str) -> list:
    """Parse a skill string into a clean list."""
    if not raw or str(raw).strip() in ("", "nan"):
        return []
    skills = re.split(r"[,;|]+", str(raw))
    skills = [s.strip(" •*-\n\r") for s in skills if s.strip()]
    return [s for s in skills if 2 < len(s) < 50]


# ── Build from real CSV ───────────────────────────────────────────────────────
def build_from_real_data():
    csv_path = "data/cleaned_resumes.csv"
    if not os.path.exists(csv_path):
        print("  [!] cleaned_resumes.csv not found, using synthetic only.")
        return [], []

    df = pd.read_csv(csv_path)
    print(f"  Loaded {len(df)} real resumes.")

    skill_extraction = []   # task 1
    question_gen     = []   # task 2

    for _, row in df.iterrows():
        # Combine Skill_Details and Skills for ground truth
        all_skills = parse_skills(str(row.get("Skill_Details", ""))) + \
                     parse_skills(str(row.get("Skills", "")))

        # Deduplicate
        seen, unique_skills = set(), []
        for s in all_skills:
            if s.lower() not in seen:
                unique_skills.append(s)
                seen.add(s.lower())

        if not unique_skills:
            continue

        clean_text = str(row.get("Clean_Text", ""))
        if not clean_text or clean_text == "nan":
            continue

        # ── Task 1: Skill extraction ──────────────────────────────────────
        # Input  : "extract skills: <resume text>"
        # Output : "Python, Docker, AWS"
        skill_extraction.append({
            "input":  "extract skills: " + clean_text[:400],
            "target": ", ".join(unique_skills[:15]),   # max 15 skills
        })

        # ── Task 2: Question generation ───────────────────────────────────
        # Input  : "generate question: <skill>"
        # Output : "<interview question>"
        for skill in unique_skills[:8]:   # up to 8 skills per resume
            q = get_question(skill)
            question_gen.append({
                "input":  f"generate question: {skill}",
                "target": q,
            })

            # Also add context-aware variant
            question_gen.append({
                "input":  f"generate question from resume: {clean_text[:200]} skill: {skill}",
                "target": q,
            })

    print(f"  Skill extraction samples : {len(skill_extraction)}")
    print(f"  Question gen samples     : {len(question_gen)}")
    return skill_extraction, question_gen


# ── Synthetic fallback ────────────────────────────────────────────────────────
SKILLS_LIST = [
    "Python","Java","C++","JavaScript","TypeScript","Go",
    "React","Angular","Django","Flask","FastAPI","Node.js",
    "Docker","Kubernetes","AWS","Azure","GCP","Terraform",
    "PostgreSQL","MySQL","MongoDB","Redis","Elasticsearch",
    "TensorFlow","PyTorch","scikit-learn","Pandas","NumPy",
    "Machine Learning","Deep Learning","NLP","Computer Vision",
    "REST APIs","GraphQL","Microservices","Agile","Git","Linux",
]

BEFORE = [
    "Proficient in","Experience with","Skilled in",
    "Strong knowledge of","Hands-on experience in",
    "3 years of experience in","Built applications with",
    "Expertise in","Implemented solutions using",
]
AFTER = [
    "for backend development.","in production environments.",
    "across multiple projects.","for data pipelines.",
    "in cloud deployments.","for API design.",
]

def build_synthetic(n=300):
    skill_extraction, question_gen = [], []

    for _ in range(n):
        skills = random.sample(SKILLS_LIST, random.randint(3, 7))
        resume_snippet = " ".join([
            f"{random.choice(BEFORE)} {s} {random.choice(AFTER)}"
            for s in skills
        ])
        skill_extraction.append({
            "input":  "extract skills: " + resume_snippet,
            "target": ", ".join(skills),
        })
        for s in skills:
            question_gen.append({
                "input":  f"generate question: {s}",
                "target": get_question(s),
            })

    return skill_extraction, question_gen


# ── Main ──────────────────────────────────────────────────────────────────────
def build_datasets():
    os.makedirs("data", exist_ok=True)

    print("Building from real resume data...")
    real_se, real_qg = build_from_real_data()

    print("Adding synthetic fallback data...")
    syn_se, syn_qg = build_synthetic(300)

    # Combine real + synthetic
    all_se = real_se + syn_se
    all_qg = real_qg + syn_qg

    random.shuffle(all_se)
    random.shuffle(all_qg)

    # Combine both tasks into one dataset (T5 learns both from prefixes)
    all_data = all_se + all_qg
    random.shuffle(all_data)

    split = int(len(all_data) * 0.85)
    train, val = all_data[:split], all_data[split:]

    with open("data/train.json", "w") as f:
        json.dump(train, f, indent=2)
    with open("data/val.json", "w") as f:
        json.dump(val, f, indent=2)

    print(f"\n  Total samples : {len(all_data)}")
    print(f"  Train         : {len(train)}")
    print(f"  Val           : {len(val)}")
    print("  Saved → data/train.json, data/val.json")
    return train, val


if __name__ == "__main__":
    build_datasets()