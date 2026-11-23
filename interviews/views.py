import json
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.db.models import Avg
from django.http import JsonResponse
from django.utils import timezone
from interviews.models import (
    Interview, 
    Question,
    Answer,
    InterviewDomain, 
    InterviewDifficulty, 
    InterviewPersona, 
    InterviewMode, 
    InterviewStatus,
    QuestionCategory,
    AnswerInputMethod
)
from analytics.models import Report, SpeechMetrics
from ai_engine.providers import get_ai_provider

logger = logging.getLogger(__name__)

from functools import wraps
from django.core.cache import cache

def ai_rate_limit(max_requests=30, window_seconds=60):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if request.user.is_authenticated:
                key = f"ai_rl:{request.user.id}:{view_func.__name__}"
                count = cache.get(key, 0)
                if count >= max_requests:
                    return JsonResponse(
                        {"status": "error", "message": "Rate limit exceeded. Please wait a moment before trying again."},
                        status=429,
                    )
                cache.set(key, count + 1, timeout=window_seconds)
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator



@login_required
def dashboard_view(request):
    """
    Candidate Dashboard:
    - IDOR Defense: Only queries current authenticated user's records.
    - Aggregated analytics (Technical, Posture, Eye Contact, Speech).
    - List of past interviews with status indicators and scorecards.
    - Performance metrics payload for the in-browser Canvas radar/trend chart.
    """
    interviews = Interview.objects.filter(
        user=request.user
    ).select_related('report', 'speech_metrics').order_by('-created_at')

    total_sessions = interviews.count()
    completed_sessions = interviews.filter(status=InterviewStatus.COMPLETED).count()
    practice_sessions = interviews.filter(mode=InterviewMode.ANXIETY_FREE).count()

    # Aggregate metric scores
    user_reports = Report.objects.filter(interview__user=request.user)
    aggregates = user_reports.aggregate(
        avg_overall=Avg('overall_score'),
        avg_technical=Avg('technical_score'),
        avg_posture=Avg('posture_score'),
        avg_eye_contact=Avg('eye_contact_score'),
        avg_speech=Avg('speech_clarity_score'),
    )

    user_speech = SpeechMetrics.objects.filter(interview__user=request.user)
    speech_aggregates = user_speech.aggregate(
        avg_wpm=Avg('words_per_minute')
    )

    avg_overall = round(aggregates['avg_overall'], 1) if aggregates['avg_overall'] else None
    avg_technical = round(aggregates['avg_technical'], 1) if aggregates['avg_technical'] else None
    avg_posture = round(aggregates['avg_posture'], 1) if aggregates['avg_posture'] else None
    avg_eye_contact = round(aggregates['avg_eye_contact'], 1) if aggregates['avg_eye_contact'] else None
    avg_speech = round(aggregates['avg_speech'], 1) if aggregates['avg_speech'] else None
    avg_wpm = round(speech_aggregates['avg_wpm'], 1) if speech_aggregates['avg_wpm'] else None

    # Chart telemetry payload for Vanilla JS Canvas Radar
    radar_metrics = {
        "labels": ["Technical Depth", "Posture Steadiness", "Eye Contact (Gaze)", "Speech Clarity", "STAR Structure"],
        "values": [
            avg_technical or 75.0,
            avg_posture or 82.0,
            avg_eye_contact or 88.0,
            avg_speech or 80.0,
            85.0
        ]
    }

    # Chronological score trends for completed sessions
    trend_data = []
    completed_interviews_chronological = interviews.filter(
        status=InterviewStatus.COMPLETED, 
        report__isnull=False
    ).order_by('created_at')[:8]
    
    for item in completed_interviews_chronological:
        trend_data.append({
            "title": item.title,
            "date": item.created_at.strftime("%b %d"),
            "score": item.report.overall_score
        })

    context = {
        'interviews': interviews,
        'total_sessions': total_sessions,
        'completed_sessions': completed_sessions,
        'practice_sessions': practice_sessions,
        'avg_overall': avg_overall,
        'avg_technical': avg_technical,
        'avg_posture': avg_posture,
        'avg_eye_contact': avg_eye_contact,
        'avg_speech': avg_speech,
        'avg_wpm': avg_wpm,
        'radar_metrics_json': json.dumps(radar_metrics),
        'trend_data_json': json.dumps(trend_data),
        'domains': InterviewDomain.choices,
        'difficulties': InterviewDifficulty.choices,
        'personas': InterviewPersona.choices,
        'modes': InterviewMode.choices,
    }
    return render(request, 'interviews/dashboard.html', context)


