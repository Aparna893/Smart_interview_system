from transformers import (
    AutoTokenizer,
    AutoModelForSeq2SeqLM
)

MODEL_PATH = "models/question_generator"

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_PATH
)

model = AutoModelForSeq2SeqLM.from_pretrained(
    MODEL_PATH
)

def generate_flan_question(skill, count, context):

    prompt = f"""
    Generate {count} professional technical interview questions.

    Skill:
    {skill}

    Candidate Resume Context:
    {context}

    Rules:
    - Questions must be specifically related to {skill}
    - Focus on practical interview assessment
    - Include conceptual and coding questions
    - Avoid generic questions
    - Avoid random Java/Python confusion
    - Avoid company-history questions
    - Avoid factual extraction questions
    - Questions should sound like real software interviews
    - Return only questions
    - One question per line
    """

    inputs = tokenizer(
        prompt,
        return_tensors="pt"
    )

    outputs = model.generate(

        inputs.input_ids,

        max_length=64,

        do_sample=True,

        temperature=0.7,

        top_p=0.9,

        repetition_penalty=2.0
    )

    generated_text = tokenizer.decode(
    outputs[0],
    skip_special_tokens=True
    )

    questions = []

    for q in generated_text.split("\n"):

        q = q.strip()

        if not q:
            continue

        q = q.lstrip("1234567890.- ")

        questions.append(q)

    return questions
