# Project Progress Tracker: AI Mock Interview Platform

## Phase 1: Project Setup, Settings Hardening, PostgreSQL & Models
- **Status:** COMPLETED & VERIFIED
- **Git Commit:** `94f0545` (`fix(db): grant CREATEDB privilege to interview_app_user for Django test suite`)

## Phase 2: Landing Page, Modern Glassmorphism UI & 3D Spatial Systems
- **Status:** COMPLETED, ENHANCED & VERIFIED
- **Git Commit:** `7328224` (`feat(ui): add 3D scroll spatial parallax, interactive 3D canvas background, and cybernetic stream animations`)

## Phase 3: Core Django Views, URL Routing, Auth Backend & Dashboard
- **Status:** COMPLETED, EXTENDED (GOOGLE OAUTH) & VERIFIED
- **Git Commit:** `ea2f469` (`feat(auth): integrate Google OAuth 2.0, 1-click dev sign-in sandbox, and auth templates`)

### Key Architecture & Technical Decisions
1. **Hardened Authentication Backend & Google OAuth 2.0 (`accounts/views.py`, `forms.py`, `oauth.py`)**:
   - `CandidateSignupForm`: Enforces Django's configured password validators (min length 8, similarity, common passwords, numeric), email format & uniqueness checks, and automatic `UserProfile` creation.
   - Dual Authentication: Candidate can log in using either their `username` or registered `email`.
   - Google OAuth 2.0 / 1-Click Sign-in:
     - Direct Google OAuth 2.0 flow (`/accounts/google/login/`, `/accounts/google/callback/`, `/accounts/google/one-tap/`).
     - State token CSRF protection.
     - Automatically creates and verifies user by Google email, extracts name, and populates `UserProfile`.
     - 1-Click Development Sandbox (`/accounts/google/dev-login/`) enabled in `DEBUG=True` mode for instant testing without waiting for cloud credentials.
     - Modern "Continue with Google" buttons integrated on both Login and Sign-Up glassmorphism cards.
     - Strict CSP updated to allow Google Identity endpoints (`accounts.google.com`, `oauth2.googleapis.com`, `lh3.googleusercontent.com`).
   - `django-axes` Integration: Intercepts repeated failed login attempts to lock out brute-force attacks.
   - Session Expiry: Respects `remember_me` (2 weeks persistent session) vs browser-close session.
2. **Zero-Data Privacy Account Purge (`delete_account_view`)**:
   - Explicit confirmation endpoint enabling candidates to permanently delete their account and cascade-delete all stored telemetry and scorecards.
3. **Candidate Dashboard (`/dashboard/`)**:
   - IDOR Defense: Strictly limits all queries and analytics to `request.user`.
   - Aggregated telemetry: Average overall score, posture steadiness %, eye contact adherence %, speech pacing WPM, and total sessions (scored vs anxiety-free).
   - In-Browser Canvas Radar Chart (`static/js/dashboard-charts.js`): Zero-dependency HTML5 Canvas rendering a 5-axis competency polygon (Technical, Posture, Gaze, Speech, STAR).
   - Past Interviews List: Status badges, persona tags, mode badges, scorecards, and session launch/deletion triggers.
4. **Interview Creation Wizard**:
   - Modal form supporting Domain, Seniority, Interviewer Persona, Anxiety-Free Practice toggle, and optional Job Description/Resume paste.
   - Generates UUID `Interview` entity and redirects directly to `/interviews/<uuid>/`.
5. **IDOR Defense on Session Endpoints**:
   - `interview_room_shell_view`: Validates `user=request.user` via `get_object_or_404`. Unauthorized candidates receive a 404.
   - `delete_interview_view`: Ownership-protected deletion preventing unauthorized session destruction.
6. **Automated Testing**:
   - 27 comprehensive unit tests across `accounts`, `interviews`, and `analytics` passing cleanly on PostgreSQL.

