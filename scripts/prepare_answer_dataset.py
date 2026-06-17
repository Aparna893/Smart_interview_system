import pandas as pd
import json
import random
from bs4 import BeautifulSoup
import re
print("Loading datasets...")

questions = pd.read_csv(
    "data/kaggle/Questions.csv",
    encoding="latin1"
)

answers = pd.read_csv(
    "data/kaggle/Answers.csv",
    encoding="latin1"
)

print("Cleaning datasets...")

questions = questions[
    ["Id", "Title"]
]

answers = answers[
    ["ParentId", "Body"]
]

# Remove nulls
questions = questions.dropna()
answers = answers.dropna()

# Merge answers with questions
merged = pd.merge(
    questions,
    answers,
    left_on="Id",
    right_on="ParentId"
)

dataset = []

print("Creating training samples...")

for _, row in merged.iterrows():

    question = str(row["Title"]).strip()

    answer = BeautifulSoup(
        str(row["Body"]),
        "html.parser"
    ).get_text()

    answer = re.sub(
        r'\s+',
        ' ',
        answer
    ).strip()

    question_lower = question.lower()

    # Keep only conceptual/interview style
    good_patterns = [

        "what is",
        "difference between",
        "explain",
        "define",
        "why",
        "how does"
    ]

    valid = False

    for pattern in good_patterns:

        if pattern in question_lower:
            valid = True
            break

    if not valid:
        continue

    # Remove huge answers
    if len(answer) > 500:
        answer = answer[:500]

    sample = {

        "input":
        f"Answer this interview question: {question}",

        "target":
        answer
    }

    dataset.append(sample)

# Shuffle dataset
random.shuffle(dataset)

# Limit for your system
dataset = dataset[:5000]

split = int(len(dataset) * 0.9)

train_data = dataset[:split]
val_data = dataset[split:]

# Save train
with open(
    "data/answer_generation/train.json",
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        train_data,
        f,
        indent=2,
        ensure_ascii=False
    )

# Save validation
with open(
    "data/answer_generation/val.json",
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        val_data,
        f,
        indent=2,
        ensure_ascii=False
    )

print("\nDataset created successfully!")

print(f"Train samples: {len(train_data)}")

print(f"Validation samples: {len(val_data)}")