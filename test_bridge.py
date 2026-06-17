from core.services.lmqg_bridge import (
    generate_lmqg_questions
)

context = """
Experienced Python developer.
Worked with Django REST APIs.
Used MongoDB and OCR systems.
"""

questions = generate_lmqg_questions(
    context
)

print("\nGenerated Questions:\n")

for q in questions:

    print("-", q)