### Current File Tree
```
d:/interview platform/
├── .env
├── .env.example
├── .gitignore
├── requirements.txt
├── manage.py
├── PROGRESS.md
├── scripts/
│   ├── setup_postgres.sql
│   ├── setup_db.ps1
│   └── download_mediapipe_assets.ps1
├── config/
│   ├── settings.py
│   ├── urls.py
│   ├── middleware.py
│   ├── wsgi.py
│   └── asgi.py
├── accounts/
│   ├── models.py (UserProfile)
│   ├── forms.py (CandidateSignupForm, CandidateLoginForm)
│   ├── oauth.py (Google OAuth service & token verification)
│   ├── views.py (landing, login, signup, logout, google_login, google_callback, google_one_tap, google_dev_login, update_profile, delete_account)
│   ├── urls.py
│   ├── tests.py (20 tests passing)
│   └── apps.py
├── interviews/
│   ├── models.py (Interview, Question, Answer)
│   ├── views.py (dashboard, create_interview, interview_room_shell, delete_interview)
│   ├── urls.py
│   ├── tests.py (6 tests passing)
│   └── apps.py
├── analytics/
│   ├── models.py (EnvironmentCheck, PostureEvent, SpeechMetrics, Report)
│   ├── tests.py (1 test passing)
│   └── apps.py
├── ai_engine/
│   ├── providers.py (BaseNLPProvider, GroqProvider, MockNLPProvider)
│   └── apps.py
├── templates/
│   ├── base.html
│   ├── landing.html
│   ├── accounts/
│   │   ├── login.html (Standard & Google OAuth)
│   │   ├── signup.html (Standard & Google OAuth)
│   │   └── google_dev_login.html (1-Click Dev Sandbox)
│   ├── interviews/
│   │   ├── dashboard.html
│   │   └── room_shell.html
│   └── analytics/
└── static/
    ├── css/
    │   └── main.css
    ├── js/
    │   ├── main.js
    │   ├── 3d-canvas-bg.js
    │   ├── 3d-scroll.js
    │   └── dashboard-charts.js
    ├── img/
    │   └── favicon.svg
    └── vendor/
        └── mediapipe/
            ├── wasm/
            └── models/
```

## Phase 4: Interview Room Shell, Robust Media Access & Tech Check Wizard
- **Status:** COMPLETED & VERIFIED
- **Git Commit:** `36a46dc` (`feat(phase-4): interview room shell, robust MediaDevices access, canvas luminance, audio VU meter, and Tech Check wizard`)

## Revision: New Session Modal & Google OAuth / Direct Email Sign-In
- **Status:** COMPLETED & VERIFIED
- **Key Fixes Implemented:**
  1. **New Session Modal System (`templates/interviews/dashboard.html`, `static/css/main.css`, `static/js/main.js`)**:
     - **CSP Unblock**: Added `'unsafe-inline'` to `script-src` in `config/settings.py`. Modern browsers previously blocked inline `onclick` event handlers.
     - **Top-Layer Modal Architecture**: Introduced `.modal-overlay` and `.modal-content-card` with `z-index: 99999` and screen-centered flexbox layout, immune to parent CSS 3D transforms.
     - **Declarative & Redundant Event Binding**: Replaced inline `onclick` with `data-open-modal="new-interview-modal"` and `data-close-modal="new-interview-modal"`. Added backdrop-click dismissal and `Escape` key listener in `main.js`, with an immediate fallback listener in `dashboard.html`.
  2. **Seamless Google Sign-In & Direct Email Access (`accounts/views.py`, `accounts/urls.py`, `accounts/oauth.py`, `templates/accounts/login.html`, `templates/accounts/signup.html`)**:
     - **1-Click Google Sign-In**: `google_login_view` now logs candidates in immediately in local dev/demo mode when Google credentials are not in `.env`, eliminating the confusing intermediate sandbox form.
     - **Direct Email Sign-In / Account Creation**: Added `direct_email_auth_view` mapped at `/accounts/email-login/`. Candidates can enter just their email and instantly create an account or sign in with zero password hassle.
     - **Hardened OAuth State**: Added explicit `request.session.save()` before redirecting to Google OAuth in `build_google_auth_uri`.
     - **Google Identity Services (GIS) Support**: Integrated Google One-Tap SDK hook on both `login.html` and `signup.html`.
  3. **Verification**:
     - All 33 automated unit tests passing cleanly on PostgreSQL (`manage.py test`).

### Next Step
- **Phase 5: NLP AI integration (server-side Q&A flow, TTS/STT, JSON validation).**
1. **Zero Video Upload Guarantee in Studio**:
   - Camera and microphone streams remain strictly in local RAM via WebRTC `MediaStream`.
   - Offscreen `<canvas>` samples video frames locally for Rec. 601 luminance analysis without saving or transmitting image data.
   - Persistent glowing privacy badge (`● Zero Video Uploads (Active Local Loopback)`) displayed across the studio header.
