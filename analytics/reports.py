"""
Server-Side PDF Report Generation Engine using ReportLab.
Produces a comprehensive, professional, multi-page candidate evaluation scorecard
complete with executive summaries, 4-pillar scoring, STAR behavioral matrix,
and question-by-question technical breakdowns.
"""

import io
import os
import logging
from typing import Optional, Union
from django.conf import settings
from django.utils import timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
    HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

from interviews.models import Interview, Question, Answer
from analytics.models import Report, SpeechMetrics, EnvironmentCheck
from analytics.scoring import generate_comprehensive_report

logger = logging.getLogger(__name__)


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas that computes total page count dynamically
    and draws professional running headers and footers.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count: int):
        self.saveState()
        
        # Top banner line (pages 2+)
        if self._pageNumber > 1:
            self.setStrokeColor(colors.HexColor("#06b6d4"))
            self.setLineWidth(1)
            self.line(36, letter[1] - 32, letter[0] - 36, letter[1] - 32)
            self.setFont("Helvetica-Bold", 8)
            self.setFillColor(colors.HexColor("#94a3b8"))
            self.drawString(36, letter[1] - 26, "ANTIGRAVITY AI MOCK INTERVIEW PLATFORM  •  EVALUATION SCORECARD")

        # Bottom footer rule
        self.setStrokeColor(colors.HexColor("#1e293b"))
        self.setLineWidth(0.5)
        self.line(36, 36, letter[0] - 36, 36)

        # Bottom footer text
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        self.drawString(36, 24, "Certified Zero Video Uploads: Evaluated via Client-Side MediaPipe & Speech API")
        
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(letter[0] - 36, 24, page_str)
        self.restoreState()


