from multiprocessing import context
import uuid
import os
import hashlib
from django.shortcuts import render
import json
from django.shortcuts import redirect
from django.conf import settings
from django.http import JsonResponse
from matplotlib.style import context
from requests import request

import interview
from .forms import ResumeUploadForm
from django.views.decorators.csrf import csrf_exempt
from core.ocr_service import (
    extract_text_from_pdf_bytes,
    extract_resume_sections,
    generate_questions,
    create_tts_audio,
)

from core.database import (
    create_interview, get_interview,
    get_all_interviews, update_questions,
    save_answers, save_evaluation, save_summary
)


from core.answer_generator import (
    generate_expected_answer,
)
from core.ats import calculate_ats_score
from core.evaluation import (
    calculate_final_score
)
from core.services.Report_service import generate_report_pdf
from django.http import HttpResponse

def home(request):

    context = {}

    if request.method == "POST":

        form = ResumeUploadForm(request.POST, request.FILES)

        if form.is_valid():
            uploaded = request.FILES["resume"]
            if not uploaded.name.endswith(".pdf"):
                return render(request, "interview/Home.html", {"form": form, "error": "Please upload a valid PDF file."})

            pdf_bytes = uploaded.read()
            uploaded.seek(0)
            print("STEP 1: File received")
            extracted_text = extract_text_from_pdf_bytes(pdf_bytes)
            print(extracted_text)
            from core.resume_parser import parse_resume
            print("STEP 2: Text extracted")
            sections = parse_resume(extracted_text)
            print(sections)
            print("STEP 3: Resume parsed")
            ats_score = calculate_ats_score(sections)
            question_count = form.cleaned_data["question_count"]

            from django.core.files.storage import FileSystemStorage
            fs = FileSystemStorage()

            safe_name = uploaded.name.replace(' ', '_')

            filename = fs.save(
                safe_name,
                uploaded
            )

            uploaded_file_url = fs.url(filename)
            if not uploaded_file_url.startswith("http"):
                uploaded_file_url = request.build_absolute_uri(uploaded_file_url)
            print("STEP 4: ATS calculated")
            # Save extracted sections and raw text; defer question generation
            interview_id = create_interview({

                "extracted_text": extracted_text,

                "resume_pdf": uploaded_file_url,

                "name": sections.get("name", ""),

                "email": sections.get("email", ""),

                "phone": sections.get(
                    "personal_info",
                    {}
                ).get("phone", ""),

                "linkedin": sections.get(
                    "personal_info",
                    {}
                ).get("linkedin", ""),

                "github": sections.get(
                    "personal_info",
                    {}
                ).get("github", ""),

                "skills": sections.get(
                    "skills",
                    []
                ),

                "education": sections.get(
                    "education",
                    []
                ),

                "projects": sections.get(
                    "projects",
                    []
                ),
                "projects_structured": sections.get("projects_structured", []),
                "experience": sections.get(
                    "experience",
                    []
                ),
                "experience_structured": sections.get("experience_structured", []),
                "education_structured":  sections.get("education_structured", []),
                "questions": {},

                "ats_score": ats_score,

                "provider": "",

                "question_count": question_count,

                "answers": [],

                "status": "pending",
            })
            print("STEP 5: Interview created")
            all_skills = sections.get(
                "skills",
                []
            )
            skills = all_skills[:7]
            context = {
                "name": sections.get("name", "Admin"),
                "sections": sections,
                "skills": all_skills,
                "skills_count": len(all_skills),
                "interview_id": interview_id,          # ← sidebar nav links
                "resume_pdf": uploaded_file_url,       # ← "View Resume" button
                "question_count": question_count,
                "ats_score": ats_score,
                "generated_questions_count": 0,        # updated after generation
            }
        else:
            form = ResumeUploadForm()
            context["form"] = form
            return render(request, "interview/Home.html", context)

    else:
        form = ResumeUploadForm()
        context = {
            "name": "Admin",
            "form": form,
            "interview_id": None,
            "ats_score": 0,
            "skills_count": 0,
            "generated_questions_count": 0,
            "skills": [],
        }

    context.setdefault("form", form)
    return render(request, "interview/Home.html", context)
