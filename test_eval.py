from interview.evaluation import (
    calculate_final_score
)

expected = """
Python is a programming language
used for web development.
"""

candidate = """
Python is used to build websites
and applications.
"""

score = calculate_final_score(
    expected,
    candidate
)

print(score)