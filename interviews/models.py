import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator


class InterviewDomain(models.TextChoices):
    FRONTEND = 'frontend', 'Frontend Engineering'
    BACKEND = 'backend', 'Backend Engineering'
    FULLSTACK = 'fullstack', 'Full-Stack Engineering'
    SYSTEM_DESIGN = 'system_design', 'System Design & Architecture'
    DEVOPS = 'devops', 'DevOps & Cloud Engineering'
    DATA_AI = 'data_ai', 'Data Science & Machine Learning'
    BEHAVIORAL = 'behavioral', 'Behavioral & Leadership (STAR)'


class InterviewDifficulty(models.TextChoices):
    ENTRY = 'entry', 'Entry Level / Junior'
    MID = 'mid', 'Mid-Level'
    SENIOR = 'senior', 'Senior Engineer'
    STAFF = 'staff', 'Staff / Principal Architect'


class InterviewPersona(models.TextChoices):
    FRIENDLY = 'friendly', 'Friendly & Supportive Mentor'
    TECHNICAL_LEAD = 'tech_lead', 'Analytical Technical Lead'
    FAANG_BAR_RAISER = 'bar_raiser', 'FAANG Bar Raiser (Rigorous)'
    HR_BEHAVIORAL = 'hr_manager', 'HR / Executive Recruiter'


class InterviewMode(models.TextChoices):
    STANDARD = 'standard', 'Standard Evaluated Mode'
    ANXIETY_FREE = 'anxiety_free', 'Anxiety-Free Practice Mode (No Scoring)'


class InterviewStatus(models.TextChoices):
    PENDING_SETUP = 'pending_setup', 'Pending Tech Check'
    IN_PROGRESS = 'in_progress', 'In Progress'
    COMPLETED = 'completed', 'Completed'
    ABANDONED = 'abandoned', 'Abandoned'


class QuestionCategory(models.TextChoices):
    TECHNICAL = 'technical', 'Technical Depth'
    BEHAVIORAL = 'behavioral', 'Behavioral / STAR'
    SYSTEM_DESIGN = 'system_design', 'System Architecture'
    PROBLEM_SOLVING = 'problem_solving', 'Live Problem Solving'
    FOLLOW_UP = 'follow_up', 'Adaptive Follow-Up'


class AnswerInputMethod(models.TextChoices):
    SPOKEN = 'spoken', 'Web Speech API (STT)'
    TYPED = 'typed', 'Typed Fallback'


class Interview(models.Model):
    """
    Core Interview Session.
    Uses UUID primary key for zero-enumeration IDOR defense.
    All CV/video runs client-side; only metadata, baseline, and scores are stored.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='interviews')
    title = models.CharField(max_length=200, blank=True)
    domain = models.CharField(
        max_length=32, 
        choices=InterviewDomain.choices, 
        default=InterviewDomain.FULLSTACK
    )
    difficulty = models.CharField(
        max_length=16, 
        choices=InterviewDifficulty.choices, 
        default=InterviewDifficulty.MID
    )
    persona = models.CharField(
        max_length=20, 
        choices=InterviewPersona.choices, 
        default=InterviewPersona.TECHNICAL_LEAD
    )
    mode = models.CharField(
        max_length=20, 
        choices=InterviewMode.choices, 
        default=InterviewMode.STANDARD
    )
    status = models.CharField(
        max_length=20, 
        choices=InterviewStatus.choices, 
        default=InterviewStatus.PENDING_SETUP
    )
    
    # Optional candidate personalization
    job_description = models.TextField(blank=True, default='')
    resume_text = models.TextField(blank=True, default='')

    # Baseline posture & head-pose coordinates captured during 10-sec calibration
    calibration_baseline = models.JSONField(
        default=dict, 
        blank=True, 
        help_text="Stores neutral posture reference points (shoulder tilt, nose/ear distance, gaze origin)."
    )

    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['domain', 'difficulty']),
        ]

    def save(self, *args, **kwargs):
        if not self.title:
            self.title = f"{self.get_domain_display()} ({self.get_difficulty_display()})"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} - {self.user.username} [{self.get_status_display()}]"


class Question(models.Model):
    """
    Interview question instances presented to the candidate.
    Supports linear progression and dynamic AI follow-up trees.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    interview = models.ForeignKey(Interview, on_delete=models.CASCADE, related_name='questions')
    order = models.PositiveSmallIntegerField(default=1)
    question_text = models.TextField()
    category = models.CharField(
        max_length=32, 
        choices=QuestionCategory.choices, 
        default=QuestionCategory.TECHNICAL
    )
    is_follow_up = models.BooleanField(default=False)
    parent_question = models.ForeignKey(
        'self', 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL, 
        related_name='follow_ups'
    )
    expected_key_points = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['interview', 'order']
        constraints = [
            models.UniqueConstraint(
                fields=['interview', 'order'], 
                name='unique_question_order_per_interview'
            )
        ]
        indexes = [
            models.Index(fields=['interview', 'order']),
        ]

    def __str__(self):
        return f"Q{self.order} ({self.get_category_display()}): {self.question_text[:50]}..."


class Answer(models.Model):
    """
    Candidate's submitted response to a question.
    Transcribed client-side via Web Speech API or typed fallback.
    Never stores audio files; only transcript text and AI scoring.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.OneToOneField(Question, on_delete=models.CASCADE, related_name='answer')
    transcript_text = models.TextField(blank=True, default='')
    input_method = models.CharField(
        max_length=16, 
        choices=AnswerInputMethod.choices, 
        default=AnswerInputMethod.SPOKEN
    )
    duration_seconds = models.FloatField(default=0.0)
    
    # Evaluated AI metrics (clamped 0.0 - 100.0)
    ai_score = models.FloatField(
        null=True, 
        blank=True, 
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)]
    )
    # Structured JSON feedback: {strengths: [], improvements: [], star_framework: {}, score_breakdown: {}}
    ai_feedback = models.JSONField(default=dict, blank=True)
    evaluated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Answer to Q{self.question.order} (Score: {self.ai_score or 'Pending'})"