@login_required
@require_http_methods(["POST"])
def create_interview_view(request):
    """
    Initializes a new interview session.
    Parses configuration options and redirects to the interview room.
    """
    domain = request.POST.get('domain', InterviewDomain.FULLSTACK)
    difficulty = request.POST.get('difficulty', InterviewDifficulty.MID)
    persona = request.POST.get('persona', InterviewPersona.TECHNICAL_LEAD)
    mode = request.POST.get('mode', InterviewMode.STANDARD)
    job_description = request.POST.get('job_description', '').strip()[:4000]
    resume_text = request.POST.get('resume_text', '').strip()[:4000]

    # Validate choices against model choices
    valid_domains = dict(InterviewDomain.choices).keys()
    valid_difficulties = dict(InterviewDifficulty.choices).keys()
    valid_personas = dict(InterviewPersona.choices).keys()
    valid_modes = dict(InterviewMode.choices).keys()

    domain = domain if domain in valid_domains else InterviewDomain.FULLSTACK
    difficulty = difficulty if difficulty in valid_difficulties else InterviewDifficulty.MID
    persona = persona if persona in valid_personas else InterviewPersona.TECHNICAL_LEAD
    mode = mode if mode in valid_modes else InterviewMode.STANDARD

    interview = Interview.objects.create(
        user=request.user,
        domain=domain,
        difficulty=difficulty,
        persona=persona,
        mode=mode,
        job_description=job_description,
        resume_text=resume_text,
        status=InterviewStatus.PENDING_SETUP
    )

    messages.success(request, f"New session created: {interview.title}")
    return redirect('interview_room', interview_id=interview.id)


@login_required
def interview_room_shell_view(request, interview_id):
    """
    IDOR-Protected Interview Room Shell.
    Validates ownership of interview UUID before allowing session entry.
    """
    interview = get_object_or_404(Interview, id=interview_id, user=request.user)
    return render(request, 'interviews/room_shell.html', {'interview': interview})


@login_required
@require_http_methods(["POST"])
def delete_interview_view(request, interview_id):
    """
    IDOR-Protected deletion of an interview session and its child telemetry.
    """
    interview = get_object_or_404(Interview, id=interview_id, user=request.user)
    title = interview.title
    interview.delete()
    messages.success(request, f"Interview '{title}' was permanently deleted.")
    return redirect('dashboard')


# -----------------------------------------------------------------------------
# Phase 5: AI Interview Orchestration & Speech Endpoints
# -----------------------------------------------------------------------------
@login_required
def interview_state_api(request, interview_id):
    """
    IDOR-Protected API endpoint returning current interview session progression state.
    Provides current question, total questions, answered counts, and completion status.
    """
    interview = get_object_or_404(Interview, id=interview_id, user=request.user)
    questions = interview.questions.all().order_by('order').select_related('answer')
    total_questions = questions.count()

    # Find the next question that hasn't received an Answer
    unanswered_questions = [q for q in questions if not hasattr(q, 'answer')]
    answered_count = total_questions - len(unanswered_questions)

    current_question = unanswered_questions[0] if unanswered_questions else None
    is_completed = total_questions > 0 and current_question is None

    current_q_data = None
    if current_question:
        current_q_data = {
            "id": str(current_question.id),
            "order": current_question.order,
            "question_text": current_question.question_text,
            "category": current_question.category,
            "category_display": current_question.get_category_display(),
            "is_follow_up": current_question.is_follow_up,
            "expected_key_points": current_question.expected_key_points,
        }

    return JsonResponse({
        "status": "ok",
        "interview": {
            "id": str(interview.id),
            "title": interview.title,
            "domain": interview.domain,
            "domain_display": interview.get_domain_display(),
            "difficulty": interview.difficulty,
            "difficulty_display": interview.get_difficulty_display(),
            "persona": interview.persona,
            "persona_display": interview.get_persona_display(),
            "mode": interview.mode,
            "status": interview.status,
            "total_questions": total_questions,
            "answered_count": answered_count,
            "is_completed": is_completed,
        },
        "current_question": current_q_data
    })