def candidate_interview(
    request,
    interview_id
):
    interview = get_interview(interview_id)

    # ---------------------------------------------------------
    # SAVE ANSWERS
    # ---------------------------------------------------------

    if request.method == "POST":

        data = json.loads(
            request.body
        )

        
        save_answers(
            interview_id,
            data["answers"]
        )


        return JsonResponse({

            "success": True
        })

    # ---------------------------------------------------------
    # GENERATE QUESTION AUDIO
    # ---------------------------------------------------------

    question_audio = []
    questions = interview.get("questions", [])

    audio_dir = os.path.join(
        settings.MEDIA_ROOT,
        "tts",
        interview_id
    )

    for index, q in enumerate(questions):
        if isinstance(q, dict):
            question_text = q.get("question", "").strip()
            skill = q.get("skill", "General")
        else:
            question_text = str(q).strip()
            skill = "General"

        if not question_text:
            continue

        audio_fingerprint = hashlib.sha256(
            question_text.encode("utf-8")
        ).hexdigest()[:12]
        audio_name = (
            f"question_{index + 1}_"
            f"{audio_fingerprint}.mp3"
        )
        audio_path = os.path.join(
            audio_dir,
            audio_name
        )
        audio_url = (
            f"{settings.MEDIA_URL}tts/"
            f"{interview_id}/{audio_name}"
        )

        if not os.path.exists(audio_path):
            try:
                create_tts_audio(
                    question_text,
                    audio_path
                )
            except Exception as e:
                print("Question TTS error:", e)
                audio_url = ""

        question_audio.append({
            "question": question_text,
            "skill": skill,
            "audio": audio_url,
        })

    print("question_audio count:", len(question_audio))

    return render(

        request,

        "interview/candidate.html",

        {

            "interview": interview,

            "question_audio": json.dumps(
                question_audio
            ),

            "has_questions": bool(
                question_audio
            ),
        }
    )
def submit_interview(request):

    if request.method == "POST":

        data = json.loads(
            request.body
        )

        interview_id = data.get(
            "interview_id"
        )

        
        interview = get_interview(interview_id)



        if not interview:
            return JsonResponse({
                "status": "error",
                "message": "Interview not found."
            }, status=404)

        questions = data.get(
            "questions",
            []
        )

        expected_map = {}
        stored_questions = interview.get("questions", {})

        if isinstance(stored_questions, dict):
            for skill, qs in stored_questions.items():
                for q in qs:
                    if isinstance(q, dict):
                        expected_map[q.get("question", "").strip()] = {
                            "expected_answer": q.get("expected_answer", ""),
                            "skill": q.get("skill", skill)
                        }
                    elif isinstance(q, str):
                        expected_map[q.strip()] = {
                            "expected_answer": "",
                            "skill": skill
                        }
        elif isinstance(stored_questions, list):
            for q in stored_questions:
                if isinstance(q, dict):
                    expected_map[q.get("question", "").strip()] = {
                        "expected_answer": q.get("expected_answer", ""),
                        "skill": q.get("skill", "General")
                    }
                elif isinstance(q, str):
                    expected_map[q.strip()] = {
                        "expected_answer": "",
                        "skill": "General"
                    }

        evaluated_questions = []

        skill_scores = {}
        total_score = 0

        for q in questions:

            question = q.get(
                "question",
                ""
            )

            candidate_answer = q.get(
                "candidate_answer",
                ""
            )

            expected_entry = expected_map.get(
                question,
                {
                    "expected_answer": "",
                    "skill": q.get("skill", "General")
                }
            )

            expected_answer = expected_entry["expected_answer"]
            skill = expected_entry["skill"]

            if not expected_answer and question:
                try:
                    expected_answer = generate_expected_answer(
                        question
                    )
                except Exception as e:
                    print("Expected answer fallback error:", e)
                    expected_answer = ""

            score = (
                calculate_final_score(
                    expected_answer,
                    candidate_answer
                )
            )

            total_score += score["final_score"]
            skill_scores.setdefault(skill, []).append(
                score["final_score"]
            )

            evaluated_questions.append({

                "question":
                    question,

                "skill":
                    skill,

                "expected_answer":
                    expected_answer,

                "candidate_answer":
                    candidate_answer,

                "keyword_score":
                    score["keyword_score"],

                "semantic_score":
                    score["semantic_score"],

                "score":
                    round(
                        score["final_score"],
                        2
                    ),

                "verdict":
                    score["verdict"]
            })

        overall_score = 0
        skill_averages = {}

        if evaluated_questions:

            overall_score = (
                total_score
                /
                len(evaluated_questions)
            )

            for skill, scores in skill_scores.items():
                if scores:
                    skill_averages[skill] = round(
                        sum(scores) / len(scores),
                        2
                    )
        save_evaluation(

            interview_id,

            {
                "answers": questions,
                "evaluated_questions": evaluated_questions,
                "skill_averages": skill_averages,
                "overall_score": round(
                    overall_score,
                    2
                ),
                "status": "completed"
            }
        )
        return JsonResponse({
            "status": "success"
        })