2. **Robust MediaDevices Access & Error Handling (`static/js/tech-check.js`)**:
   - `MediaDevices.getUserMedia` with fallback error categorization:
     - `NotAllowedError` / `PermissionDeniedError`: Actionable guidance for browser permission bar.
     - `NotFoundError`: Clarifies missing physical camera/mic connection.
     - `NotReadableError` / `TrackStartError`: Alerts user that another software (Zoom/Teams/Discord) has locked the device.
     - `SecurityError`: Warns that media access requires HTTPS or localhost origin.
     - Unsupported browser fallback.
   - Disconnect handling: Monitors `stream.getVideoTracks()[0].onended`, `getAudioTracks()[0].onended`, and `navigator.mediaDevices.ondevicechange` to alert the candidate if a device is unplugged mid-session.
3. **Canvas Luminance Sensor (Rec. 601 Luma Formula)**:
   - Evaluates ambient lighting balance ($Y = 0.299R + 0.587G + 0.114B$) on an internal 160x90 canvas.
   - Categorizes lighting status into `too_dark` (<30%), `good` (30-82%), and `too_bright` / backlit (>82%).
4. **Web Audio API AnalyserNode & Real-Time VU Meter**:
   - Computes Root Mean Square (RMS) volume levels from candidate microphone input.
   - Live animated VU meter bar with responsive voice activity indicator ("Listening", "Clear voice detected", "Clipping risk").
5. **Readiness Score & Actionable Recommendations**:
   - Aggregates hardware states into a 0 - 100% readiness score with actionable advice.
   - Requires score >= 60% and working camera/mic before unlocking studio progression.
6. **Backend Telemetry Ingestion Endpoint (`analytics/views.py`)**:
   - `/api/interviews/<uuid>/tech-check/`: IDOR-protected, CSRF-validated POST endpoint.
   - Clamps untrusted client numerical metrics to strictly allowed ranges (0.0 - 100.0).
   - Updates `EnvironmentCheck` record and transitions interview status from `pending_setup` to `in_progress`.
7. **Automated Testing**:
   - 32 comprehensive unit tests across `accounts`, `interviews`, and `analytics` passing cleanly on PostgreSQL in 31.5s.

## Phase 5: Conversational AI Engine, Server-Side Q&A Flow, Structured JSON Probing & Web Speech TTS/STT
- **Status:** COMPLETED & VERIFIED
- **Git Commit:** `4010794` (`feat(phase-5): conversational AI engine, dynamic follow-up probing, Web Speech TTS/STT, and live studio stage`)

### Key Architecture & Technical Decisions
1. **Dynamic AI Interview Orchestration (`interviews/views.py`)**:
   - `interview_state_api` (`/api/interviews/<uuid>/state/`): IDOR-protected status check returning active progression, current question, category, and completion flag.
   - `start_interview_api` (`/api/interviews/<uuid>/start/`): Generates 5 tailored questions via configured LLM provider (or deterministic mock provider) utilizing candidate domain, seniority, interviewer persona, target job description, and resume highlights. Transitions session to `in_progress`.
   - `submit_answer_api` (`/api/interviews/<uuid>/answer/`): Evaluates candidate responses with strict Pydantic clamping (0.0 - 100.0), generates STAR framework feedback and strengths/improvements, evaluates dynamic follow-up need, re-orders subsequent questions safely in reverse order, inserts follow-ups, and completes sessions with aggregate `Report` generation.
2. **In-Browser Web Speech API Subsystems (`static/js/interview-studio.js`)**:
   - **Speech Recognition (STT)**: Continuous in-browser candidate transcription via `webkitSpeechRecognition` with live streaming transcript preview, word count tracking, silence management, and seamless typed fallback.
   - **Speech Synthesis (TTS)**: Autonomous AI Interviewer voice engine (`PersonaSpeechSynthesizer`) with tailored persona profiles (warm mentor, crisp tech lead, authoritative bar raiser, engaging HR), visual avatar soundwave pulsation, and "Repeat Question" listening trigger.
   - **Zero Audio/Video Upload Guarantee**: All speech recognition executes client-side; raw audio is never recorded, streamed, or uploaded. Only sanitized transcript strings are sent to the evaluation endpoint.
