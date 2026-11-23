import uuid
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from interviews.models import (
    Interview, 
    Question, 
    Answer, 
    InterviewDomain, 
    InterviewDifficulty,
    InterviewPersona,
    InterviewMode,
    InterviewStatus
)
from analytics.models import Report

class InterviewModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='candidatetest', 
            email='candidate@example.com', 
            password='ComplexPassword123!'
        )

    def test_create_interview_with_uuid_and_question_order(self):
        interview = Interview.objects.create(
            user=self.user,
            domain=InterviewDomain.FULLSTACK,
            difficulty=InterviewDifficulty.SENIOR,
        )
        self.assertIsInstance(interview.id, uuid.UUID)
        self.assertIn("Full-Stack Engineering", interview.title)

        q1 = Question.objects.create(
            interview=interview,
            order=1,
            question_text="Explain database connection pooling."
        )
        self.assertIsInstance(q1.id, uuid.UUID)

        answer = Answer.objects.create(
            question=q1,
            transcript_text="Connection pooling keeps active DB connections open to minimize handshake overhead.",
            ai_score=88.5
        )
        self.assertEqual(answer.ai_score, 88.5)


class DashboardAndIDORTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user_a = User.objects.create_user(username='user_a', password='Password123!')
        self.user_b = User.objects.create_user(username='user_b', password='Password123!')

        self.interview_a = Interview.objects.create(
            user=self.user_a,
            title="User A Full-Stack Practice",
            domain=InterviewDomain.FULLSTACK,
            difficulty=InterviewDifficulty.SENIOR,
            status=InterviewStatus.COMPLETED
        )
        Report.objects.create(
            interview=self.interview_a,
            overall_score=89.5,
            technical_score=92.0,
            posture_score=86.0
        )

        self.interview_b = Interview.objects.create(
            user=self.user_b,
            title="User B System Design Interview",
            domain=InterviewDomain.SYSTEM_DESIGN,
            difficulty=InterviewDifficulty.STAFF
        )

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    def test_dashboard_renders_for_logged_in_candidate(self):
        self.client.force_login(self.user_a)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'interviews/dashboard.html')
        self.assertContains(response, 'User A Full-Stack Practice')
        self.assertContains(response, '89.5%')
        self.assertContains(response, 'radarChart')
        self.assertContains(response, 'data-open-modal="new-interview-modal"')
        self.assertContains(response, 'id="new-interview-modal"')
        self.assertContains(response, 'modal-overlay')
        self.assertContains(response, 'data-close-modal="new-interview-modal"')

    def test_dashboard_idor_isolation(self):
        """User A must NOT see User B's interview sessions on their dashboard."""
        self.client.force_login(self.user_a)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'User A Full-Stack Practice')
        self.assertNotContains(response, 'User B System Design Interview')

    def test_create_interview_session_via_post(self):
        self.client.force_login(self.user_a)
        response = self.client.post(reverse('create_interview'), {
            'domain': 'system_design',
            'difficulty': 'senior',
            'persona': 'bar_raiser',
            'mode': 'standard',
            'job_description': 'Lead Distributed Systems Architect role at Stripe.',
            'resume_text': 'Designed Kafka pipeline processing 10M events/sec.',
        }, follow=False)

        self.assertEqual(response.status_code, 302)
        new_interview = Interview.objects.filter(
            user=self.user_a, 
            domain='system_design', 
            persona='bar_raiser'
        ).first()
        self.assertIsNotNone(new_interview)
        self.assertIn(str(new_interview.id), response.url)

    def test_interview_room_shell_idor_protection(self):
        """User B cannot enter or inspect User A's interview room (must return 404)."""
        self.client.force_login(self.user_b)
        response = self.client.get(reverse('interview_room', kwargs={'interview_id': self.interview_a.id}))
        self.assertEqual(response.status_code, 404)

        # But User A can enter their own room
        self.client.force_login(self.user_a)
        response_owner = self.client.get(reverse('interview_room', kwargs={'interview_id': self.interview_a.id}))
        self.assertEqual(response_owner.status_code, 200)
        self.assertTemplateUsed(response_owner, 'interviews/room_shell.html')

    def test_delete_interview_idor_protection(self):
        """User B cannot delete User A's interview session (must return 404)."""
        self.client.force_login(self.user_b)
        response = self.client.post(reverse('delete_interview', kwargs={'interview_id': self.interview_a.id}))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Interview.objects.filter(id=self.interview_a.id).exists())

        # User A can delete their own interview
        self.client.force_login(self.user_a)
        response_owner = self.client.post(reverse('delete_interview', kwargs={'interview_id': self.interview_a.id}), follow=True)
        self.assertEqual(response_owner.status_code, 200)
        self.assertFalse(Interview.objects.filter(id=self.interview_a.id).exists())

    def test_interview_state_api_idor_and_structure(self):
        # User B cannot access User A's interview state
        self.client.force_login(self.user_b)
        resp_b = self.client.get(reverse('interview_state_api', kwargs={'interview_id': self.interview_a.id}))
        self.assertEqual(resp_b.status_code, 404)

        # User A accesses state successfully
        self.client.force_login(self.user_a)
        resp_a = self.client.get(reverse('interview_state_api', kwargs={'interview_id': self.interview_a.id}))
        self.assertEqual(resp_a.status_code, 200)
        data = resp_a.json()
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['interview']['title'], self.interview_a.title)

    def test_start_interview_api_generates_questions_and_sets_in_progress(self):
        interview = Interview.objects.create(
            user=self.user_a,
            domain=InterviewDomain.BACKEND,
            difficulty=InterviewDifficulty.SENIOR,
            persona=InterviewPersona.TECHNICAL_LEAD
        )

        self.client.force_login(self.user_a)
        resp = self.client.post(reverse('start_interview_api', kwargs={'interview_id': interview.id}))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['status'], 'ok')
        self.assertIn('question', data)
        self.assertEqual(data['question']['order'], 1)

        interview.refresh_from_db()
        self.assertEqual(interview.status, InterviewStatus.IN_PROGRESS)
        self.assertEqual(interview.questions.count(), 5)

    def test_submit_answer_api_evaluates_and_persists(self):
        interview = Interview.objects.create(
            user=self.user_a,
            domain=InterviewDomain.FULLSTACK,
            difficulty=InterviewDifficulty.MID
        )
        self.client.force_login(self.user_a)
        start_resp = self.client.post(reverse('start_interview_api', kwargs={'interview_id': interview.id}))
        first_q = start_resp.json()['question']

        # User B cannot submit answer for User A's question
        self.client.force_login(self.user_b)
        idor_resp = self.client.post(
            reverse('submit_answer_api', kwargs={'interview_id': interview.id}),
            data={'question_id': first_q['id'], 'transcript_text': 'IDOR attack response'},
            content_type='application/json'
        )
        self.assertEqual(idor_resp.status_code, 404)

        # User A submits answer
        self.client.force_login(self.user_a)
        ans_resp = self.client.post(
            reverse('submit_answer_api', kwargs={'interview_id': interview.id}),
            data={
                'question_id': first_q['id'],
                'transcript_text': 'I implement database connection pooling using HikariCP with max pool size 20 to reduce SSL handshake overhead.',
                'duration_seconds': 42.5,
                'input_method': 'spoken'
            },
            content_type='application/json'
        )
        self.assertEqual(ans_resp.status_code, 200)
        ans_data = ans_resp.json()
        self.assertEqual(ans_data['status'], 'ok')
        self.assertTrue(0.0 <= ans_data['score'] <= 100.0)

        # Verify Answer record in PostgreSQL
        answer_record = Answer.objects.get(question_id=first_q['id'])
        self.assertEqual(answer_record.duration_seconds, 42.5)
        self.assertEqual(answer_record.input_method, 'spoken')
        self.assertIsNotNone(answer_record.ai_score)
        self.assertIn('strengths', answer_record.ai_feedback)