def evaluation_results(request):

    results = request.session.get(

        "evaluation_results",

        {}
    )

    return render(

        request,

        "interview/evaluation_results.html",

        {
            "results": results
        }
    )
def review_interview(
    request,
    interview_id
):

    
    interview = get_interview(interview_id)

    candidate_link = (
        f"/candidate/{interview_id}/"
    )
    context = {

        "interview": interview,

        "candidate_link": candidate_link,
    }

    return render(

        request,

        "interview/review.html",

        context
    )
def admin_dashboard(
    request
):

    all_interviews = get_all_interviews()

    best_resume = None
    best_score = -1

    for interview in all_interviews:
        if str(interview.get("status", "")).lower() != "completed":
            continue
        score = interview.get("overall_score")
        if isinstance(score, (int, float)) and score > best_score:
            best_score = score
            best_resume = interview
    total_interviews = len(all_interviews)

    completed_interviews = sum(

        1 for i in all_interviews

        if i.get("status") == "completed"
    )

    pending_interviews = sum(

        1 for i in all_interviews

        if i.get("status") == "pending"
    )

    average_score = 0

    scores = [

        i.get("overall_score", 0)

        for i in all_interviews

        if isinstance(
            i.get("overall_score"),
            (int, float)
        )
    ]

    if scores:

        average_score = round(

            sum(scores) / len(scores),

            2
        )
    return render(

        request,

        "interview/dashboard.html",

        {
            "interviews": all_interviews,

            "best_resume": best_resume,

            "best_score": round(
                best_score,
                2
            ) if best_resume is not None else None,

            "total_interviews": total_interviews,

            "completed_interviews": completed_interviews,

            "pending_interviews": pending_interviews,

            "average_score": average_score,
        }
    )


def resumes(request):

    all_interviews = [

        interview

        for interview in get_all_interviews()

        if interview.get("resume_pdf")
    ]



    def _extract_pdf_name(url: str) -> str:
        if not url:
            return "resume.pdf"
        parts = url.split("?")[0].split("/")
        return parts[-1] if parts[-1] else "resume.pdf"

    for interview in all_interviews:
        interview["resume_file_name"] = _extract_pdf_name(
            interview.get("resume_pdf", "")
        )

    pending_count = sum(
        1 for interview in all_interviews
        if str(interview.get("status", "")).lower() == "pending"
    )

    completed_count = sum(
        1 for interview in all_interviews
        if str(interview.get("status", "")).lower() == "completed"
    )

    return render(

        request,

        "interview/resumes.html",

        {
            "interviews": all_interviews,
            "pending_count": pending_count,
            "completed_count": completed_count,
        }
    )
def generate_questions_ajax(request):

    if request.method != "POST":

        return JsonResponse({
            "status": "error",
            "message": "POST required."
        }, status=400)

    try:

        data = json.loads(request.body)

        interview_id = data.get(
            "interview_id"
        )


        interview = get_interview(
            interview_id
        )

        if not interview:

            return JsonResponse({
                "status": "error",
                "message": "Interview not found."
            }, status=404)
        max_questions = int(interview.get("question_count", 10))
        all_skills = interview.get(

            "skills",

            []
        )
        skills = all_skills[:7]
        projects = interview.get(
            "projects",
            []
        )

        experience = interview.get(
            "experience",
            []
        )

        questions_dict = generate_questions(

            skills=skills,

            projects=projects,

            experience=experience,

            max_questions=max_questions
        )

        provider = "openrouter"

        update_questions(

            interview_id,

            questions_dict,

            provider=provider,

            question_count=max_questions
        )

        return JsonResponse({

            "status": "success",

            "questions": questions_dict,

            "provider": provider,
            "model": provider,
        })

    except Exception as e:

        print(
            "QUESTION GENERATION ERROR:",
            e
        )

        return JsonResponse({

            "status": "error",
    
            "message": str(e)
        }, status=500)

def finalize_questions(request):

    if request.method == "POST":

        selected_questions = request.POST.getlist(
            "selected_questions"
        )

        request.session[
            "final_questions"
        ] = selected_questions

        return redirect(
            "/dashboard/"
        )