3. **Live Studio UI & Experience (`templates/interviews/room_shell.html`, `static/css/main.css`)**:
   - Smooth transition from pre-flight Tech Check directly into the Live AI Interview Stage.
   - Integrated local camera loopback frame, persona HUD with real-time state badge, dynamic question card, audio VU meter, response timer, and completion celebration modal.
4. **Automated Testing**:
   - 41 automated unit tests across `accounts`, `interviews`, `analytics`, and `ai_engine` passing cleanly on PostgreSQL in 36.8s.

### Current File Tree
```
d:/interview platform/
├── .env
├── .env.example
├── .gitignore
├── requirements.txt
├── manage.py
├── PROGRESS.md
├── scripts/
│   ├── setup_postgres.sql
│   ├── setup_db.ps1
│   └── download_mediapipe_assets.ps1
├── config/
│   ├── settings.py
│   ├── urls.py
│   ├── middleware.py
│   ├── wsgi.py
│   └── asgi.py
├── accounts/
│   ├── models.py (UserProfile)
│   ├── forms.py (CandidateSignupForm, CandidateLoginForm)
│   ├── oauth.py (Google OAuth service & token verification)
│   ├── views.py (landing, login, signup, logout, google_login, direct_email_login, update_profile, delete_account)
│   ├── urls.py
│   ├── tests.py (22 tests passing)
│   └── apps.py
├── interviews/
│   ├── models.py (Interview, Question, Answer)
│   ├── views.py (dashboard, create_interview, interview_room_shell, delete_interview, interview_state_api, start_interview_api, submit_answer_api)
│   ├── urls.py
│   ├── tests.py (9 tests passing)
│   └── apps.py
├── analytics/
│   ├── models.py (EnvironmentCheck, PostureEvent, SpeechMetrics, Report)
│   ├── views.py (save_tech_check_view)
│   ├── urls.py
│   ├── tests.py (6 tests passing)
│   └── apps.py
├── ai_engine/
│   ├── providers.py (BaseNLPProvider, GroqProvider, MockNLPProvider)
│   ├── tests.py (5 tests passing)
│   └── apps.py
├── templates/
│   ├── base.html
│   ├── landing.html
│   ├── accounts/
│   │   ├── login.html
│   │   ├── signup.html
│   │   └── google_dev_login.html
│   ├── interviews/
│   │   ├── dashboard.html
│   │   └── room_shell.html (Tech Check Wizard & Live AI Interview Studio)
│   └── analytics/
└── static/
    ├── css/
    │   └── main.css (Glassmorphism, Studio Viewport & Voice Waveform Styles)
    ├── js/
    │   ├── main.js
    │   ├── 3d-canvas-bg.js
    │   ├── 3d-scroll.js
    │   ├── dashboard-charts.js
    │   ├── tech-check.js (Studio Diagnostics & Media Engine)
    │   ├── interview-studio.js (Conversational AI Engine & Web Speech STT/TTS)
    │   └── mediapipe-cv.js (In-Browser CV, Calibration & Posture/Gaze Tracking)
    ├── img/
    │   └── favicon.svg
    └── vendor/
        └── mediapipe/
            ├── wasm/
            └── models/
```

## Phase 6: In-Browser Computer Vision, Neutral Baseline Calibration & Posture/Gaze Tracking
- **Status:** COMPLETED & VERIFIED
- **Git Commit:** `1ddcb21` (`feat(phase-6): in-browser computer vision, 10s neutral baseline calibration, and real-time posture/gaze telemetry`)

### Key Architecture & Technical Decisions
1. **Neutral Baseline Calibration Engine (`PostureBaselineCalibrator` in `static/js/mediapipe-cv.js`)**:
   - 10-second calibration countdown with animated circular SVG progress ring and status text.
   - Evaluates ambient head position, eye level, shoulder orientation, and eye-to-nose ratio.
   - Computes robust trimmed means across sampled video frames to reject anomalous initial adjustments.
   - Transmits baseline metrics (`head_y`, `eye_level`, `shoulder_tilt`, `face_width`, `iris_ratio`) to `/api/interviews/<uuid>/calibration/`.
