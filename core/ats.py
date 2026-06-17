def calculate_ats_score(sections):

    score = 0

    skills = sections.get("skills", [])
    projects = sections.get("projects", [])
    experience = sections.get("experience", [])
    education = sections.get("education", [])

    if len(skills) >= 5:
        score += 30

    if len(projects) >= 2:
        score += 25

    if len(experience) >= 1:
        score += 25

    if len(education) >= 1:
        score += 20

    return min(score, 100)