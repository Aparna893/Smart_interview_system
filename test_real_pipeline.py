from core.services.hybrid_question_service import (
    generate_questions
)

resume_text = """
Experienced Python developer.
Worked with Django REST APIs.
Used MongoDB and OCR systems.
Implemented JWT authentication.
"""

questions = generate_questions(
    "Python",
    resume_text
)

print("\nGenerated Questions:\n")

for q in questions:

    print("-", q)