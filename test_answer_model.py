from transformers import (
    AutoTokenizer,
    AutoModelForSeq2SeqLM
)

MODEL_PATH = "models/answer_generator"

print("Loading answer generation model...")

tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)

model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_PATH)

while True:

    question = input(
        "\nEnter Interview Question: "
    )

    if question.lower() == "exit":
        break

    prompt = (
        f"Answer this interview question: "
        f"{question}"
    )

    inputs = tokenizer(
        prompt,
        return_tensors="pt"
    )

    outputs = model.generate(

        inputs.input_ids,

        max_length=128,

        do_sample=True,

        temperature=0.7,

        top_k=50,

        top_p=0.9,

        repetition_penalty=1.5
    )

    answer = tokenizer.decode(
        outputs[0],
        skip_special_tokens=True
    )

    print("\nGenerated Answer:\n")

    print(answer)