from transformers import (
    AutoTokenizer,
    AutoModelForSeq2SeqLM
)

from bs4 import BeautifulSoup
import re

MODEL_PATH = "models/answer_generator"

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_PATH
)

model = AutoModelForSeq2SeqLM.from_pretrained(
    MODEL_PATH
)

def clean_text(text):

    text = BeautifulSoup(
        text,
        "html.parser"
    ).get_text()

    text = re.sub(
        r'\s+',
        ' ',
        text
    )

    return text.strip()

def generate_flan_answer(question):

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

        top_p=0.9,

        repetition_penalty=2.0
    )

    answer = tokenizer.decode(
        outputs[0],
        skip_special_tokens=True
    )

    answer = clean_text(answer)

    return answer