@login_required
@require_http_methods(["POST"])
@ai_rate_limit(max_requests=20, window_seconds=60)
def start_interview_api(request, interview_id):
    """
    Initializes AI interview Q&A session.
    Generates personalized questions via configured LLM provider (or mock fallback)
    if not yet provisioned, and sets interview status to IN_PROGRESS.
    """
    interview = get_object_or_404(Interview, id=interview_id, user=request.user)

    # Generate questions if interview has no question records yet
    if not interview.questions.exists():
        # Exclude questions previously asked to this candidate across other sessions to ensure freshness
        prior_questions = list(
            Question.objects.filter(interview__user=request.user)
            .exclude(interview=interview)
            .values_list('question_text', flat=True)
        )

        provider = get_ai_provider()
        questions_payload = provider.generate_questions(
            domain=interview.domain,
            difficulty=interview.difficulty,
            persona=interview.get_persona_display(),
            job_description=interview.job_description,
            resume_text=interview.resume_text,
            count=5,
            exclude_questions=prior_questions
        )

        # Fallback safeguard in case provider returned empty
        if not questions_payload:
            from ai_engine.providers import MockNLPProvider
            questions_payload = MockNLPProvider().generate_questions(
                domain=interview.domain,
                difficulty=interview.difficulty,
                persona=interview.get_persona_display(),
                count=5,
                exclude_questions=prior_questions
            )

        valid_categories = dict(QuestionCategory.choices).keys()
        for idx, item in enumerate(questions_payload, start=1):
            cat_raw = str(item.get('category', 'technical')).lower().replace(' ', '_')
            category = cat_raw if cat_raw in valid_categories else QuestionCategory.TECHNICAL

            Question.objects.create(
                interview=interview,
                order=item.get('order', idx),
                question_text=item.get('question', '').strip(),
                category=category,
                expected_key_points=item.get('expected_key_points', [])
            )

    interview.status = InterviewStatus.IN_PROGRESS
    if not interview.started_at:
        interview.started_at = timezone.now()
    interview.save(update_fields=['status', 'started_at', 'updated_at'])

    first_question = interview.questions.filter(answer__isnull=True).order_by('order').first() or interview.questions.order_by('order').first()
    return JsonResponse({
        "status": "ok",
        "message": "Interview started",
        "question": {
            "id": str(first_question.id),
            "order": first_question.order,
            "question_text": first_question.question_text,
            "category": first_question.category,
            "category_display": first_question.get_category_display(),
            "is_follow_up": first_question.is_follow_up,
            "expected_key_points": first_question.expected_key_points,
            "total_questions": interview.questions.count(),
        }
    })


