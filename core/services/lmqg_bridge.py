import subprocess
import json

from matplotlib import lines

LMQG_PYTHON = (
    r"C:\Users\pattn\My project\OCR\lmqg_env\Scripts\python.exe"
)

LMQG_SCRIPT = (
    r"C:\Users\pattn\My project\OCR\lmqg_generate.py"
)

def generate_lmqg_questions(context):

    try:

        result = subprocess.run(

            [
                LMQG_PYTHON,
                LMQG_SCRIPT
            ],

            input=context,

            text=True,

            capture_output=True
        )

        output = result.stdout.strip()

        print("LMQG RAW OUTPUT:", output)

        lines = output.splitlines()

        json_output = lines[-1]

        questions = json.loads(json_output)
        return questions

    except Exception as e:

        print("LMQG Bridge Error:", e)

        return []