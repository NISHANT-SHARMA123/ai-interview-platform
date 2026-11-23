from unittest.mock import patch
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth.models import User
from accounts.models import UserProfile
from accounts.oauth import get_or_create_candidate_from_google

class UserProfileTests(TestCase):
    def test_user_profile_automatically_created_on_user_save(self):
        user = User.objects.create_user(
            username='testcandidate', 
            email='candidate@example.com', 
            password='ComplexPassword123!'
        )
        self.assertTrue(hasattr(user, 'profile'))
        self.assertIsInstance(user.profile, UserProfile)
        self.assertEqual(user.profile.target_role, 'Software Engineer')
        self.assertIsNotNone(user.profile.id)


class LandingAndAuthUITests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_landing_page_renders_successfully(self):
        response = self.client.get(reverse('landing'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'landing.html')
        self.assertTemplateUsed(response, 'base.html')
        self.assertContains(response, 'InterView')
        self.assertContains(response, 'Zero Video Uploads')
        self.assertContains(response, 'Real-Time Computer Vision')

    def test_login_page_renders_successfully(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/login.html')
        self.assertContains(response, 'Welcome Back')
        self.assertContains(response, 'csrfmiddlewaretoken')
        self.assertContains(response, 'id_username')
        self.assertContains(response, 'id_password')

    def test_signup_page_renders_successfully(self):
        response = self.client.get(reverse('signup'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/signup.html')
        self.assertContains(response, 'Create Candidate Account')
        self.assertContains(response, 'csrfmiddlewaretoken')
        self.assertContains(response, 'signup-email')
        self.assertContains(response, 'signup-password')
        self.assertContains(response, 'id_preferred_domain')
        self.assertContains(response, 'Anxiety-Free Mode')

    def test_security_headers_middleware_applied(self):
        response = self.client.get(reverse('landing'))
        self.assertIn('Content-Security-Policy', response.headers)
        self.assertIn('wasm-unsafe-eval', response.headers['Content-Security-Policy'])
        self.assertIn('Permissions-Policy', response.headers)
        self.assertIn('camera=(self)', response.headers['Permissions-Policy'])

    def test_favicon_redirect_resolves(self):
        response = self.client.get('/favicon.ico')
        self.assertEqual(response.status_code, 301)
        self.assertIn('/static/img/favicon.svg', response.headers['Location'])

    def test_3d_canvas_and_assets_rendered(self):
        response = self.client.get(reverse('landing'))
        self.assertContains(response, 'id="bg-3d-canvas"')
        self.assertContains(response, 'hero-cyber-stream')


class AuthBackendAndProfileTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.signup_data = {
            'username': 'alex_engineer',
            'email': 'alex@example.com',
            'password': 'SecureP@ssword123!',
            'password_confirm': 'SecureP@ssword123!',
            'target_role': 'Staff Cloud Architect',
            'preferred_domain': 'system_design',
            'anxiety_mode_default': True,
        }

    def test_signup_success_flow(self):
        response = self.client.post(reverse('signup'), self.signup_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'interviews/dashboard.html')

        user = User.objects.get(username='alex_engineer')
        self.assertEqual(user.email, 'alex@example.com')
        self.assertEqual(user.profile.target_role, 'Staff Cloud Architect')
        self.assertEqual(user.profile.preferred_domain, 'system_design')
        self.assertTrue(user.profile.anxiety_mode_default)

    def test_signup_rejects_mismatched_password(self):
        data = self.signup_data.copy()
        data['password_confirm'] = 'DifferentP@ssword123!'
        response = self.client.post(reverse('signup'), data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Passwords do not match.")
        self.assertFalse(User.objects.filter(username='alex_engineer').exists())

    def test_signup_rejects_duplicate_username_and_email(self):
        User.objects.create_user(username='existing_user', email='existing@example.com', password='Password123!')
        
        # Duplicate username
        data1 = self.signup_data.copy()
        data1['username'] = 'existing_user'
        response1 = self.client.post(reverse('signup'), data1, follow=True)
        self.assertContains(response1, "already taken")

        # Duplicate email
        data2 = self.signup_data.copy()
        data2['email'] = 'existing@example.com'
        response2 = self.client.post(reverse('signup'), data2, follow=True)
        self.assertContains(response2, "already exists")

    def test_login_with_username_and_email(self):
        User.objects.create_user(username='login_test', email='logintest@example.com', password='LoginP@ssword123!')

        # Login via username
        resp_username = self.client.post(reverse('login'), {
            'username': 'login_test',
            'password': 'LoginP@ssword123!',
        }, follow=True)
        self.assertEqual(resp_username.status_code, 200)
        self.assertTemplateUsed(resp_username, 'interviews/dashboard.html')
        self.client.logout()

        # Login via email
        resp_email = self.client.post(reverse('login'), {
            'username': 'logintest@example.com',
            'password': 'LoginP@ssword123!',
        }, follow=True)
        self.assertEqual(resp_email.status_code, 200)
        self.assertTemplateUsed(resp_email, 'interviews/dashboard.html')

    def test_logout_clears_session(self):
        user = User.objects.create_user(username='logout_test', password='Password123!')
        self.client.force_login(user)
        response = self.client.get(reverse('logout'), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'landing.html')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_update_profile_view(self):
        user = User.objects.create_user(username='profile_user', password='Password123!')
        self.client.force_login(user)

        response = self.client.post(reverse('update_profile'), {
            'target_role': 'Senior DevOps Lead',
            'preferred_domain': 'devops',
            'anxiety_mode_default': 'on',
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        user.profile.refresh_from_db()
        self.assertEqual(user.profile.target_role, 'Senior DevOps Lead')
        self.assertEqual(user.profile.preferred_domain, 'devops')
        self.assertTrue(user.profile.anxiety_mode_default)

    def test_delete_account_purges_user_and_data(self):
        user = User.objects.create_user(username='delete_me', password='Password123!')
        self.client.force_login(user)

        response = self.client.post(reverse('delete_account'), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'landing.html')
        self.assertFalse(User.objects.filter(username='delete_me').exists())


class GoogleOAuthTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_google_buttons_present_on_login_and_signup(self):
        login_resp = self.client.get(reverse('login'))
        self.assertContains(login_resp, 'id="google-login-btn"')
        self.assertContains(login_resp, 'Continue with Google')

        signup_resp = self.client.get(reverse('signup'))
        self.assertContains(signup_resp, 'id="google-signup-btn"')
        self.assertContains(signup_resp, 'Sign up instantly with Google')

    @override_settings(DEBUG=True, GOOGLE_CLIENT_ID='', GOOGLE_CLIENT_SECRET='')
    def test_google_dev_login_flow(self):
        # In DEBUG mode, visiting /accounts/google/login/ seamlessly provisions & logs in candidate
        resp = self.client.get(reverse('google_oauth_login'), follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'interviews/dashboard.html')

        user = User.objects.get(email='sarah.developer@gmail.com')
        self.assertEqual(user.first_name, 'Sarah')
        self.assertTrue(user.is_authenticated)

        # Dev login POST can also customize email
        self.client.logout()
        post_resp = self.client.post(reverse('google_dev_login'), {
            'email': 'sarah.engineer@gmail.com',
            'name': 'Sarah Engineer'
        }, follow=True)
        self.assertEqual(post_resp.status_code, 200)
        self.assertTemplateUsed(post_resp, 'interviews/dashboard.html')

        user2 = User.objects.get(email='sarah.engineer@gmail.com')
        self.assertEqual(user2.first_name, 'Sarah')
        self.assertEqual(user2.last_name, 'Engineer')

    def test_direct_email_login_flow(self):
        # Direct email login creates or logs in candidate with zero password hassle
        resp = self.client.post(reverse('direct_email_login'), {
            'email': 'direct.candidate@example.com'
        }, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'interviews/dashboard.html')

        user = User.objects.get(email='direct.candidate@example.com')
        self.assertTrue(user.is_authenticated)
        self.assertTrue(hasattr(user, 'profile'))

    @override_settings(GOOGLE_CLIENT_ID='test-client-id.apps.googleusercontent.com', GOOGLE_CLIENT_SECRET='test-secret')
    def test_google_oauth_configured_redirect(self):
        resp = self.client.get(reverse('google_oauth_login'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('https://accounts.google.com/o/oauth2/v2/auth', resp.url)
        self.assertIn('test-client-id.apps.googleusercontent.com', resp.url)
        self.assertIn('google_oauth_state', self.client.session)

    @override_settings(GOOGLE_CLIENT_ID='test-client-id.apps.googleusercontent.com', GOOGLE_CLIENT_SECRET='test-secret')
    @patch('accounts.views.exchange_code_for_user_info')
    def test_google_oauth_callback_creates_and_logs_in_user(self, mock_exchange):
        mock_exchange.return_value = {
            'email': 'cloud.lead@gmail.com',
            'name': 'Cloud Lead'
        }

        # Set session state
        session = self.client.session
        session['google_oauth_state'] = 'test-state-token'
        session.save()

        callback_url = reverse('google_oauth_callback') + '?code=valid-auth-code&state=test-state-token'
        resp = self.client.get(callback_url, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'interviews/dashboard.html')

        user = User.objects.get(email='cloud.lead@gmail.com')
        self.assertEqual(user.first_name, 'Cloud')
        self.assertTrue(user.is_authenticated)

    def test_get_or_create_candidate_from_google_deduplicates(self):
        user1, created1 = get_or_create_candidate_from_google('test.unique@gmail.com', 'Test User')
        self.assertTrue(created1)

        user2, created2 = get_or_create_candidate_from_google('test.unique@gmail.com', 'Test User')
        self.assertFalse(created2)
        self.assertEqual(user1.id, user2.id)


# -----------------------------------------------------------------------------
# Phase 8: Zero-Data Retention & Cascade Deletion Tests
# -----------------------------------------------------------------------------
class ZeroDataRetentionTests(TestCase):
    def setUp(self):
        import os
        from django.conf import settings
        from interviews.models import Interview, Question, Answer
        from analytics.models import (
            EnvironmentCheck, 
            PostureEvent, 
            SpeechMetrics, 
            Report, 
            PostureEventType
        )

        self.client = Client()
        self.user = User.objects.create_user(
            username='privacy_user', 
            email='privacy@example.com', 
            password='ComplexPassword123!'
        )
        self.interview = Interview.objects.create(
            user=self.user,
            title="Privacy Verification Interview"
        )
        self.question = Question.objects.create(
            interview=self.interview,
            order=1,
            question_text="How do you handle zero data retention?"
        )
        self.answer = Answer.objects.create(
            question=self.question,
            transcript_text="Process purely in RAM with immediate ephemeral cleanup.",
            duration_seconds=20.0,
            ai_score=95.0
        )
        self.env_check = EnvironmentCheck.objects.create(
            interview=self.interview,
            camera_ok=True,
            mic_ok=True,
            readiness_score=98.0
        )
        self.posture = PostureEvent.objects.create(
            interview=self.interview,
            event_type=PostureEventType.SLOUCHING,
            start_offset_ms=5000
        )
        self.speech = SpeechMetrics.objects.create(
            interview=self.interview,
            words_per_minute=140.0,
            total_words=300
        )

        # Create a dummy PDF on disk to test Report.delete() disk purge
        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
        self.dummy_pdf = os.path.join(settings.MEDIA_ROOT, f"test_purge_{self.interview.id}.pdf")
        with open(self.dummy_pdf, 'wb') as f:
            f.write(b"%PDF-1.4 dummy test report")

        self.report = Report.objects.create(
            interview=self.interview,
            overall_score=92.0,
            pdf_path=self.dummy_pdf
        )

    def test_delete_account_complete_cascade_purge(self):
        """
        Verify Zero-Data Guarantee: Purging user account completely removes
        all profiles, interviews, questions, answers, CV events, speech metrics,
        reports, and file artifacts with zero residual data.
        """
        import os
        from interviews.models import Interview, Question, Answer
        from analytics.models import EnvironmentCheck, PostureEvent, SpeechMetrics, Report

        self.client.force_login(self.user)
        response = self.client.post(reverse('delete_account'))
        self.assertEqual(response.status_code, 302)

        # Verify all records associated with the user are completely purged
        self.assertFalse(User.objects.filter(id=self.user.id).exists())
        self.assertFalse(UserProfile.objects.filter(user_id=self.user.id).exists())
        self.assertFalse(Interview.objects.filter(id=self.interview.id).exists())
        self.assertFalse(Question.objects.filter(interview_id=self.interview.id).exists())
        self.assertFalse(Answer.objects.filter(question_id=self.question.id).exists())
        self.assertFalse(EnvironmentCheck.objects.filter(interview_id=self.interview.id).exists())
        self.assertFalse(PostureEvent.objects.filter(interview_id=self.interview.id).exists())
        self.assertFalse(SpeechMetrics.objects.filter(interview_id=self.interview.id).exists())
        self.assertFalse(Report.objects.filter(interview_id=self.interview.id).exists())

        # Verify disk PDF artifact was deleted
        self.assertFalse(os.path.exists(self.dummy_pdf))

    def test_delete_interview_cascades_child_telemetry(self):
        """
        Deleting a single interview removes all its child questions, answers,
        and telemetry while preserving the user account.
        """
        import os
        from interviews.models import Interview, Question, Answer
        from analytics.models import EnvironmentCheck, PostureEvent, SpeechMetrics, Report

        self.client.force_login(self.user)
        response = self.client.post(reverse('delete_interview', kwargs={'interview_id': self.interview.id}))
        self.assertEqual(response.status_code, 302)

        # User and UserProfile still exist
        self.assertTrue(User.objects.filter(id=self.user.id).exists())
        self.assertTrue(UserProfile.objects.filter(user_id=self.user.id).exists())

        # Interview and its children are deleted
        self.assertFalse(Interview.objects.filter(id=self.interview.id).exists())
        self.assertFalse(Question.objects.filter(interview_id=self.interview.id).exists())
        self.assertFalse(Answer.objects.filter(question_id=self.question.id).exists())
        self.assertFalse(EnvironmentCheck.objects.filter(interview_id=self.interview.id).exists())
        self.assertFalse(PostureEvent.objects.filter(interview_id=self.interview.id).exists())
        self.assertFalse(SpeechMetrics.objects.filter(interview_id=self.interview.id).exists())
        self.assertFalse(Report.objects.filter(interview_id=self.interview.id).exists())

        # Verify disk PDF artifact was deleted
        self.assertFalse(os.path.exists(self.dummy_pdf))

    def test_zero_raw_media_files_stored(self):
        """
        Verify zero video upload guarantee: ensure no video/audio media files exist in MEDIA_ROOT.
        """
        import os
        from django.conf import settings

        forbidden_extensions = ('.mp4', '.webm', '.avi', '.mov', '.wav', '.mp3', '.ogg', '.m4a')
        if os.path.exists(settings.MEDIA_ROOT):
            for root, _, files in os.walk(settings.MEDIA_ROOT):
                for f in files:
                    self.assertFalse(
                        f.lower().endswith(forbidden_extensions),
                        f"Found forbidden uploaded video/audio file: {f}"
                    )