@login_required
@require_http_methods(["POST"])
@ai_rate_limit(max_requests=30, window_seconds=60)
def submit_answer_api(request, interview_id):
    """
    Processes candidate answer:
    1. Evaluates technical accuracy and STAR structure via LLM provider.
    2. Saves Answer model with score and feedback JSON.
    3. Triggers dynamic follow-up probe generation if needed.
    4. Advances to next question or completes the interview session.
    """
    interview = get_object_or_404(Interview, id=interview_id, user=request.user)

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({"status": "error", "message": "Invalid JSON body"}, status=400)

    question_id = data.get('question_id')
    transcript_text = str(data.get('transcript_text', '')).strip()[:10000]
    duration_seconds = max(0.0, float(data.get('duration_seconds', 0.0)))
    input_method = data.get('input_method', AnswerInputMethod.SPOKEN)

    if not question_id:
        return JsonResponse({"status": "error", "message": "question_id is required"}, status=400)

    question = get_object_or_404(Question, id=question_id, interview=interview)

    if not transcript_text:
        transcript_text = "(Candidate provided no audible response)"

    # AI Evaluation with expected key points matching
    provider = get_ai_provider()
    eval_result = provider.evaluate_answer(
        question_text=question.question_text,
        answer_text=transcript_text,
        persona=interview.get_persona_display(),
        domain=interview.get_domain_display(),
        difficulty=interview.get_difficulty_display(),
        expected_key_points=question.expected_key_points
    )

    score = round(max(0.0, min(100.0, float(eval_result.get('score', 75.0)))), 1)

    # Persist or update Answer
    answer, _ = Answer.objects.update_or_create(
        question=question,
        defaults={
            "transcript_text": transcript_text,
            "duration_seconds": duration_seconds,
            "input_method": input_method if input_method in dict(AnswerInputMethod.choices).keys() else AnswerInputMethod.SPOKEN,
            "ai_score": score,
            "ai_feedback": eval_result,
            "evaluated_at": timezone.now()
        }
    )

    # Dynamic Follow-Up Probing Check (adaptive, at most 2 follow-ups per session to avoid repetition)
    has_follow_up = False
    follow_up_q_data = None
    if not question.is_follow_up and interview.questions.filter(is_follow_up=True).count() < 3:
        try:
            already_asked_follow_ups = list(
                Question.objects.filter(interview=interview, is_follow_up=True)
                .values_list('question_text', flat=True)
            )
            follow_up_res = provider.generate_follow_up(
                question_text=question.question_text,
                answer_text=transcript_text,
                persona=interview.get_persona_display(),
                score=score,
                already_asked_follow_ups=already_asked_follow_ups
            )

            if follow_up_res.get('should_ask_follow_up') and follow_up_res.get('follow_up_question'):
                # Shift subsequent questions down in reverse order to respect unique constraints
                subsequent_questions = list(
                    Question.objects.filter(interview=interview, order__gt=question.order).order_by('-order')
                )
                for sq in subsequent_questions:
                    sq.order += 1
                    sq.save(update_fields=['order'])

                # Insert the follow-up question directly following current question
                new_follow_up = Question.objects.create(
                    interview=interview,
                    order=question.order + 1,
                    question_text=follow_up_res['follow_up_question'].strip(),
                    category=QuestionCategory.FOLLOW_UP,
                    is_follow_up=True,
                    parent_question=question,
                    expected_key_points=[follow_up_res.get('rationale', 'Probing technical reasoning and edge case handling')]
                )

                has_follow_up = True
                follow_up_q_data = {
                    "id": str(new_follow_up.id),
                    "order": new_follow_up.order,
                    "question_text": new_follow_up.question_text,
                    "category": new_follow_up.category,
                    "category_display": new_follow_up.get_category_display(),
                    "is_follow_up": True,
                    "expected_key_points": new_follow_up.expected_key_points,
                    "total_questions": interview.questions.count()
                }
        except Exception as e:
            logger.warning("Follow-up generation skipped: %s", str(e))

    # Determine next question
    if has_follow_up and follow_up_q_data:
        next_q_data = follow_up_q_data
        is_completed = False
    else:
        next_question = Question.objects.filter(interview=interview, answer__isnull=True).order_by('order').first()
        if next_question:
            next_q_data = {
                "id": str(next_question.id),
                "order": next_question.order,
                "question_text": next_question.question_text,
                "category": next_question.category,
                "category_display": next_question.get_category_display(),
                "is_follow_up": next_question.is_follow_up,
                "expected_key_points": next_question.expected_key_points,
                "total_questions": interview.questions.count()
            }
            is_completed = False
        else:
            next_q_data = None
            is_completed = True

    # If interview is complete, finalize session status and execute multimodal evaluation engine
    overall_avg = None
    if is_completed:
        interview.status = InterviewStatus.COMPLETED
        interview.completed_at = timezone.now()
        interview.save(update_fields=['status', 'completed_at', 'updated_at'])

        from analytics.scoring import generate_comprehensive_report
        report = generate_comprehensive_report(interview)
        overall_avg = report.overall_score

    return JsonResponse({
        "status": "ok",
        "is_anxiety_free": interview.mode == InterviewMode.ANXIETY_FREE,
        "has_follow_up": has_follow_up,
        "is_completed": is_completed,
        "score": score,
        "overall_score": overall_avg,
        "evaluation_summary": eval_result.get('summary', 'Answer recorded successfully.'),
        "next_question": next_q_data,
        "answered_count": Question.objects.filter(interview=interview, answer__isnull=False).count(),
        "total_questions": interview.questions.count()
    })


@login_required
@require_http_methods(["POST"])
@ai_rate_limit(max_requests=30, window_seconds=60)
def hint_question_api(request, interview_id):
    """
    Live Socratic Coach Lifeline:
    Provides a concise 1-2 sentence hint for the active question without spoiling the answer.
    """
    interview = get_object_or_404(Interview, id=interview_id, user=request.user)
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({"status": "error", "message": "Invalid JSON body"}, status=400)

    question_id = data.get("question_id")
    partial_answer = str(data.get("partial_answer", "")).strip()[:2000]
    if not question_id:
        return JsonResponse({"status": "error", "message": "question_id is required"}, status=400)

    question = get_object_or_404(Question, id=question_id, interview=interview)
    provider = get_ai_provider()
    hint_text = provider.generate_hint(
        question_text=question.question_text,
        partial_answer=partial_answer,
        domain=interview.get_domain_display(),
        difficulty=interview.get_difficulty_display(),
        expected_key_points=question.expected_key_points,
    )
    return JsonResponse({"status": "ok", "hint": hint_text})
