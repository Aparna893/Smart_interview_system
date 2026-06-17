from transformers import (
    AutoTokenizer,
    AutoModelForSeq2SeqLM
)

MODEL_PATH = "models/question_generator"

print("Loading trained model...")

tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)

model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_PATH)

print("Model loaded successfully!")

while True:

    skill = input("\nEnter Skill: ")

    if skill.lower() == "exit":
        break

    prompt = f"Generate an intermediate interview question about {skill}"

    inputs = tokenizer(
        prompt,
        return_tensors="pt"
    )

    outputs = model.generate(

        inputs.input_ids,

        max_length=64,

        do_sample=True,

        temperature=1.0,

        top_k=50,

        top_p=0.95,

        repetition_penalty=1.8,

        num_return_sequences=3
    )

    print("\nGenerated Questions:\n")

    seen = set()

    count = 1

    for output in outputs:

        question = tokenizer.decode(
            output,
            skip_special_tokens=True
        )

        if question not in seen:

            seen.add(question)

            print(f"{count}. {question}\n")

            count += 1