def questions_page(

    request,

    interview_id
):

    interview = get_interview(
        interview_id
    )

    if not interview:

        return redirect("/")
    finalized = False

    # --------------------------------------------------
    # FINALIZE SELECTED QUESTIONS
    # --------------------------------------------------

    if request.method == "POST":

        selected_questions = request.POST.getlist(
            "selected_questions"
        )

        if not selected_questions:
            return render(
                request,
                "interview/questions.html",
                {
                    "interview": interview,
                    "questions": interview.get(
                        "generated_questions",
                        {}
                    ),
                    "finalized": False,
                    "error": (
                        "Select at least one question "
                        "before finalizing the interview."
                    ),
                }
            )

        parsed_questions = []
        final_questions = parsed_questions
        for q in selected_questions:

            try:

                parsed_questions.append(
                    json.loads(q)
                )

            except Exception:

                parsed_questions.append({

                    "question": q,

                    "skill": "General",

                    "difficulty": "medium",

                    "type": "conceptual"
                })

        # Save selected questions to BOTH fields:
        # 'generated_questions' for questions page display
        # 'questions' for candidate_interview view to read
        from core.database import interviews_collection
        # Enforce server-side cap
        question_count = interview.get("question_count", 10)
        parsed_questions = parsed_questions[:question_count]
        interviews_collection.update_one(
            {"interview_id": interview_id},
            {
                "$set": {
                    "questions": parsed_questions,
                    "provider": "selected",
                    "finalized": True,
                }
            }
        )

        # Reload updated interview
        interview = get_interview(interview_id)
        finalized = True

    # --------------------------------------------------
    # SHOW FINALIZED QUESTIONS AFTER FINALIZATION
    # --------------------------------------------------

    if interview.get("finalized"):

        raw_questions = interview.get(
            "questions",
            []
        )

        grouped_questions = {}

        for q in raw_questions:

            skill = (
                q.get("skill", "General")
                if isinstance(q, dict)
                else "General"
            )

            if skill not in grouped_questions:
                grouped_questions[skill] = []

            grouped_questions[skill].append(q)

        questions = grouped_questions

    else:

        questions = interview.get(
            "generated_questions",
            {}
        )
    print("FINALIZED =", finalized)
    print("QUESTIONS =", questions)
    return render(

        request,

        "interview/questions.html",

        {

            "interview": interview,

            "questions": questions,

            "finalized": finalized,
        }
    )
@csrf_exempt
def upload_video_chunk(request):

    if request.method == "POST":

        video_file = request.FILES.get(
            "video_chunk"
        )

        interview_id = request.POST.get(
            "interview_id"
        )

        if not video_file:
            return JsonResponse({
                "status": "error"
            })

        save_dir = os.path.join(
            settings.MEDIA_ROOT,
            "video_chunks",
            interview_id
        )

        os.makedirs(
            save_dir,
            exist_ok=True
        )

        file_path = os.path.join(
            save_dir,
            video_file.name
        )

        with open(file_path, "wb+") as f:
            for chunk in video_file.chunks():
                f.write(chunk)

        interview = get_interview(interview_id)

        existing_chunks = interview.get(
            "video_chunks",
            []
        )

        existing_chunks.append(file_path)

        from core.database import interviews_collection

        interviews_collection.update_one(
            {
                "interview_id": interview_id
            },
            {
                "$set": {
                    "video_chunks": existing_chunks
                }
            }
        )

        return JsonResponse({
            "status": "success"
        })
# ================================================================
# ADD THESE IMPORTS AT THE TOP OF views.py (if not already there)
# ================================================================
# from core.database import get_interview, get_all_interviews
# from core.ats import calculate_ats_score

# ================================================================
# PASTE THESE FUNCTIONS INTO views.py
# ================================================================


# ── RESUME ANALYSIS ──────────────────────────────────────────────
def resume_analysis(request, interview_id):
    interview = get_interview(interview_id)
    if not interview:
        return redirect('home')

    # Use stored summary if exists, else generate and store
    summary_text = interview.get("summary_text", "")
    if not summary_text:
        try:
            from core.services.Report_service import generate_summary_text
            summary_text = generate_summary_text(interview)
            save_summary(interview_id, summary_text)
        except Exception as e:
            print(f"[Summary] Generation failed: {e}")
            summary_text = ""

    # Parse summary into structured lines for display
    summary_lines = []
    for line in summary_text.splitlines():
        line = line.strip()
        if not line:
            continue
        if ":" in line:
            key, _, value = line.partition(":")
            summary_lines.append({
                "key":   key.strip(),
                "value": value.strip()
            })
        else:
            summary_lines.append({
                "key":   "",
                "value": line
            })

    return render(request, 'interview/resume_analysis.html', {
        'interview':              interview,
        'interview_id':           interview_id,
        'summary_text':           summary_text,
        'summary_lines':          summary_lines,
        'experience_structured':  interview.get('experience_structured', []),
        'education_structured':   interview.get('education_structured', []),
        'projects_structured':    interview.get('projects_structured', []),
    })

