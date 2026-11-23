import json
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from interviews.models import Interview, InterviewStatus
from analytics.models import (
    EnvironmentCheck, 
    PostureEvent, 
    SpeechMetrics, 
    Report, 
    PostureEventType, 
    PostureSeverity, 
    LightingStatus
)


class AnalyticsModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='analyticsuser', 
            email='user@example.com', 
            password='ComplexPassword123!'
        )
        self.interview = Interview.objects.create(user=self.user)

    def test_analytics_models_creation(self):
        env_check = EnvironmentCheck.objects.create(
            interview=self.interview,
            camera_ok=True,
            mic_ok=True,
            luminance_score=82.0,
            readiness_score=95.0
        )
        self.assertEqual(env_check.readiness_score, 95.0)

        posture_event = PostureEvent.objects.create(
            interview=self.interview,
            event_type=PostureEventType.SLOUCHING,
            severity=PostureSeverity.MEDIUM,
            start_offset_ms=12400,
            end_offset_ms=16800
        )
        self.assertEqual(posture_event.start_offset_ms, 12400)

        speech = SpeechMetrics.objects.create(
            interview=self.interview,
            words_per_minute=135.0,
            total_words=420,
            filler_words_count=4
        )
        self.assertEqual(speech.filler_words_count, 4)

        report = Report.objects.create(
            interview=self.interview,
            overall_score=86.0,
            technical_score=88.0,
            posture_score=85.0
        )
        self.assertEqual(report.overall_score, 86.0)


class TechCheckEndpointTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.candidate = User.objects.create_user(
            username='candidate_tech', 
            password='Password123!'
        )
        self.other_candidate = User.objects.create_user(
            username='other_candidate', 
            password='Password123!'
        )
        self.interview = Interview.objects.create(
            user=self.candidate,
            title="Frontend Senior Loop",
            status=InterviewStatus.PENDING_SETUP
        )
        self.url = reverse('save_tech_check', kwargs={'interview_id': self.interview.id})

    def test_save_tech_check_success(self):
        self.client.force_login(self.candidate)
        payload = {
            'camera_ok': True,
            'mic_ok': True,
            'luminance_score': 68.5,
            'lighting_status': 'good',
            'audio_level_rms': 22.4,
            'background_clutter_detected': False,
            'phone_detected': False,
            'readiness_score': 90.0,
            'suggestions': ["Environment is optimal! You are ready."]
        }

        response = self.client.post(
            self.url, 
            data=json.dumps(payload), 
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['readiness_score'], 90.0)
        self.assertEqual(data['interview_status'], InterviewStatus.IN_PROGRESS)

        # Check database record
        env_check = EnvironmentCheck.objects.get(interview=self.interview)
        self.assertTrue(env_check.camera_ok)
        self.assertTrue(env_check.mic_ok)
        self.assertEqual(env_check.luminance_score, 68.5)
        self.assertEqual(env_check.readiness_score, 90.0)

        # Interview transitioned to IN_PROGRESS
        self.interview.refresh_from_db()
        self.assertEqual(self.interview.status, InterviewStatus.IN_PROGRESS)

    def test_save_tech_check_clamps_untrusted_metrics(self):
        self.client.force_login(self.candidate)
        payload = {
            'camera_ok': True,
            'mic_ok': True,
            'luminance_score': 250.0,   # > 100
            'lighting_status': 'unknown_status', # Invalid choice fallback
            'audio_level_rms': -50.0,   # < 0
            'readiness_score': 180.0,   # > 100
            'suggestions': ["Test suggestion"]
        }

        response = self.client.post(
            self.url, 
            data=json.dumps(payload), 
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)

        env_check = EnvironmentCheck.objects.get(interview=self.interview)
        self.assertEqual(env_check.luminance_score, 100.0)
        self.assertEqual(env_check.audio_level_rms, 0.0)
        self.assertEqual(env_check.readiness_score, 100.0)
        self.assertEqual(env_check.lighting_status, LightingStatus.GOOD)

    def test_save_tech_check_idor_protection(self):
        """Candidate B cannot modify Candidate A's tech check record (must return 404)."""
        self.client.force_login(self.other_candidate)
        payload = {
            'camera_ok': True,
            'mic_ok': True,
            'readiness_score': 90.0
        }
        response = self.client.post(
            self.url, 
            data=json.dumps(payload), 
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(EnvironmentCheck.objects.filter(interview=self.interview).exists())

    def test_save_tech_check_requires_login(self):
        payload = {'camera_ok': True}
        response = self.client.post(
            self.url, 
            data=json.dumps(payload), 
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    def test_save_tech_check_rejects_malformed_json(self):
        self.client.force_login(self.candidate)
        response = self.client.post(
            self.url, 
            data="not a json payload", 
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json()['status'])


class CalibrationAndPostureTelemetryTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user_a = User.objects.create_user(username='cand_a', password='Password123!')
        self.user_b = User.objects.create_user(username='cand_b', password='Password123!')

        self.interview = Interview.objects.create(
            user=self.user_a,
            title="Computer Vision Calibration Loop"
        )
        self.calib_url = reverse('save_calibration', kwargs={'interview_id': self.interview.id})
        self.telem_url = reverse('save_posture_telemetry', kwargs={'interview_id': self.interview.id})

    def test_save_baseline_calibration_success_and_clamping(self):
        self.client.force_login(self.user_a)
        payload = {
            'face_center_x': 0.4821,
            'face_center_y': 0.4125,
            'face_scale': 0.195,
            'shoulder_tilt': 0.012,
            'gaze_origin_x': 0.490,
            'gaze_origin_y': 0.380,
            'calibrated_samples': 85
        }
        resp = self.client.post(self.calib_url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['baseline']['calibrated_samples'], 85)

        self.interview.refresh_from_db()
        self.assertEqual(self.interview.calibration_baseline['face_center_x'], 0.4821)
        self.assertEqual(self.interview.calibration_baseline['face_center_y'], 0.4125)

    def test_save_baseline_calibration_idor_protection(self):
        # User B cannot save calibration on User A's session
        self.client.force_login(self.user_b)
        payload = {'face_center_x': 0.5}
        resp = self.client.post(self.calib_url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(resp.status_code, 404)

    def test_save_posture_telemetry_batch_success(self):
        self.client.force_login(self.user_a)
        payload = {
            'events': [
                {
                    'event_type': 'slouching',
                    'severity': 'medium',
                    'start_offset_ms': 5400,
                    'end_offset_ms': 8200,
                    'details': {'delta_y': 0.16}
                },
                {
                    'event_type': 'looking_away',
                    'severity': 'low',
                    'start_offset_ms': 12000,
                    'end_offset_ms': 14500,
                    'details': {'delta_x': 0.22}
                },
                {
                    'event_type': 'leaning',
                    'severity': 'low',
                    'start_offset_ms': 20000,
                    'end_offset_ms': 22500,
                    'details': {'delta_x': 0.18}
                }
            ]
        }
        resp = self.client.post(self.telem_url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['saved_count'], 3)

        # Verify database records
        events = PostureEvent.objects.filter(interview=self.interview)
        self.assertEqual(events.count(), 3)
        slouch_ev = events.filter(event_type='slouching').first()
        self.assertIsNotNone(slouch_ev)
        self.assertEqual(slouch_ev.severity, 'medium')
        self.assertEqual(slouch_ev.start_offset_ms, 5400)

    def test_save_posture_telemetry_batch_idor_protection(self):
        # User B cannot inject posture telemetry into User A's session
        self.client.force_login(self.user_b)
        payload = {
            'events': [{'event_type': 'slouching', 'start_offset_ms': 1000}]
        }
        resp = self.client.post(self.telem_url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(resp.status_code, 404)
        self.assertFalse(PostureEvent.objects.filter(interview=self.interview).exists())


# -----------------------------------------------------------------------------
# Phase 7: Multimodal Scoring & PDF Report Generation Tests
# -----------------------------------------------------------------------------
class MultimodalScoringUnitTests(TestCase):
    def setUp(self):
        from interviews.models import Question, Answer
        self.user = User.objects.create_user(username='scoring_user', password='Password123!')
        self.interview = Interview.objects.create(
            user=self.user,
            title="System Design Architecture Loop"
        )

        # Create sample questions and answers
        self.q1 = Question.objects.create(
            interview=self.interview,
            order=1,
            question_text="Design a distributed cache system with TTL eviction."
        )
        self.a1 = Answer.objects.create(
            question=self.q1,
            transcript_text="I would use Redis with consistent hashing and an LRU eviction policy. Like, you know, we want to minimize hot-key contention.",
            duration_seconds=45.0,
            ai_score=85.0,
            ai_feedback={
                "summary": "Solid architectural foundation.",
                "strengths": ["Clear consistent hashing choice", "Addressed cache stampede"],
                "improvements": ["Elaborate on write-through vs write-back"],
                "star_framework": {"situation": 85, "task": 82, "action": 88, "result": 80}
            }
        )

        self.q2 = Question.objects.create(
            interview=self.interview,
            order=2,
            question_text="How do you handle database failover in production?"
        )
        self.a2 = Answer.objects.create(
            question=self.q2,
            transcript_text="We configure active-passive replication with automated sentinel failover and read replicas. Um, actually, we observed zero data loss.",
            duration_seconds=50.0,
            ai_score=90.0,
            ai_feedback={
                "summary": "Great high-availability explanation.",
                "strengths": ["Mentioned sentinel heartbeats", "Split-brain defense"],
                "improvements": ["Explain replication lag mitigation"],
                "star_framework": {"situation": 90, "task": 85, "action": 92, "result": 85}
            }
        )

    def test_calculate_technical_score(self):
        from analytics.scoring import calculate_technical_score
        tech_data = calculate_technical_score(self.interview)
        self.assertEqual(tech_data['count'], 2)
        # (85.0 + 90.0) / 2 = 87.5
        self.assertEqual(tech_data['score'], 87.5)
        self.assertEqual(len(tech_data['details']), 2)

    def test_calculate_posture_and_gaze_scores_no_events(self):
        from analytics.scoring import calculate_posture_and_gaze_scores
        cv_data = calculate_posture_and_gaze_scores(self.interview)
        self.assertGreaterEqual(cv_data['posture_score'], 95.0)
        self.assertGreaterEqual(cv_data['eye_contact_score'], 95.0)
        self.assertEqual(cv_data['total_events'], 0)

    def test_calculate_posture_and_gaze_scores_with_penalties(self):
        from analytics.scoring import calculate_posture_and_gaze_scores
        # Add posture slips
        PostureEvent.objects.create(
            interview=self.interview,
            event_type=PostureEventType.SLOUCHING,
            severity=PostureSeverity.MEDIUM, # 5.5 penalty
            start_offset_ms=10000
        )
        PostureEvent.objects.create(
            interview=self.interview,
            event_type=PostureEventType.LOOKING_AWAY,
            severity=PostureSeverity.HIGH, # 11.0 * 1.2 = 13.2 gaze penalty
            start_offset_ms=25000
        )
        cv_data = calculate_posture_and_gaze_scores(self.interview)
        self.assertEqual(cv_data['total_events'], 2)
        self.assertLess(cv_data['posture_score'], 96.0)
        self.assertLess(cv_data['eye_contact_score'], 90.0)

    def test_calculate_speech_metrics_and_fillers(self):
        from analytics.scoring import calculate_speech_metrics
        speech_data = calculate_speech_metrics(self.interview)
        self.assertGreater(speech_data['total_words'], 20)
        self.assertGreater(speech_data['words_per_minute'], 0)
        # Transcripts contained "like", "you know", "um", "actually"
        self.assertGreater(speech_data['total_fillers'], 0)
        self.assertIn('like', speech_data['filler_counts'])
        
        # Verify SpeechMetrics model in DB
        metrics = SpeechMetrics.objects.get(interview=self.interview)
        self.assertEqual(metrics.total_words, speech_data['total_words'])
        self.assertEqual(metrics.filler_words_count, speech_data['total_fillers'])

    def test_calculate_star_breakdown(self):
        from analytics.scoring import calculate_star_breakdown
        star = calculate_star_breakdown(self.interview)
        self.assertGreaterEqual(star['composite_star_score'], 80.0)
        self.assertIn('situation', star)
        self.assertIn('task', star)
        self.assertIn('action', star)
        self.assertIn('result', star)
        self.assertGreaterEqual(len(star['strengths']), 1)

    def test_generate_comprehensive_report_composite_weighting(self):
        from analytics.scoring import generate_comprehensive_report
        report = generate_comprehensive_report(self.interview)
        
        self.assertIsNotNone(report)
        self.assertEqual(report.technical_score, 87.5)
        self.assertGreaterEqual(report.posture_score, 30.0)
        self.assertGreaterEqual(report.eye_contact_score, 30.0)
        self.assertGreaterEqual(report.speech_clarity_score, 30.0)

        # Check composite formula: tech*0.4 + posture*0.2 + eye*0.2 + speech*0.2
        expected_overall = round(
            (report.technical_score * 0.40) + 
            (report.posture_score * 0.20) + 
            (report.eye_contact_score * 0.20) + 
            (report.speech_clarity_score * 0.20),
            1
        )
        self.assertEqual(report.overall_score, expected_overall)
        self.assertTrue(len(report.summary) > 20)
        self.assertGreaterEqual(len(report.timeline_events), 2)


class ReportAndPdfEndpointTests(TestCase):
    def setUp(self):
        from interviews.models import Question, Answer
        self.client = Client()
        self.user = User.objects.create_user(username='pdf_user', password='Password123!', email='pdf@example.com')
        self.other_user = User.objects.create_user(username='other_pdf_user', password='Password123!')

        self.interview = Interview.objects.create(
            user=self.user,
            title="Backend Staff Distributed Systems",
            status=InterviewStatus.COMPLETED
        )

        q = Question.objects.create(interview=self.interview, order=1, question_text="Explain Raft consensus.")
        Answer.objects.create(
            question=q, 
            transcript_text="Raft uses leader election, log replication, and safety guarantees.",
            duration_seconds=30.0,
            ai_score=92.0,
            ai_feedback={"summary": "Great consensus explanation.", "strengths": ["Clear leader election"]}
        )

        self.report_url = reverse('interview_report', kwargs={'interview_id': self.interview.id})
        self.pdf_url = reverse('interview_report_pdf', kwargs={'interview_id': self.interview.id})

    def test_interview_report_view_success(self):
        self.client.force_login(self.user)
        resp = self.client.get(self.report_url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Backend Staff Distributed Systems")
        self.assertContains(resp, "Composite Rating")
        self.assertContains(resp, "STAR Behavioral Competency Breakdown")
        self.assertContains(resp, "reportRadarChart")

    def test_interview_report_view_idor_protection(self):
        self.client.force_login(self.other_user)
        resp = self.client.get(self.report_url)
        self.assertEqual(resp.status_code, 404)

    def test_interview_report_view_requires_login(self):
        resp = self.client.get(self.report_url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('login'), resp.url)

    def test_interview_report_pdf_download_success(self):
        self.client.force_login(self.user)
        resp = self.client.get(self.pdf_url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')
        self.assertIn('attachment;', resp['Content-Disposition'])
        self.assertIn('.pdf', resp['Content-Disposition'])

        # Validate that the response stream is a valid PDF file (begins with %PDF-)
        content = b"".join(resp.streaming_content)
        self.assertTrue(content.startswith(b'%PDF-'))
        self.assertGreater(len(content), 1000)

    def test_interview_report_pdf_idor_protection(self):
        self.client.force_login(self.other_user)
        resp = self.client.get(self.pdf_url)
        self.assertEqual(resp.status_code, 404)

    def test_direct_pdf_generator_function(self):
        from analytics.reports import generate_pdf_report
        import io
        buf = generate_pdf_report(self.interview)
        self.assertIsInstance(buf, io.BytesIO)
        pdf_bytes = buf.getvalue()
        self.assertTrue(pdf_bytes.startswith(b'%PDF-'))
        self.assertGreater(len(pdf_bytes), 2000)

