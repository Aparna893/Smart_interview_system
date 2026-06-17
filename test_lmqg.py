from core.services.lmqg_service import (
    generate_lmqg_questions
)

context = """
Python supports object oriented programming.
Decorators modify function behavior.
Generators use yield keyword.
"""

questions = generate_lmqg_questions(
    context
)

print("\nGenerated Questions:\n")

for q in questions:

    print("-", q)