# ── ATS SCORE ────────────────────────────────────────────────────
def ats_score_page(request, interview_id):
    interview = get_interview(interview_id)
    if not interview:
        return redirect('home')

    ats_score = interview.get('ats_score', 0)

    # Derive sub-scores from what we have
    skills_count     = len(interview.get('skills', []))
    experience_count = len(interview.get('experience', []))
    projects_count   = len(interview.get('projects', []))
    education_count  = len(interview.get('education', []))

    keywords_score   = min(100, ats_score + 5)
    skills_score     = min(100, 30 if skills_count >= 5 else skills_count * 6)
    experience_score = min(100, 25 if experience_count >= 1 else 0)
    format_score     = min(100, ats_score)

    # SVG circle: circumference = 2 * pi * 50 ≈ 314
    circumference = 314
    dash_offset   = circumference - (circumference * ats_score / 100)

    return render(request, 'interview/ats_score.html', {
        'interview':       interview,
        'interview_id':    interview_id,
        'ats_score':       ats_score,
        'keywords_score':  keywords_score,
        'skills_score':    skills_score,
        'experience_score': experience_score,
        'format_score':    format_score,
        'circumference':   circumference,
        'dash_offset':     round(dash_offset, 2),
    })


# ── SKILLS PAGE ──────────────────────────────────────────────────
def skills_page(request, interview_id):
    interview = get_interview(interview_id)
    if not interview:
        return redirect('home')

    all_skills = interview.get('skills', [])
    ats_score  = interview.get('ats_score', 0)

    # Heuristic split: treat common soft-skill words separately
    SOFT_SKILL_KEYWORDS = {
        'communication', 'teamwork', 'leadership', 'problem solving',
        'critical thinking', 'time management', 'collaboration',
        'adaptability', 'creativity', 'presentation', 'negotiation',
        'interpersonal', 'organisation', 'organization', 'management',
    }

    technical_skills = [
        s for s in all_skills
        if s.lower() not in SOFT_SKILL_KEYWORDS
    ]
    soft_skills = [
        s for s in all_skills
        if s.lower() in SOFT_SKILL_KEYWORDS
    ]

    # Strong = first 60%, improve = rest
    split       = max(1, int(len(technical_skills) * 0.6))
    strong_skills  = technical_skills[:split]
    improve_skills = technical_skills[split:]

    # Build proficiency bars (deterministic from skill name length as proxy)
    import hashlib
    skill_bars = []
    for skill in all_skills[:12]:   # cap at 12 for readability
        h     = int(hashlib.md5(skill.encode()).hexdigest(), 16)
        level = 60 + (h % 35)       # 60–94 %
        skill_bars.append({'name': skill, 'level': level})

    return render(request, 'interview/skills.html', {
        'interview':       interview,
        'interview_id':    interview_id,
        'all_skills':      all_skills,
        'technical_skills': technical_skills,
        'soft_skills':     soft_skills,
        'strong_skills':   strong_skills,
        'improve_skills':  improve_skills,
        'skill_bars':      skill_bars,
        'total_skills':    len(all_skills),
        'technical_count': len(technical_skills),
        'soft_count':      len(soft_skills),
        'ats_score':       ats_score,
    })


# ── HISTORY PAGE ─────────────────────────────────────────────────
def history_page(request):
    all_interviews = get_all_interviews()

    completed = [i for i in all_interviews if i.get('status') == 'completed']
    scores    = [
        i.get('overall_score', 0)
        for i in completed
        if i.get('overall_score')
    ]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0

    best_resume = None
    best_score  = 0
    for iv in completed:
        s = iv.get('overall_score', 0)
        if s > best_score:
            best_score  = s
            best_resume = iv

    total_questions = sum(
        i.get('question_count', 0) for i in all_interviews
    )

    return render(request, 'interview/history.html', {
        'interviews':          all_interviews,
        'total_interviews':    len(all_interviews),
        'completed_interviews': len(completed),
        'pending_count':       len(all_interviews) - len(completed),
        'average_score':       avg_score,
        'total_questions':     total_questions,
        'best_resume':         best_resume,
        'best_score':          best_score,
        # sidebar needs interview_id=None (no active interview on history page)
        'interview_id':        None,
    })
def download_report(request, interview_id):
    """Generate and download the resume summary report as PDF."""
    from django.http import HttpResponse

    interview = get_interview(interview_id)
    if not interview:
        return redirect('home')

    try:
        pdf_bytes = generate_report_pdf(interview)

        name = interview.get("name", "candidate").replace(" ", "_")
        filename = f"Resume_Report_{name}.pdf"

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    except Exception as e:
        print(f"[ReportService] PDF generation failed: {e}")
        return redirect('resume_analysis', interview_id=interview_id)

