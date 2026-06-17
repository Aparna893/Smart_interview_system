
import os
from datetime import datetime
from pymongo import MongoClient
import uuid

MONGO_URI = os.getenv(
    "MONGODB_URI",
    "mongodb://localhost:27017"
)

DB_NAME = "ai_interview_system"

client = MongoClient(MONGO_URI)

db = client[DB_NAME]

interviews_collection = db["interviews"]


# =========================================================
# CREATE INTERVIEW
# =========================================================

def create_interview(data):

    data["interview_id"] = uuid.uuid4().hex

    data["created_at"] = datetime.utcnow()

    result = interviews_collection.insert_one(data)
    
    return data["interview_id"]
# =========================================================
# GET INTERVIEW
# =========================================================

def get_interview(interview_id):

    try:

        return interviews_collection.find_one({

            "interview_id": interview_id
        })

    except Exception:

        return None

# =========================================================
# UPDATE QUESTIONS
# =========================================================
def update_questions(

    interview_id,

    questions,

    provider="",

    question_count=0
):

    interviews_collection.update_one(

        {
            "interview_id": interview_id
        },

        {
            "$set": {

                "generated_questions": questions,

                "provider": provider,

                "question_count": question_count
            }
        }
    )





# =========================================================
# SAVE ANSWERS
# =========================================================

def save_answers(interview_id, answers):

    interviews_collection.update_one(

        {
            "interview_id": interview_id
        },

        {
            "$set": {
                "answers": answers
            }
        }
    )


# =========================================================
# SAVE EVALUATION
# =========================================================

def save_evaluation(interview_id, evaluation):

    interviews_collection.update_one(

        {
            "interview_id": interview_id
        },

        {
            "$set": evaluation
        }
    )


# =========================================================
# GET ALL INTERVIEWS
# =========================================================

def get_all_interviews():

    return list(

        interviews_collection.find().sort(
            "created_at",
            -1
        )
    )
def save_summary(interview_id, summary_text):
    interviews_collection.update_one(
        {"interview_id": interview_id},
        {"$set": {"summary_text": summary_text}}
    )
