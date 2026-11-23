import json
import logging
from django.http import JsonResponse, FileResponse
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from interviews.models import Interview, InterviewStatus
from analytics.models import (
    EnvironmentCheck, 
    LightingStatus, 
    PostureEvent, 
    PostureEventType, 
    PostureSeverity,
    Report,
    SpeechMetrics
)
from analytics.scoring import generate_comprehensive_report
from analytics.reports import generate_pdf_report

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["POST"])
def save_tech_check_view(request, interview_id):
    """
    Saves or updates EnvironmentCheck results from the client-side Tech Check Wizard.
    Enforces IDOR defense and strict validation/clamping of client metrics.
    Zero video upload: Only numeric telemetry and boolean status flags are accepted.
    """
    interview = get_object_or_404(Interview, id=interview_id, user=request.user)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON payload.'}, status=400)

    # Validate and clamp numerical metrics (untrusted client input)
    try:
        camera_ok = bool(data.get('camera_ok', False))
        mic_ok = bool(data.get('mic_ok', False))
        
        raw_luminance = float(data.get('luminance_score', 0.0))
        luminance_score = max(0.0, min(100.0, round(raw_luminance, 1)))

        raw_audio_rms = float(data.get('audio_level_rms', 0.0))
        audio_level_rms = max(0.0, min(100.0, round(raw_audio_rms, 2)))

        raw_readiness = float(data.get('readiness_score', 0.0))
        readiness_score = max(0.0, min(100.0, round(raw_readiness, 1)))

        background_clutter_detected = bool(data.get('background_clutter_detected', False))
        phone_detected = bool(data.get('phone_detected', False))

        raw_lighting_status = str(data.get('lighting_status', LightingStatus.GOOD)).lower()
        valid_lighting = [choice[0] for choice in LightingStatus.choices]
        if raw_lighting_status not in valid_lighting:
            raw_lighting_status = LightingStatus.GOOD

        raw_suggestions = data.get('suggestions', [])
        if isinstance(raw_suggestions, list):
            suggestions = [str(s)[:250] for s in raw_suggestions[:10]]
        else:
            suggestions = []
    except (TypeError, ValueError) as err:
        return JsonResponse({'status': 'error', 'message': f'Validation failed: {str(err)}'}, status=400)

    # Update or create EnvironmentCheck
    env_check, created = EnvironmentCheck.objects.update_or_create(
        interview=interview,
        defaults={
            'camera_ok': camera_ok,
            'mic_ok': mic_ok,
            'luminance_score': luminance_score,
            'lighting_status': raw_lighting_status,
            'audio_level_rms': audio_level_rms,
            'background_clutter_detected': background_clutter_detected,
            'phone_detected': phone_detected,
            'readiness_score': readiness_score,
            'suggestions': suggestions,
        }
    )

    # Advance interview status from PENDING_SETUP to IN_PROGRESS if ready
    if readiness_score >= 60.0 and camera_ok and mic_ok:
        if interview.status == InterviewStatus.PENDING_SETUP:
            interview.status = InterviewStatus.IN_PROGRESS
            interview.save(update_fields=['status'])

    return JsonResponse({
        'status': 'success',
        'readiness_score': env_check.readiness_score,
        'lighting_status': env_check.lighting_status,
        'camera_ok': env_check.camera_ok,
        'mic_ok': env_check.mic_ok,
        'suggestions': env_check.suggestions,
        'interview_status': interview.status,
    })


@login_required
@require_http_methods(["POST"])
def save_baseline_calibration_view(request, interview_id):
    """
    Saves candidate's neutral posture & gaze baseline captured during the
    10-second calibration countdown. Eliminates false positives from camera angle tilts.
    Zero video upload: only coordinates & geometric ratios are retained.
    """
    interview = get_object_or_404(Interview, id=interview_id, user=request.user)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON payload.'}, status=400)

    try:
        baseline = {
            "face_center_x": round(max(0.0, min(1.0, float(data.get('face_center_x', 0.5)))), 4),
            "face_center_y": round(max(0.0, min(1.0, float(data.get('face_center_y', 0.42)))), 4),
            "face_scale": round(max(0.01, min(1.0, float(data.get('face_scale', 0.2)))), 4),
            "shoulder_tilt": round(max(-1.0, min(1.0, float(data.get('shoulder_tilt', 0.0)))), 4),
            "gaze_origin_x": round(max(0.0, min(1.0, float(data.get('gaze_origin_x', 0.5)))), 4),
            "gaze_origin_y": round(max(0.0, min(1.0, float(data.get('gaze_origin_y', 0.4)))), 4),
            "calibrated_samples": max(1, min(500, int(data.get('calibrated_samples', 60)))),
        }
    except (TypeError, ValueError) as err:
        return JsonResponse({'status': 'error', 'message': f'Invalid numeric baseline: {str(err)}'}, status=400)

    interview.calibration_baseline = baseline
    interview.save(update_fields=['calibration_baseline', 'updated_at'])

    return JsonResponse({
        'status': 'ok',
        'message': 'Baseline calibration coordinates saved.',
        'baseline': baseline
    })


