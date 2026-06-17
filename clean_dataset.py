import json


BAD_PATTERNS = [

    "why does",
    "why is",
    "why can't",
    "undefined",
    "error",
    "exception",
    "not working",
    "failed",
    "stacktrace",
    "bug",
    "issue",
    "problem",
    "cannot",
    "can't",
    "fix",
    "wrong",
]


GOOD_STARTERS = [

    "what is",
    "how would",
    "explain",
    "describe",
    "write",
    "compare",
    "implement",
    "define",
]


INPUT_FILE = "data/training/val.json"

OUTPUT_FILE = "data/clean_val.json"


with open(
    INPUT_FILE,
    "r",
    encoding="utf-8"
) as f:

    data = json.load(f)


cleaned = []


for item in data:

    question = (
        item["target"]
        .lower()
        .strip()
    )

    # REMOVE BAD QUESTIONS
    if any(
        bad in question
        for bad in BAD_PATTERNS
    ):
        continue

    # KEEP ONLY INTERVIEW-LIKE QUESTIONS
    if not any(
        question.startswith(good)
        for good in GOOD_STARTERS
    ):
        continue

    cleaned.append(item)


print(f"Original: {len(data)}")

print(f"Cleaned : {len(cleaned)}")


with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        cleaned,
        f,
        indent=2
    )


print(
    "Clean dataset created successfully!"
)