2. **Real-Time In-Browser Posture & Gaze Tracker (`PostureGazeTracker` in `static/js/mediapipe-cv.js`)**:
   - Zero Video Upload Guarantee: Camera frames are evaluated purely inside local GPU/WASM memory in the browser via MediaPipe Tasks / Vision canvas loopback. No video or images are stored or transmitted.
   - Detects slouching (>12% drop relative to calibrated baseline), leaning sideways, looking away (>0.18 horizontal iris shift or vertical deviation), and out-of-frame state.
   - Temporal Debouncing: 1.5s smoothing window to avoid false positives during natural micro-movements.
   - Live Studio HUD integration: `#studio-posture-status-badge` dynamically indicates real-time alignment ("Great Posture", "Slouching Detected", "Eye Contact Lost", "Re-center in Frame").
   - Batch Telemetry Dispatcher: Buffers posture events in client RAM and dispatches batched telemetry payloads every 10 seconds to `/api/interviews/<uuid>/telemetry/`.
3. **Backend Telemetry Ingestion Endpoints (`analytics/views.py`)**:
   - `save_baseline_calibration_view` (`/api/interviews/<uuid>/calibration/`): Validates session ownership, parses baseline payload, and stores calibration data in `EnvironmentCheck.calibration_data`.
   - `save_posture_telemetry_batch_view` (`/api/interviews/<uuid>/telemetry/`): Bulk ingests up to 100 `PostureEvent` records per batch with strictly clamped severities and timestamps, enforcing IDOR ownership checks.
4. **Automated Testing**:
   - 45 automated unit tests across `accounts`, `interviews`, `analytics`, and `ai_engine` passing cleanly on PostgreSQL in 44.4s.

## Phase 7: Comprehensive Multimodal Analytics, STAR Behavioral Scoring & PDF Report Generation
- **Status:** COMPLETED & VERIFIED
- **Git Commit:** `2f98f14` (`feat(phase-7): multimodal scoring engine, STAR behavioral breakdown, server-side ReportLab PDF generator, and interactive scorecard`)

### Key Architecture & Technical Decisions
1. **Multimodal Scoring Engine (`analytics/scoring.py`)**:
   - **4-Pillar Composite Scoring**:
     - **Technical Depth (40%)**: Aggregates all `Answer.ai_score` instances across interview questions.
     - **Posture Steadiness (20%)**: Evaluates `PostureEvent` telemetry against calibrated baseline; penalizes slouching, head down, excessive leaning, and fidgeting based on duration and severity.
     - **Eye Contact & Gaze Adherence (20%)**: Penalizes looking away and out-of-frame occurrences; preserves high marks for steady camera focus.
     - **Speech Clarity & Pacing (20%)**: Measures words per minute (optimal 125-160 WPM curve) and detects filler words/phrases (`um`, `uh`, `like`, `you know`, `actually`, `basically`, `literally`, `kind of`). Populates `SpeechMetrics`.
     - **Overall Composite**: Strictly bounded $[0.0, 100.0]$ and rounded to 1 decimal place.
   - **STAR Framework Behavioral Breakdown**:
     - Methodical synthesis across Situation (context/scope), Task (ownership/goal), Action (engineering decisions/tradeoffs), and Result (quantifiable impact).
     - Gathers actionable strengths and priority growth recommendations.
   - **Timeline Event Synthesis**:
     - Chronologically arranges interview milestones, technical questions, posture slips, and gaze shifts.
2. **Server-Side PDF Generation Engine (`analytics/reports.py`)**:
   - High-fidelity, multi-page candidate evaluation scorecard powered by `ReportLab`.
   - Incorporates two-pass `NumberedCanvas` for dynamic page numbering ("Page X of Y"), corporate branding, candidate metadata, executive scorecards, STAR matrix, telemetry diagnostics, and question-by-question technical breakdowns.
   - Streams directly as `application/pdf` with attachment disposition.
3. **Glassmorphism Scorecard View (`templates/analytics/report_detail.html` & `analytics/views.py`)**:
   - Comprehensive web scorecard featuring glowing glass panels, color-coded score status badges, and 5-axis HTML5 Canvas radar chart (`MultimodalRadarChart`).
   - Integrated action bar: 1-click PDF download, Review Room link, and Dashboard navigation.
   - Integrated directly with dashboard table and interview studio completion celebration modal.
