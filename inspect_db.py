from pymongo import MongoClient
from pprint import pprint

client = MongoClient('mongodb://localhost:27017/')
db = client['ai_interview_system']
if 'interviews' not in db.list_collection_names():
    print('no interviews collection')
    raise SystemExit
coll = db['interviews']
for i, doc in enumerate(coll.find().limit(20), start=1):
    print('DOC', i)
    print('id:', doc.get('interview_id'))
    print('status:', doc.get('status'))
    print('resume_pdf:', doc.get('resume_pdf'))
    print('overall_score:', doc.get('overall_score'))
    print('skill_averages:', doc.get('skill_averages'))
    questions = doc.get('questions')
    print('questions type:', type(questions).__name__)
    if isinstance(questions, dict):
        print('question keys:', list(questions.keys())[:5])
        first_skill = next(iter(questions), None)
        print('sample question item:', questions[first_skill][0] if first_skill and questions[first_skill] else None)
    else:
        print('question sample:', questions[0] if questions else None)
    print('answers present:', bool(doc.get('answers')))
    print('-'*40)
