from urllib import response

import requests
import json
import os

from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv(
    "OPENROUTER_API_KEY"
)
MODEL = (
    "openai/gpt-4o-mini"
)


def generate_questions_openrouter(

    skill,

    resume_context,

    count=2
):

    prompt = f"""
You are an expert technical interviewer.

Candidate Resume:

{resume_context}

Current Skill:
{skill}

Generate EXACTLY {count} interview questions.

Return ONLY valid JSON.

IMPORTANT:
- No markdown
- No explanation
- No extra text
- No ```json block

Format:

[
    {{
        "question": "Explain Python decorators.",
        "difficulty": "medium",
        "type": "conceptual"
    }},
    {{
        "question": "How does Django ORM work?",
        "difficulty": "hard",
        "type": "project-based"
    }}
]

Rules:
- Questions must be skill-based
- Questions must be resume-based
- Questions must be different every time
- Include conceptual + coding + scenario questions
"""

    response = requests.post(

        url=
        "https://openrouter.ai/api/v1/chat/completions",

        headers={

            "Authorization":
            f"Bearer {OPENROUTER_API_KEY}",

            "Content-Type":
            "application/json"
        },

        data=json.dumps({

            "model": MODEL,

            "temperature": 0.9,

            "messages": [

                {
                    "role": "user",

                    "content": prompt
                }
            ]
        }),

        timeout=30
    )

    response.raise_for_status()

    result = response.json()

    if "choices" not in result:

        raise Exception(
            f"OpenRouter Error: {result}"
        )

    output = result["choices"][0][
        "message"
    ]["content"]

    # CLEAN RESPONSE

    output = output.replace(
        "```json",
        ""
    )

    output = output.replace(
        "```",
        ""
    )

    output = output.strip()

    try:

        parsed = json.loads(output)

    except Exception as e:

        print(
            "JSON PARSE ERROR:",
            e
        )

        print(output)

        parsed = [

            {
                "question":
                f"Explain {skill}.",

                "difficulty":
                "medium",

                "type":
                "conceptual"
            }
        ]

    return parsed

def ask_openrouter(prompt, model=None, temperature=0.5):

    response = requests.post(

        url=
        "https://openrouter.ai/api/v1/chat/completions",

        headers={

            "Authorization":
            f"Bearer {OPENROUTER_API_KEY}",

            "Content-Type": "application/json"
        },

        data=json.dumps({

            "model": model or MODEL,
            "temperature": temperature,
            "messages": [

                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "reasoning": {
                "exclude": True
            },
        }),
        timeout=30
    )
    
    response.raise_for_status()

    result = response.json()

    if "choices" not in result:

        raise Exception(
            f"OpenRouter Error: {result}"
        )

    return result["choices"][0]["message"]["content"].strip()