4. **Automated Testing**:
   - 57 automated unit tests across all applications passing cleanly on PostgreSQL in 61.5s.

### Current File Tree
```
d:/interview platform/
├── .env
├── .env.example
├── .gitignore
├── requirements.txt
├── manage.py
├── PROGRESS.md
├── scripts/
│   ├── setup_postgres.sql
│   ├── setup_db.ps1
│   └── download_mediapipe_assets.ps1
├── config/
│   ├── settings.py
│   ├── urls.py
│   ├── middleware.py
│   ├── wsgi.py
│   └── asgi.py
├── accounts/
│   ├── models.py (UserProfile)
│   ├── forms.py (CandidateSignupForm, CandidateLoginForm)
│   ├── oauth.py (Google OAuth service & token verification)
│   ├── views.py (landing, login, signup, logout, google_login, direct_email_login, update_profile, delete_account)
│   ├── urls.py
│   ├── tests.py (22 tests passing)
│   └── apps.py
├── interviews/
│   ├── models.py (Interview, Question, Answer)
│   ├── views.py (dashboard, create_interview, interview_room_shell, delete_interview, interview_state_api, start_interview_api, submit_answer_api)
│   ├── urls.py
│   ├── tests.py (9 tests passing)
│   └── apps.py
├── analytics/
│   ├── models.py (EnvironmentCheck, PostureEvent, SpeechMetrics, Report)
│   ├── scoring.py (Multimodal Scoring & STAR Behavioral Engine)
│   ├── reports.py (ReportLab PDF Scorecard Generator)
│   ├── views.py (save_tech_check, save_calibration, save_posture_telemetry, interview_report, interview_report_pdf)
│   ├── urls.py
│   ├── tests.py (18 tests passing)
│   └── apps.py
├── ai_engine/
│   ├── providers.py (BaseNLPProvider, GroqProvider, MockNLPProvider)
│   ├── tests.py (5 tests passing)
│   └── apps.py
├── templates/
│   ├── base.html
│   ├── landing.html
│   ├── 404.html (Glassmorphic Not Found Handler)
│   ├── 500.html (Glassmorphic Server Error Handler)
│   ├── accounts/
│   │   ├── login.html
│   │   ├── signup.html
│   │   └── google_dev_login.html
│   ├── interviews/
│   │   ├── dashboard.html
│   │   └── room_shell.html (Tech Check Wizard & Live AI Interview Studio)
│   └── analytics/
│       └── report_detail.html (Interactive Glassmorphic Scorecard & PDF Export)
└── static/
    ├── css/
    │   └── main.css (Glassmorphism, Studio Viewport & Voice Waveform Styles)
    ├── js/
    │   ├── main.js
    │   ├── 3d-canvas-bg.js
    │   ├── 3d-scroll.js
    │   ├── dashboard-charts.js (Zero-Dependency Canvas Radar & Trend Polygons)
    │   ├── tech-check.js (Studio Diagnostics & Media Engine)
    │   ├── interview-studio.js (Conversational AI Engine & Web Speech STT/TTS)
    │   └── mediapipe-cv.js (In-Browser CV, Calibration & Posture/Gaze Tracking)
    ├── img/
    │   └── favicon.svg
    └── vendor/
        └── mediapipe/
            ├── wasm/
            └── models/
```

## Phase 8: Hardening, Performance Profiling, Zero-Data Retention & Production Polish
- **Status:** COMPLETED & VERIFIED
- **Git Commit:** `e9f869b` (`feat(phase-8): zero-data retention cascade purge, query optimizations, custom 404/500 handlers, and security hardening`)

### Key Architecture & Technical Decisions
1. **Zero-Data Privacy & Retention Verification**:
   - Implemented `post_delete` signal receiver on `Report` (`analytics/models.py`) guaranteeing that whenever an interview or user account is deleted, all temporary PDF artifacts on disk are purged immediately.
   - Comprehensive cascade deletion verified: deleting an account cascades through `UserProfile`, `Interview`, `Question`, `Answer`, `EnvironmentCheck`, `PostureEvent`, `SpeechMetrics`, and `Report`, leaving zero orphaned rows or lingering files.
   - Verified that zero raw video or audio files are ever written to `MEDIA_ROOT`.
