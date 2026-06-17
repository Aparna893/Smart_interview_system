BAD_PATTERNS = [

    "what was the name",
    "undefined variable",
    "xml parameter",
    "how did python work",
    "best way to convert",
    "type of experience",
    "what was the name",
    "which company",
    "where did",
    "personal information",
    "candidate name",
    "email address",
    "phone number",
]

def filter_questions(questions):

    filtered = []

    for q in questions:

        q_lower = q.lower()

        bad = False

        for pattern in BAD_PATTERNS:

            if pattern in q_lower:

                bad = True
                break

        if not bad:

            filtered.append(q)

    return filtered