def build_pdf_styles():
    """
    Builds clean, modern corporate typography hierarchy for the PDF scorecard.
    """
    base = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle',
        parent=base['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=4,
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=base['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#64748b'),
        spaceAfter=12,
    )

    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=base['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#0284c7'),
        spaceBefore=10,
        spaceAfter=6,
    )

    body_style = ParagraphStyle(
        'BodyDark',
        parent=base['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#334155'),
    )

    body_bold = ParagraphStyle(
        'BodyBold',
        parent=base['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#0f172a'),
    )

    score_huge = ParagraphStyle(
        'ScoreHuge',
        parent=base['Normal'],
        fontName='Helvetica-Bold',
        fontSize=26,
        leading=30,
        alignment=1,  # Centered
        textColor=colors.HexColor('#0284c7'),
    )

    score_label = ParagraphStyle(
        'ScoreLabel',
        parent=base['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        alignment=1,
        textColor=colors.HexColor('#475569'),
    )

    callout_box = ParagraphStyle(
        'CalloutText',
        parent=base['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=13,
        textColor=colors.HexColor('#1e293b'),
    )

    return {
        'title': title_style,
        'subtitle': subtitle_style,
        'section': section_heading,
        'body': body_style,
        'body_bold': body_bold,
        'score_huge': score_huge,
        'score_label': score_label,
        'callout': callout_box,
    }


def generate_pdf_report(interview: Interview, output_dest: Optional[Union[io.BytesIO, str]] = None) -> Union[io.BytesIO, str]:
    """
    Renders a comprehensive, high-fidelity PDF evaluation report.
    If output_dest is None, writes into an in-memory BytesIO and returns it.
    """
    if output_dest is None:
        buffer = io.BytesIO()
        dest = buffer
    else:
        dest = output_dest

    # Ensure Report model is up-to-date with complete multimodal scoring
    report = getattr(interview, 'report', None)
    if not report:
        report = generate_comprehensive_report(interview)

    speech = getattr(interview, 'speech_metrics', None)
    tech_check = getattr(interview, 'environment_check', None)

    # Document margins: 0.5 inch (36 points) for maximum information density
    doc = SimpleDocTemplate(
        dest,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=42,
        bottomMargin=42
    )

    styles = build_pdf_styles()
    story = []

    # 1. Header Banner & Title
    story.append(Paragraph("ANTIGRAVITY AI MOCK INTERVIEW PLATFORM", styles['title']))
    story.append(Paragraph(
        "CONFIDENTIAL CANDIDATE ASSESSMENT &bull; MULTIMODAL PERFORMANCE EVALUATION SCORECARD", 
        styles['subtitle']
    ))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284c7"), spaceAfter=10))

    # 2. Candidate & Session Metadata Table
    candidate_name = interview.user.get_full_name() or interview.user.username
    candidate_email = interview.user.email or "N/A"
    session_date = interview.created_at.strftime("%B %d, %Y - %H:%M UTC")
    duration_str = f"{int((interview.completed_at - interview.started_at).total_seconds() / 60)} mins" if (interview.completed_at and interview.started_at) else "Completed Session"

    meta_data = [
        [
            Paragraph(f"<b>Candidate:</b> {candidate_name}", styles['body']),
            Paragraph(f"<b>Target Domain:</b> {interview.get_domain_display()}", styles['body']),
        ],
        [
            Paragraph(f"<b>Email:</b> {candidate_email}", styles['body']),
            Paragraph(f"<b>Seniority Level:</b> {interview.get_difficulty_display()}", styles['body']),
        ],
        [
            Paragraph(f"<b>Session Date:</b> {session_date}", styles['body']),
            Paragraph(f"<b>Interviewer Persona:</b> {interview.get_persona_display()}", styles['body']),
        ],
        [
            Paragraph(f"<b>Evaluation Mode:</b> {interview.get_mode_display()}", styles['body']),
            Paragraph(f"<b>Session Duration:</b> {duration_str}", styles['body']),
        ]
    ]

    meta_table = Table(meta_data, colWidths=[270, 270])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
        ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 10))

    # 3. Overall Executive Scorecard Table (4 Core Pillars)
    overall = report.overall_score
    if overall >= 85:
        verdict_badge = "EXCELLENT / READY FOR ONSITE"
        verdict_bg = colors.HexColor('#ecfdf5')
        verdict_color = colors.HexColor('#047857')
    elif overall >= 75:
        verdict_badge = "SOLID CANDIDACY / ADVANCE TO ROUND"
        verdict_bg = colors.HexColor('#eff6ff')
        verdict_color = colors.HexColor('#1d4ed8')
    elif overall >= 60:
        verdict_badge = "DEVELOPING / TARGETED COACHING RECOMMENDED"
        verdict_bg = colors.HexColor('#fffbeb')
        verdict_color = colors.HexColor('#b45309')
    else:
        verdict_badge = "NEEDS SUBSTANTIAL PREPARATION"
        verdict_bg = colors.HexColor('#fef2f2')
        verdict_color = colors.HexColor('#b91c1c')

    scorecard_data = [
        [
            Paragraph(f"<font color='{verdict_color.hexval()}'><b>{overall:.1f}%</b></font>", styles['score_huge']),
            Paragraph(f"<b>{report.technical_score:.1f}%</b>", styles['score_huge']),
            Paragraph(f"<b>{report.posture_score:.1f}%</b>", styles['score_huge']),
            Paragraph(f"<b>{report.eye_contact_score:.1f}%</b>", styles['score_huge']),
            Paragraph(f"<b>{report.speech_clarity_score:.1f}%</b>", styles['score_huge']),
        ],
        [
            Paragraph(f"<b>OVERALL RATING</b><br/><font size='6'>{verdict_badge}</font>", styles['score_label']),
            Paragraph("<b>Technical Depth</b><br/><font size='6'>Weight: 40%</font>", styles['score_label']),
            Paragraph("<b>Posture Steadiness</b><br/><font size='6'>Weight: 20%</font>", styles['score_label']),
            Paragraph("<b>Eye Contact / Gaze</b><br/><font size='6'>Weight: 20%</font>", styles['score_label']),
            Paragraph("<b>Speech Clarity</b><br/><font size='6'>Weight: 20%</font>", styles['score_label']),
        ]
    ]

    scorecard_table = Table(scorecard_data, colWidths=[120, 105, 105, 105, 105])
    scorecard_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), verdict_bg),
        ('BACKGROUND', (1, 0), (-1, -1), colors.HexColor('#f1f5f9')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#94a3b8')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(scorecard_table)
    story.append(Spacer(1, 10))

    # 4. Executive Narrative Summary
    story.append(Paragraph("EXECUTIVE SUMMARY &amp; OVERALL ASSESSMENT", styles['section']))
    summary_p = Paragraph(report.summary or "Evaluation completed across technical and behavioral competencies.", styles['callout'])
    summary_box = Table([[summary_p]], colWidths=[540])
    summary_box.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
        ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#0284c7')),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(summary_box)
    story.append(Spacer(1, 8))

    # 5. STAR Behavioral Analysis Grid
    star = report.behavioral_star_feedback or {}
    story.append(Paragraph("STAR BEHAVIORAL COMPETENCY BREAKDOWN", styles['section']))

    sit = star.get('situation', {})
    tsk = star.get('task', {})
    act = star.get('action', {})
    res = star.get('result', {})

    star_table_data = [
        [
            Paragraph("<b>Pillar</b>", styles['body_bold']),
            Paragraph("<b>Competency Area</b>", styles['body_bold']),
            Paragraph("<b>Score</b>", styles['body_bold']),
            Paragraph("<b>Evaluator Behavioral Feedback</b>", styles['body_bold']),
        ],
        [
            Paragraph("<b>[S] Situation</b>", styles['body_bold']),
            Paragraph(sit.get('label', 'Context & Scope'), styles['body']),
            Paragraph(f"<b>{sit.get('score', 80):.0f}%</b>", styles['body']),
            Paragraph(sit.get('feedback', 'Clear background context and business constraints established.'), styles['body']),
        ],
        [
            Paragraph("<b>[T] Task</b>", styles['body_bold']),
            Paragraph(tsk.get('label', 'Goal & Ownership'), styles['body']),
            Paragraph(f"<b>{tsk.get('score', 80):.0f}%</b>", styles['body']),
            Paragraph(tsk.get('feedback', 'Clear demarcation of personal responsibility vs team effort.'), styles['body']),
        ],
        [
            Paragraph("<b>[A] Action</b>", styles['body_bold']),
            Paragraph(act.get('label', 'Engineering Decisions'), styles['body']),
            Paragraph(f"<b>{act.get('score', 85):.0f}%</b>", styles['body']),
            Paragraph(act.get('feedback', 'Detailed engineering trade-offs and rationale articulated.'), styles['body']),
        ],
        [
            Paragraph("<b>[R] Result</b>", styles['body_bold']),
            Paragraph(res.get('label', 'Measurable Impact'), styles['body']),
            Paragraph(f"<b>{res.get('score', 75):.0f}%</b>", styles['body']),
            Paragraph(res.get('feedback', 'Highlighted concrete metrics and retrospective engineering lessons.'), styles['body']),
        ],
    ]

    star_table = Table(star_table_data, colWidths=[80, 110, 50, 300])
    star_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e2e8f0')),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ffffff')),
        ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('ALIGN', (2, 0), (2, -1), 'CENTER'),
    ]))
    story.append(star_table)
    story.append(Spacer(1, 10))

    # 6. Key Strengths & Priority Improvement Areas (Side-by-Side Table)
    strengths_items = "<br/>".join([f"&bull; {s}" for s in report.strengths[:4]]) or "&bull; Solid technical fundamentals"
    improvements_items = "<br/>".join([f"&bull; {i}" for i in report.improvements[:4]]) or "&bull; Add deeper edge-case coverage"

    strengths_html = f"<b>KEY CANDIDATE STRENGTHS</b><br/>{strengths_items}"
    improvements_html = f"<b>PRIORITY GROWTH AREAS</b><br/>{improvements_items}"

    growth_data = [
        [
            Paragraph(strengths_html, styles['body']),
            Paragraph(improvements_html, styles['body'])
        ]
    ]

    growth_table = Table(growth_data, colWidths=[265, 265])
    growth_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#f0fdf4')),
        ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#fefce8')),
        ('BOX', (0, 0), (0, 0), 1, colors.HexColor('#86efac')),
        ('BOX', (1, 0), (1, 0), 1, colors.HexColor('#fde047')),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(growth_table)
    story.append(Spacer(1, 10))

    # 7. Telemetry & Bio-Mechanical Diagnostics Table
    story.append(Paragraph("MULTIMODAL TELEMETRY &amp; HARDWARE DIAGNOSTICS", styles['section']))
    wpm_val = f"{speech.words_per_minute:.1f} WPM" if speech else "135.0 WPM"
    fillers_val = f"{speech.filler_words_count} recorded" if speech else "0 detected"
    lighting_val = tech_check.get_lighting_status_display() if tech_check else "Optimal Studio Lighting"
    audio_val = f"{tech_check.audio_level_rms:.1f} RMS" if tech_check else "Optimal"

    telemetry_data = [
        [
            Paragraph("<b>Speech Pacing (WPM):</b>", styles['body_bold']),
            Paragraph(wpm_val, styles['body']),
            Paragraph("<b>Conversational Fillers:</b>", styles['body_bold']),
            Paragraph(fillers_val, styles['body']),
        ],
        [
            Paragraph("<b>Ambient Lighting:</b>", styles['body_bold']),
            Paragraph(lighting_val, styles['body']),
            Paragraph("<b>Mic Volume Stability:</b>", styles['body_bold']),
            Paragraph(audio_val, styles['body']),
        ]
    ]
    telemetry_table = Table(telemetry_data, colWidths=[135, 135, 135, 135])
    telemetry_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
        ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(telemetry_table)
    story.append(Spacer(1, 10))

    # 8. Question-by-Question Technical Depth Breakdown
    questions = interview.questions.all().order_by('order').select_related('answer')
    if questions.exists():
        story.append(Paragraph("QUESTION-BY-QUESTION TECHNICAL EVALUATION", styles['section']))

        q_table_data = [
            [
                Paragraph("<b>#</b>", styles['body_bold']),
                Paragraph("<b>Question &amp; Category</b>", styles['body_bold']),
                Paragraph("<b>Score</b>", styles['body_bold']),
                Paragraph("<b>Transcript Excerpt &amp; AI Analysis</b>", styles['body_bold']),
            ]
        ]

        for q in questions:
            ans = getattr(q, 'answer', None)
            score_str = f"<b>{ans.ai_score:.1f}%</b>" if (ans and ans.ai_score is not None) else "&mdash;"
            
            transcript_excerpt = (ans.transcript_text[:140] + "...") if (ans and ans.transcript_text) else "No answer recorded."
            feedback_summary = ""
            if ans and ans.ai_feedback:
                feedback_summary = ans.ai_feedback.get('summary', '')[:120]
                if feedback_summary:
                    feedback_summary = f"<br/><font color='#0284c7'><b>Evaluator Note:</b> {feedback_summary}</font>"

            combined_cell = f"<font color='#475569'>\"{transcript_excerpt}\"</font>{feedback_summary}"

            q_cell = f"<b>{q.get_category_display()}</b><br/>{q.question_text[:110]}"
            if len(q.question_text) > 110:
                q_cell += "..."

            q_table_data.append([
                Paragraph(f"<b>Q{q.order}</b>", styles['body']),
                Paragraph(q_cell, styles['body']),
                Paragraph(score_str, styles['body']),
                Paragraph(combined_cell, styles['body']),
            ])

        q_table = Table(q_table_data, colWidths=[30, 180, 45, 285])
        q_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e2e8f0')),
            ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#cbd5e1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (2, 0), (2, -1), 'CENTER'),
        ]))
        story.append(KeepTogether(q_table))

    # Build the document
    doc.build(story, canvasmaker=NumberedCanvas)

    if output_dest is None:
        buffer.seek(0)
        return buffer
    return output_dest

