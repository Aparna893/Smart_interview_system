from django.urls import path
from . import views

urlpatterns = [

    # ── HOME / DASHBOARD ──────────────────────────────
    path('',
         views.home,
         name='home'),

    # ── NEW SIDEBAR PAGES ─────────────────────────────
    path('resume-analysis/<str:interview_id>/',
         views.resume_analysis,
         name='resume_analysis'),

    path('ats-score/<str:interview_id>/',
         views.ats_score_page,
         name='ats_score'),

    path('skills/<str:interview_id>/',
         views.skills_page,
         name='skills_page'),

    path('history/',
         views.history_page,
         name='history'),

    # ── QUESTIONS ─────────────────────────────────────
    path('questions/<str:interview_id>/',
         views.questions_page,
         name='questions_page'),

    path('generate_questions_ajax/',
         views.generate_questions_ajax,
         name='generate_questions_ajax'),

    # ── CANDIDATE INTERVIEW ───────────────────────────
    path('candidate/<str:interview_id>/',
         views.candidate_interview,
         name='candidate_interview'),

    path('submit_interview/',
         views.submit_interview,
         name='submit_interview'),

    path('upload_video_chunk/',
         views.upload_video_chunk,
         name='upload_video_chunk'),

     path(
        'download-report/<str:interview_id>/',
        views.download_report,
        name='download_report',
     ),
    # ── REVIEW ────────────────────────────────────────
    path('review/<str:interview_id>/',
         views.review_interview,
         name='review_interview'),

    # ── LEGACY (kept for back-compat) ─────────────────
    path('dashboard/',
         views.history_page,
         name='dashboard'),

    path('resumes/',
         views.history_page,
         name='resumes'),
]
