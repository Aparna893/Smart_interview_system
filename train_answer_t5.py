from datasets import load_dataset

from transformers import (
    AutoTokenizer,
    AutoModelForSeq2SeqLM,
    Trainer,
    TrainingArguments
)

MODEL_NAME = "google/flan-t5-small"

print("Loading tokenizer...")

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

print("Loading model...")

model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME)

print("Loading dataset...")

dataset = load_dataset(
    "json",
    data_files={
        "train":
        "data/answer_generation/train.json",

        "validation":
        "data/answer_generation/val.json"
    }
)

MAX_INPUT = 128
MAX_TARGET = 128

def preprocess(example):

    model_inputs = tokenizer(
        example["input"],
        max_length=MAX_INPUT,
        truncation=True,
        padding="max_length"
    )

    labels = tokenizer(
        example["target"],
        max_length=MAX_TARGET,
        truncation=True,
        padding="max_length"
    )

    model_inputs["labels"] = labels["input_ids"]

    return model_inputs

print("Tokenizing dataset...")

tokenized_dataset = dataset.map(
    preprocess,
    batched=False
)

training_args = TrainingArguments(

    output_dir="models/answer_checkpoints",

    learning_rate=1e-4,

    per_device_train_batch_size=2,
    per_device_eval_batch_size=2,

    num_train_epochs=2,

    weight_decay=0.01,

    logging_steps=100,

    eval_strategy="steps",

    eval_steps=100,

    save_steps=500,

    save_total_limit=2,
    gradient_accumulation_steps=2,

    do_eval=True,

    fp16=False
)

trainer = Trainer(

    model=model,

    args=training_args,

    train_dataset=tokenized_dataset["train"],

    eval_dataset=tokenized_dataset["validation"]
)

print("Starting training...")

trainer.train()

print("Saving model...")

model.save_pretrained(
    "models/answer_generator"
)

tokenizer.save_pretrained(
    "models/answer_generator"
)

print("Training completed successfully!")