import pandas as pd
import json
from sklearn.model_selection import train_test_split

print("Loading Questions dataset...")

# Load only required columns
df = pd.read_csv(
    "data/kaggle/Questions.csv",
    encoding="latin1",
    usecols=["Title"],
    low_memory=False
)

# Remove missing values
df = df.dropna()

training_data = []

# Technical keywords
skills = [
    "python",
    "java",
    "javascript",
    "react",
    "django",
    "sql",
    "mysql",
    "html",
    "css",
    "node",
    "mongodb",
    "machine learning",
    "api",
    "flask",
]

print("Generating training samples...")

for _, row in df.iterrows():

    title = str(row["Title"]).strip()
    title_lower = title.lower()

    # Remove noisy/problem-style questions
    bad_patterns = [

        "how to",
        "error",
        "unable",
        "problem",
        "issue",
        "fix",
        "failed",
        "exception",
        "warning",
        "crash",
        "not working",
        "php",
        "html",
        "css",
        "javascript",
        "jquery",
        "mysql",
        "sql",

        "file",
        "server",
        "binary",
        "array",
    ]

    skip = False

    for pattern in bad_patterns:

        if pattern in title_lower:
            skip = True
            break

    if skip:
        continue
    good_patterns = [

        "what is",
        "difference between",
        "explain",
        "define",
        "why",
        "when to use",
    ]

    valid = False

    for pattern in good_patterns:

        if pattern in title_lower:
            valid = True
            break

    if not valid:
        continue

    for skill in skills:

        if skill in title_lower:

            sample = {
                "input": f"Generate interview question for {skill}",
                "target": title
            }

            training_data.append(sample)

# Remove duplicates
unique_data = []
seen = set()

for item in training_data:

    pair = (item["input"], item["target"])

    if pair not in seen:
        seen.add(pair)
        unique_data.append(item)

print("Total Clean Samples:", len(unique_data))
unique_data = unique_data[:5000]
# Split train/validation
train_data, val_data = train_test_split(
    unique_data,
    test_size=0.1,
    random_state=42
)

# Save training files
with open("data/training/train.json", "w") as f:
    json.dump(train_data, f, indent=2)

with open("data/training/val.json", "w") as f:
    json.dump(val_data, f, indent=2)

print("Training dataset created successfully!")