from django.test import TestCase, override_settings
from ai_engine.providers import (
    get_ai_provider,
    MockNLPProvider,
    GroqProvider,
    GeminiProvider,
    QuestionSchema,
    QuestionsPayloadSchema,
    AnswerEvaluationSchema,
    FollowUpSchema
)

class AIEngineSchemaAndProviderTests(TestCase):
    def test_mock_nlp_provider_generates_valid_questions(self):
        provider = MockNLPProvider()
        questions = provider.generate_questions(
            domain="fullstack",
            difficulty="senior",
            persona="Analytical Technical Lead",
            count=5
        )
        self.assertEqual(len(questions), 5)
        for q in questions:
            self.assertIn("order", q)
            self.assertIn("question", q)
            self.assertIn("category", q)
            self.assertIn("expected_key_points", q)

    def test_mock_nlp_provider_evaluates_answer(self):
        provider = MockNLPProvider()
        res = provider.evaluate_answer(
            question_text="Explain database connection pooling.",
            answer_text="Connection pooling maintains an active pool of open database connections to reduce handshake latency.",
            persona="Analytical Technical Lead",
            domain="backend",
            difficulty="mid"
        )
        self.assertIn("score", res)
        self.assertTrue(0.0 <= res["score"] <= 100.0)
        self.assertIn("summary", res)
        self.assertIn("strengths", res)
        self.assertIn("improvements", res)
        self.assertIn("star_analysis", res)

    def test_mock_nlp_provider_follow_up(self):
        provider = MockNLPProvider()
        follow_up = provider.generate_follow_up(
            question_text="How do you cache responses?",
            answer_text="I use Redis in front of PostgreSQL.",
            persona="Analytical Technical Lead"
        )
        self.assertIn("should_ask_follow_up", follow_up)
        self.assertIn("follow_up_question", follow_up)

    def test_pydantic_schema_validation(self):
        valid_q = QuestionSchema(
            order=1,
            question="What is Event Loop in JavaScript?",
            category="Technical",
            expected_key_points=["Call stack", "Task queue", "Microtasks"]
        )
        self.assertEqual(valid_q.order, 1)

        payload = QuestionsPayloadSchema(questions=[valid_q])
        self.assertEqual(len(payload.questions), 1)

        eval_schema = AnswerEvaluationSchema(
            score=88.5,
            summary="Strong understanding of concurrency.",
            strengths=["Clear microtask ordering"],
            improvements=["Mention process.nextTick"],
            star_analysis={"action": "Explained single-threaded event loop"}
        )
        self.assertEqual(eval_schema.score, 88.5)

    def test_get_ai_provider_fallback(self):
        # With default or empty key, get_ai_provider falls back to MockNLPProvider
        provider = get_ai_provider()
        self.assertIsInstance(provider, (MockNLPProvider, GroqProvider, GeminiProvider))

    def test_mock_nlp_provider_diversity_and_exclusion(self):
        provider = MockNLPProvider()
        batch_1 = provider.generate_questions(domain="backend", difficulty="senior", persona="Tech Lead", count=3)
        asked_texts = [q["question"] for q in batch_1]

        # Generate batch 2 excluding batch 1 questions
        batch_2 = provider.generate_questions(
            domain="backend", 
            difficulty="senior", 
            persona="Tech Lead", 
            count=3,
            exclude_questions=asked_texts
        )
        batch_2_texts = [q["question"] for q in batch_2]

        # Verify no intersection between batch 1 and batch 2
        for q_text in batch_2_texts:
            self.assertNotIn(q_text, asked_texts)

    def test_semantic_answer_evaluation_distinguishes_good_from_empty_answers(self):
        provider = MockNLPProvider()
        q_text = "Can you explain the difference between optimistic and pessimistic locking in database transactions?"

        # 1. Empty / Inaudible answer
        empty_res = provider.evaluate_answer(
            question_text=q_text,
            answer_text="(Candidate provided no audible response)",
            persona="Tech Lead",
            domain="backend",
            difficulty="senior"
        )
        self.assertLessEqual(empty_res["score"], 25.0)

        # 2. Rich, accurate answer
        rich_ans = (
            "Optimistic locking uses a version column or timestamp to check for concurrent modifications at commit time, "
            "making it ideal for low contention. Pessimistic locking acquires explicit SELECT FOR UPDATE row-level locks, "
            "which prevents concurrent writes but increases deadlock risk and limits transaction throughput."
        )
        rich_res = provider.evaluate_answer(
            question_text=q_text,
            answer_text=rich_ans,
            persona="Tech Lead",
            domain="backend",
            difficulty="senior"
        )
        self.assertGreaterEqual(rich_res["score"], 78.0)
        self.assertGreater(len(rich_res["strengths"]), 0)
        self.assertIn("star_analysis", rich_res)
        self.assertIsInstance(rich_res["star_analysis"]["action"], (int, float))

    def test_contextual_follow_up_non_repeating(self):
        provider = MockNLPProvider()
        q_text = "How do you design an idempotent payment processing API to guarantee customers are never double-charged during network timeouts?"
        ans_text = "I pass a client-generated Idempotency-Key in the request header and use Redis with an atomic SETNX to lock and store the response."

        fu1 = provider.generate_follow_up(
            question_text=q_text,
            answer_text=ans_text,
            persona="Tech Lead",
            score=85.0
        )
        self.assertTrue(fu1["should_ask_follow_up"])
        q1_text = fu1["follow_up_question"]
        self.assertTrue(len(q1_text) > 10)

        # Asking a second follow-up excluding the first one
        fu2 = provider.generate_follow_up(
            question_text=q_text,
            answer_text=ans_text,
            persona="Tech Lead",
            score=85.0,
            already_asked_follow_ups=[q1_text]
        )
        if fu2["should_ask_follow_up"]:
            self.assertNotEqual(fu2["follow_up_question"], q1_text)


    @override_settings(DEFAULT_AI_PROVIDER="gemini", GEMINI_API_KEY="AIzaSyDummyTestKey1234567890", GEMINI_MODEL="gemini-2.5-flash")
    def test_get_ai_provider_returns_gemini_when_configured(self):
        from ai_engine.providers import GeminiProvider
        provider = get_ai_provider()
        self.assertIsInstance(provider, GeminiProvider)
        self.assertEqual(provider.model, "gemini-2.5-flash")

    def test_gemini_provider_structured_methods_with_mock_client(self):
        from unittest.mock import MagicMock
        from ai_engine.providers import (
            GeminiProvider,
            GeminiAnswerEvaluationSchema,
            StarAnalysisSchema,
            HolisticAnalysisSchema,
        )

        provider = GeminiProvider(api_key="AIzaSyDummyTestKey1234567890", model="gemini-2.5-flash")
        mock_client = MagicMock()
        provider._client = mock_client

        # 1. Question generation
        q_payload = QuestionsPayloadSchema(questions=[
            QuestionSchema(order=1, question="How does consistent hashing work?", category="system_design", expected_key_points=["ring", "virtual nodes"])
        ])
        mock_client.models.generate_content.return_value = MagicMock(parsed=q_payload)
        qs = provider.generate_questions(domain="system_design", difficulty="senior", persona="Tech Lead", count=1)
        self.assertEqual(len(qs), 1)
        self.assertEqual(qs[0]["question"], "How does consistent hashing work?")

        # 2. Answer evaluation
        eval_payload = GeminiAnswerEvaluationSchema(
            score=91.5,
            strengths=["Explained virtual nodes"],
            improvements=["Discuss rebalancing latency"],
            star_analysis=StarAnalysisSchema(situation=85, task=85, action=92, result=90),
            summary="Strong systems explanation."
        )
        mock_client.models.generate_content.return_value = MagicMock(parsed=eval_payload)
        res = provider.evaluate_answer("Q?", "A", "Tech Lead", "system_design", "senior")
        self.assertEqual(res["score"], 91.5)
        self.assertEqual(res["star_analysis"]["action"], 92.0)

        # 3. Follow-up generation
        fu_payload = FollowUpSchema(should_ask_follow_up=True, follow_up_question="How do you handle hot keys?", rationale="Hot key mitigation")
        mock_client.models.generate_content.return_value = MagicMock(parsed=fu_payload)
        fu = provider.generate_follow_up("Q?", "A", "Tech Lead", score=91.5)
        self.assertTrue(fu["should_ask_follow_up"])

        # 4. Holistic interview analysis
        holistic_payload = HolisticAnalysisSchema(
            executive_summary="Candidate showed strong systems depth.",
            top_strengths=["Consistent hashing"],
            priority_improvements=["Quantify metrics"],
            readiness_verdict="Hire Ready"
        )
        mock_client.models.generate_content.return_value = MagicMock(parsed=holistic_payload)
        holistic = provider.analyze_full_interview(
            domain="System Design", difficulty="Senior", persona="Tech Lead",
            qa_pairs=[{"order": 1, "category": "System Design", "question": "Q?", "answer": "A", "score": 91.5}],
            posture_summary="Good posture", speech_summary="140 WPM, 1 filler",
            scores={"overall": 90.0}
        )
        self.assertEqual(holistic["readiness_verdict"], "Hire Ready")
