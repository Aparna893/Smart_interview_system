from .openrouter_service import ask_openrouter

from core.services.hybrid_answer_service import (
    generate_answer
)
def generate_expected_answer(question):

    prompt = f"""
You are an expert technical interviewer.

Provide a concise but correct expected answer
for the following interview question.

Question:
{question}

Expected Answer:
"""

    try:

        response = generate_answer(
            prompt
        )
        answer = response.strip()
        print(f"\n[ANSWER GENERATED]\nQ: {question}\nA: {answer}\n")
        return answer
    except Exception:

        return (
            "Candidate should explain core concepts "
            "related to the question clearly."
        )
