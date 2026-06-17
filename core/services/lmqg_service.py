from lmqg import TransformersQG

question_model = TransformersQG(
    language="en",
    model="lmqg/t5-base-squad-qg"
)

def generate_lmqg_questions(context):

    try:

        questions = question_model.generate_q(
            context
        )

        return questions

    except Exception as e:

        print("LMQG Error:", e)

        return []