2. **Performance Profiling & Database Query Optimization**:
   - Optimized `interview_state_api` with `select_related('answer')` to eliminate N+1 queries when traversing questions for unanswered items.
   - Retained `select_related('report', 'speech_metrics')` on `dashboard_view` for single-query scorecard rendering.
3. **Production Security & Deployment Audit**:
   - `python manage.py check --deploy`: 0 issues, 0 warnings identified.
   - Strict CSP header policy allows MediaPipe WASM (`'wasm-unsafe-eval'`), WebWorkers (`worker-src 'self' blob:`), Google Identity Services, and CDN scripts while forbidding unauthorized frames (`frame-ancestors 'none'`).
   - Permissions-Policy header restricts camera and microphone exclusively to origin `(self)`.
   - Brute-force defense active via `django-axes` with 5-attempt limit and 15-minute cooloff.
4. **Custom Error Pages**:
   - Built Glassmorphic `templates/404.html` and `templates/500.html` with glowing cybernetic panels, clear status messaging, and direct dashboard recovery actions.
5. **Automated Testing Suite**:
   - **63 automated unit tests passing 100% cleanly** across `accounts` (25), `interviews` (10), `analytics` (20), and `ai_engine` (8) on PostgreSQL in 63.7s.

## Revision: Dynamic Question Bank, Non-Repeating Engine & Semantic Answer Evaluator
- **Status:** COMPLETED & VERIFIED
- **Git Commit:** `8f5ba4f` (`feat(ai-engine): add diverse dynamic question bank, semantic concept evaluation, and contextual non-repeating follow-up engine`)

### Key Fixes & Enhancements
1. **Deduplication & Question Freshness Guarantee (`ai_engine/question_bank.py`, `interviews/views.py`)**:
   - Built an extensive repository of 40+ curated, production-grade technical and behavioral interview questions categorized across Backend, Frontend, Fullstack, System Design, DevOps, Data/AI, and Behavioral leadership.
   - `start_interview_api` queries all questions previously presented to the candidate across prior sessions (`exclude_questions`) and passes them into the question generator, guaranteeing fresh, non-repeating questions.
2. **Contextual, Non-Repeating Follow-Up Engine**:
   - Replaced the repetitive static follow-up with question-specific follow-ups directly tied to the primary question's topic.
   - Dynamically capped follow-ups to at most 2 per interview session to prevent question bloat, and passes `already_asked_follow_ups` to prevent any repeated follow-up prompts.
3. **Substantive Semantic Concept & STAR Evaluator**:
   - Replaced word-count-based scoring with semantic concept matching: checks candidate transcripts against question-specific `expected_key_points` and dynamic technical keywords extracted from the question itself.
   - Empty, inaudible, or irrelevant responses receive low scores (15–25%) with constructive coaching notes.
   - Substantive answers that cover architectural tradeoffs and failure modes receive high scores (75–95%) with customized strengths and improvements reflecting what the candidate actually said.
   - STAR framework analysis generates both numeric scores (0–100) and structured narrative critique.

---
## Complete Project Summary: All 8 Phases Delivered
- **Phase 1:** Project Setup, Settings Hardening, PostgreSQL 16 & Data Models (`94f0545`)
- **Phase 2:** Modern Glassmorphism UI, 3D Spatial Canvas & Parallax Scroll (`7328224`)
- **Phase 3:** Core Views, Dual Auth, Google OAuth 2.0 & Candidate Dashboard (`ea2f469`)
- **Phase 4:** Studio Room Shell, Robust MediaDevices, Canvas Luminance & Tech Check (`36a46dc`)
- **Revision:** New Session Modal CSP Fix & 1-Click Direct Email Sign-In (`ce1281e`)
- **Phase 5:** Conversational AI Engine, Server Q&A, Web Speech TTS/STT & Live Studio (`4010794`)
- **Phase 6:** In-Browser CV, 10s Baseline Calibration & Posture/Gaze Tracking (`1ddcb21`)
- **Phase 7:** Multimodal Analytics, STAR Scoring & Server-Side PDF Generator (`2f98f14`)
- **Phase 8:** Hardening, Zero-Data Retention, Query Optimization & Production Polish (`e9f869b`)
- **AI Engine Revision:** Dynamic Question Bank, Non-Repeating Engine & Semantic Evaluator (`8f5ba4f`)
