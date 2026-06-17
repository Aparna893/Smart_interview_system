from lmqg import TransformersQG
import sys
import json
import warnings

warnings.filterwarnings("ignore")

model = TransformersQG(
    "lmqg/t5-small-squad-qg"
)

def generate_questions(context):

    questions = model.generate_q(
        context
    )

    if isinstance(questions, str):

        questions = [questions]

    return questions


if __name__ == "__main__":

    try:

        context = sys.stdin.read()

        questions = generate_questions(
            context
        )

        print(json.dumps(questions))

    except Exception as e:

        print(json.dumps([]))