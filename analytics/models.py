import uuid
import os
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.core.validators import MinValueValidator, MaxValueValidator
from interviews.models import Interview


class LightingStatus(models.TextChoices):
    TOO_DARK = 'too_dark', 'Insufficient Lighting (Too Dark)'
    GOOD = 'good', 'Optimal Studio Lighting'
    TOO_BRIGHT = 'too_bright', 'Overexposed / Backlit'


class PostureEventType(models.TextChoices):
    SLOUCHING = 'slouching', 'Slouching / Forward Head Posture'
    HEAD_DOWN = 'head_down', 'Head Tilted Downward'
    LOOKING_AWAY = 'looking_away', 'Gaze Shifted Off-Screen'
    OUT_OF_FRAME = 'out_of_frame', 'Candidate Out of Frame'
    LEANING = 'leaning', 'Excessive Leaning'
    RAPID_FIDGETING = 'fidgeting', 'Restless / Rapid Movement'


class PostureSeverity(models.TextChoices):
    LOW = 'low', 'Subtle / Minor'
    MEDIUM = 'medium', 'Noticeable'
    HIGH = 'high', 'Persistent / Significant'


class EnvironmentCheck(models.Model):
    """
    Results of the pre-interview Tech Check Wizard.
    Ensures optimal lighting, audio levels, and phone/clutter detection.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    interview = models.OneToOneField(Interview, on_delete=models.CASCADE, related_name='environment_check')
    camera_ok = models.BooleanField(default=False)
    mic_ok = models.BooleanField(default=False)
    luminance_score = models.FloatField(
        default=0.0, 
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)]
    )
    lighting_status = models.CharField(
        max_length=20, 
        choices=LightingStatus.choices, 
        default=LightingStatus.GOOD
    )
    audio_level_rms = models.FloatField(default=0.0, help_text="Measured microphone RMS volume during sound check.")
    background_clutter_detected = models.BooleanField(default=False)
    phone_detected = models.BooleanField(default=False)
    readiness_score = models.FloatField(
        default=0.0, 
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)]
    )
    suggestions = models.JSONField(
        default=list, 
        blank=True, 
        help_text="Actionable suggestions (e.g., 'Increase frontal lighting', 'Adjust camera to eye level')."
    )
    checked_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Tech Check for {self.interview.id} (Readiness: {self.readiness_score}%)"


class PostureEvent(models.Model):
    """
    Temporal events detected by MediaPipe browser vision models.
    Zero video upload: Only timestamps, event categories, and severity are transmitted.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    interview = models.ForeignKey(Interview, on_delete=models.CASCADE, related_name='posture_events')
    event_type = models.CharField(max_length=32, choices=PostureEventType.choices)
    severity = models.CharField(
        max_length=16, 
        choices=PostureSeverity.choices, 
        default=PostureSeverity.LOW
    )
    start_offset_ms = models.PositiveIntegerField(help_text="Milliseconds from interview session start.")
    end_offset_ms = models.PositiveIntegerField(null=True, blank=True)
    details = models.JSONField(
        default=dict, 
        blank=True, 
        help_text="Numeric telemetry (e.g., pitch/yaw delta degrees, shoulder tilt ratio)."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['interview', 'start_offset_ms']
        indexes = [
            models.Index(fields=['interview', 'start_offset_ms']),
            models.Index(fields=['event_type']),
        ]

    def __str__(self):
        return f"[{self.start_offset_ms}ms] {self.get_event_type_display()} ({self.severity})"


class SpeechMetrics(models.Model):
    """
    Client-side computed speech analytics parsed from Web Speech API and Web Audio AnalyserNode.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    interview = models.OneToOneField(Interview, on_delete=models.CASCADE, related_name='speech_metrics')
    words_per_minute = models.FloatField(default=0.0)
    total_words = models.PositiveIntegerField(default=0)
    filler_words_count = models.PositiveIntegerField(default=0)
    filler_words_breakdown = models.JSONField(
        default=dict, 
        blank=True, 
        help_text="Dictionary of counts: e.g. {'um': 3, 'uh': 2, 'like': 6, 'you know': 1}"
    )
    pause_count = models.PositiveIntegerField(default=0)
    average_pause_duration_ms = models.FloatField(default=0.0)
    average_loudness_rms = models.FloatField(default=0.0)
    computed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Speech Metrics for {self.interview.id} ({self.words_per_minute:.1f} WPM, {self.filler_words_count} fillers)"


class Report(models.Model):
    """
    Comprehensive Post-Interview Evaluation Report.
    Combines technical accuracy, STAR behavioral breakdown, CV body language, and speech clarity.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    interview = models.OneToOneField(Interview, on_delete=models.CASCADE, related_name='report')
    
    # Composite & breakdown scores (0 - 100)
    overall_score = models.FloatField(
        default=0.0, 
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)]
    )
    technical_score = models.FloatField(
        default=0.0, 
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)]
    )
    posture_score = models.FloatField(
        default=0.0, 
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)]
    )
    eye_contact_score = models.FloatField(
        default=0.0, 
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)]
    )
    speech_clarity_score = models.FloatField(
        default=0.0, 
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)]
    )

    summary = models.TextField(blank=True, default='')
    strengths = models.JSONField(default=list, blank=True)
    improvements = models.JSONField(default=list, blank=True)
    behavioral_star_feedback = models.JSONField(
        default=dict, 
        blank=True, 
        help_text="Detailed STAR method analysis (Situation, Task, Action, Result)."
    )
    timeline_events = models.JSONField(
        default=list, 
        blank=True, 
        help_text="Chronological timeline of occurrences (e.g. posture slips, filler spikes)."
    )
    pdf_path = models.CharField(max_length=512, blank=True, null=True)
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-generated_at']

    def delete(self, *args, **kwargs):
        """Zero-Data Guarantee: Purges any generated PDF file on disk upon report deletion."""
        if self.pdf_path and os.path.isfile(self.pdf_path):
            try:
                os.remove(self.pdf_path)
            except OSError:
                pass
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"Report for {self.interview.title} (Overall: {self.overall_score}%)"


@receiver(post_delete, sender=Report)
def purge_report_pdf_file_on_delete(sender, instance, **kwargs):
    """Zero-Data Guarantee: Purges any generated PDF file on disk upon cascading or direct report deletion."""
    if instance.pdf_path and os.path.isfile(instance.pdf_path):
        try:
            os.remove(instance.pdf_path)
        except OSError:
            pass