@login_required
@require_http_methods(["POST"])
def save_posture_telemetry_batch_view(request, interview_id):
    """
    Batch ingestion endpoint for temporal posture and gaze events detected client-side.
    Enforces IDOR defense, validates event types and severities, and bulk-inserts PostureEvents.
    Zero video upload: video frames never leave client memory; only timestamped telemetry is stored.
    """
    interview = get_object_or_404(Interview, id=interview_id, user=request.user)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON payload.'}, status=400)

    events_raw = data.get('events', [])
    if not isinstance(events_raw, list):
        return JsonResponse({'status': 'error', 'message': 'Expected events array.'}, status=400)

    valid_types = dict(PostureEventType.choices).keys()
    valid_severities = dict(PostureSeverity.choices).keys()

    new_events = []
    for item in events_raw[:100]:  # Cap at 100 per batch for rate defense
        event_type = str(item.get('event_type', '')).lower()
        if event_type not in valid_types:
            continue

        severity = str(item.get('severity', PostureSeverity.LOW)).lower()
        if severity not in valid_severities:
            severity = PostureSeverity.LOW

        try:
            start_offset_ms = max(0, int(item.get('start_offset_ms', 0)))
            end_offset_ms = item.get('end_offset_ms')
            if end_offset_ms is not None:
                end_offset_ms = max(start_offset_ms, int(end_offset_ms))
        except (TypeError, ValueError):
            continue

        raw_details = item.get('details', {})
        details = raw_details if isinstance(raw_details, dict) else {}

        new_events.append(PostureEvent(
            interview=interview,
            event_type=event_type,
            severity=severity,
            start_offset_ms=start_offset_ms,
            end_offset_ms=end_offset_ms,
            details=details
        ))

    saved_count = len(new_events)
    if new_events:
        PostureEvent.objects.bulk_create(new_events)

    return JsonResponse({
        'status': 'ok',
        'saved_count': saved_count
    })


# -----------------------------------------------------------------------------
# Phase 7: Multimodal Analytics, Scorecard & PDF Report Endpoints
# -----------------------------------------------------------------------------
@login_required
def interview_report_view(request, interview_id):
    """
    IDOR-Protected Comprehensive Interview Evaluation Scorecard View.
    Calculates or updates multi-modal scoring and renders Glassmorphism report
    with 5-axis Canvas radar chart, STAR analysis, and posture/gaze telemetry.
    """
    interview = get_object_or_404(Interview, id=interview_id, user=request.user)

    # Compute or retrieve the comprehensive report
    report = generate_comprehensive_report(interview)

    # Fetch associated questions, answers, and telemetry
    questions = interview.questions.all().order_by('order').select_related('answer')
    speech = getattr(interview, 'speech_metrics', None)
    tech_check = getattr(interview, 'environment_check', None)
    posture_events = PostureEvent.objects.filter(interview=interview).order_by('start_offset_ms')

    # Prepare radar chart JSON for HTML5 Canvas
    star_composite = 80.0
    if report.behavioral_star_feedback and isinstance(report.behavioral_star_feedback, dict):
        star_composite = float(report.behavioral_star_feedback.get('composite_star_score', 80.0))

    radar_payload = {
        "labels": ["Technical Depth", "Posture Steadiness", "Eye Contact (Gaze)", "Speech Clarity", "STAR Structure"],
        "values": [
            report.technical_score,
            report.posture_score,
            report.eye_contact_score,
            report.speech_clarity_score,
            star_composite
        ]
    }

    # Format session duration
    duration_str = None
    if interview.completed_at and interview.started_at:
        mins = int((interview.completed_at - interview.started_at).total_seconds() / 60)
        secs = int((interview.completed_at - interview.started_at).total_seconds() % 60)
        duration_str = f"{mins}m {secs}s"

    context = {
        'interview': interview,
        'report': report,
        'questions': questions,
        'speech': speech,
        'tech_check': tech_check,
        'posture_events_count': posture_events.count(),
        'posture_events': posture_events[:50],  # Limit to 50 for page responsiveness
        'radar_payload_json': json.dumps(radar_payload),
        'duration_str': duration_str,
        'star': report.behavioral_star_feedback or {},
    }
    return render(request, 'analytics/report_detail.html', context)


@login_required
def interview_report_pdf_view(request, interview_id):
    """
    IDOR-Protected endpoint that generates and streams a high-resolution,
    multi-page candidate evaluation PDF scorecard via ReportLab.
    """
    interview = get_object_or_404(Interview, id=interview_id, user=request.user)
    
    # Generate in-memory PDF buffer
    pdf_buffer = generate_pdf_report(interview)

    safe_title = "".join(c for c in interview.title if c.isalnum() or c in (' ', '-', '_')).strip().replace(' ', '_')
    filename = f"Evaluation_{safe_title}_{str(interview.id)[:8]}.pdf"

    return FileResponse(
        pdf_buffer, 
        as_attachment=True, 
        filename=filename, 
        content_type='application/pdf'
    )

