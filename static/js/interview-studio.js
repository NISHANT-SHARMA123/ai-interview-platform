/**
 * AI Mock Interview Platform - Live Interview Studio & Conversational Engine
 * In-browser Web Speech API (STT & TTS), Dynamic Follow-up Probing, and Zero Video Upload.
 */

export class PersonaSpeechSynthesizer {
  constructor(personaType = 'tech_lead', onSpeakingChange = null) {
    this.personaType = personaType;
    this.onSpeakingChange = onSpeakingChange;
    this.isMuted = false;
    this.synth = window.speechSynthesis;
    this.voices = [];

    if (this.synth) {
      this.loadVoices();
      if (speechSynthesis.onvoiceschanged !== undefined) {
        speechSynthesis.onvoiceschanged = () => this.loadVoices();
      }
    }
  }

  loadVoices() {
    this.voices = this.synth.getVoices();
  }

  getPersonaVoiceProfile() {
    // Select best matching English voice
    let preferredVoice = this.voices.find(v => 
      v.lang.startsWith('en') && (v.name.includes('Google') || v.name.includes('Natural') || v.name.includes('Online'))
    ) || this.voices.find(v => v.lang.startsWith('en')) || null;

    let pitch = 1.0;
    let rate = 1.0;

    switch (this.personaType) {
      case 'friendly':
        pitch = 1.06;
        rate = 0.95;
        break;
      case 'bar_raiser':
        pitch = 0.92;
        rate = 1.02;
        break;
      case 'hr_manager':
        pitch = 1.08;
        rate = 1.0;
        break;
      case 'tech_lead':
      default:
        pitch = 0.98;
        rate = 1.02;
        break;
    }

    return { voice: preferredVoice, pitch, rate };
  }

  speak(text, onComplete = null) {
    if (!this.synth || this.isMuted) {
      if (onComplete) onComplete();
      return;
    }

    // Cancel any active utterance
    this.synth.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    const profile = this.getPersonaVoiceProfile();

    if (profile.voice) utterance.voice = profile.voice;
    utterance.pitch = profile.pitch;
    utterance.rate = profile.rate;

    utterance.onstart = () => {
      if (this.onSpeakingChange) this.onSpeakingChange(true);
    };

    utterance.onend = () => {
      if (this.onSpeakingChange) this.onSpeakingChange(false);
      if (onComplete) onComplete();
    };

    utterance.onerror = (e) => {
      console.warn("Speech synthesis error:", e);
      if (this.onSpeakingChange) this.onSpeakingChange(false);
      if (onComplete) onComplete();
    };

    this.synth.speak(utterance);
  }

  cancel() {
    if (this.synth) {
      this.synth.cancel();
      if (this.onSpeakingChange) this.onSpeakingChange(false);
    }
  }

  toggleMute() {
    this.isMuted = !this.isMuted;
    if (this.isMuted) this.cancel();
    return this.isMuted;
  }
}


export class CandidateSpeechRecognizer {
  constructor(onTranscriptUpdate = null, onStateChange = null) {
    this.onTranscriptUpdate = onTranscriptUpdate;
    this.onStateChange = onStateChange;
    this.isListening = false;
    this.finalTranscript = '';
    this.interimTranscript = '';

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    this.isSupported = !!SpeechRecognition;

    if (this.isSupported) {
      this.recognition = new SpeechRecognition();
      this.recognition.continuous = true;
      this.recognition.interimResults = true;
      this.recognition.lang = 'en-US';

      this.recognition.onstart = () => {
        this.isListening = true;
        if (this.onStateChange) this.onStateChange(true);
      };

      this.recognition.onresult = (event) => {
        let interim = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            this.finalTranscript += event.results[i][0].transcript + ' ';
          } else {
            interim += event.results[i][0].transcript;
          }
        }
        this.interimTranscript = interim;
        const fullText = (this.finalTranscript + interim).trim();
        if (this.onTranscriptUpdate) this.onTranscriptUpdate(fullText);
      };

      this.recognition.onerror = (event) => {
        console.warn("Speech recognition notice:", event.error);
        if (event.error === 'not-allowed') {
          this.isListening = false;
          if (this.onStateChange) this.onStateChange(false, 'Mic permission not granted. Use typed fallback.');
        }
      };

      this.recognition.onend = () => {
        // If candidate didn't explicitly finish, auto-restart continuous listening
        if (this.isListening) {
          try {
            this.recognition.start();
          } catch (e) {
            this.isListening = false;
            if (this.onStateChange) this.onStateChange(false);
          }
        } else {
          if (this.onStateChange) this.onStateChange(false);
        }
      };
    }
  }

  start() {
    if (!this.isSupported) return false;
    this.finalTranscript = '';
    this.interimTranscript = '';
    this.isListening = true;
    try {
      this.recognition.start();
      return true;
    } catch (e) {
      console.warn("Recognition start failed or already active:", e);
      return false;
    }
  }

  stop() {
    this.isListening = false;
    if (this.recognition) {
      try {
        this.recognition.stop();
      } catch (e) {
        // no-op
      }
    }
    return (this.finalTranscript + this.interimTranscript).trim();
  }

  reset() {
    this.finalTranscript = '';
    this.interimTranscript = '';
  }
}


export class InterviewStudioEngine {
  constructor(config) {
    this.interviewId = config.interviewId;
    this.persona = config.persona || 'tech_lead';
    this.personaDisplay = config.personaDisplay || 'Technical Lead';
    this.csrfToken = config.csrfToken;
    this.startEndpoint = config.startEndpoint;
    this.answerEndpoint = config.answerEndpoint;
    this.hintEndpoint = config.hintEndpoint || null;
    this.isAnxietyFree = !!config.isAnxietyFree;
    this.stateEndpoint = config.stateEndpoint;
    this.dashboardUrl = config.dashboardUrl;
    this.onCompleted = config.onCompleted || null;

    // UI Element References
    this.questionTextEl = document.getElementById('studio-question-text');
    this.questionOrderEl = document.getElementById('studio-question-order');
    this.questionCategoryEl = document.getElementById('studio-question-category');
    this.followUpBadgeEl = document.getElementById('studio-followup-badge');
    this.transcriptInputEl = document.getElementById('studio-transcript-input');
    this.wordCountEl = document.getElementById('studio-word-count');
    this.timerEl = document.getElementById('studio-timer-display');
    this.micToggleBtn = document.getElementById('studio-mic-toggle-btn');
    this.submitBtn = document.getElementById('studio-submit-answer-btn');
    this.repeatBtn = document.getElementById('studio-repeat-question-btn');
    this.hintBtn = document.getElementById('studio-hint-btn');
    this.hintBoxEl = document.getElementById('studio-hint-box');
    this.muteBtn = document.getElementById('studio-mute-voice-btn');
    this.personaStatusEl = document.getElementById('studio-persona-status');
    this.personaAvatarEl = document.getElementById('studio-persona-avatar');
    this.feedbackToastEl = document.getElementById('studio-feedback-toast');
    this.completionModalEl = document.getElementById('studio-completion-modal');
    this.inputModeBtn = document.getElementById('studio-switch-input-mode-btn');

    // State Variables
    this.currentQuestion = null;
    this.isAnswering = false;
    this.isTypedMode = false;
    this.startTime = null;
    this.timerInterval = null;
    this.elapsedSeconds = 0;

    // Subsystems
    this.tts = new PersonaSpeechSynthesizer(this.persona, (isSpeaking) => {
      this.updatePersonaSpeakingState(isSpeaking);
    });

    this.stt = new CandidateSpeechRecognizer(
      (transcript) => {
        this.transcriptInputEl.value = transcript;
        this.updateWordCount(transcript);
      },
      (isListening, errorMsg) => {
        this.updateMicUIState(isListening, errorMsg);
      }
    );

    this.bindEvents();
  }

  init() {
    this.startSession();
  }

  bindEvents() {
    // Mic Toggle Button
    if (this.micToggleBtn) {
      this.micToggleBtn.addEventListener('click', () => {
        if (!this.isAnswering) {
          this.beginAnswer();
        } else {
          this.finishAndSubmitAnswer();
        }
      });
    }

    // Submit Button
    if (this.submitBtn) {
      this.submitBtn.addEventListener('click', () => {
        this.finishAndSubmitAnswer();
      });
    }

    // Socratic Hint Lifeline
    if (this.hintBtn) {
      this.hintBtn.addEventListener('click', () => this.requestHint());
    }

    // Repeat Question (TTS)
    if (this.repeatBtn) {
      this.repeatBtn.addEventListener('click', () => {
        if (this.currentQuestion) {
          this.tts.speak(this.currentQuestion.question_text);
        }
      });
    }

    // Mute AI Voice Toggle
    if (this.muteBtn) {
      this.muteBtn.addEventListener('click', () => {
        const muted = this.tts.toggleMute();
        this.muteBtn.innerHTML = muted 
          ? `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="1" y1="1" x2="23" y2="23"></line><path d="M9 9v3a3 3 0 0 0 5.12 2.12M15 9.34V4a3 3 0 0 0-5.94-.6"></path><path d="M17 16.95A7 7 0 0 1 5 12v-2m14 0v2a7 7 0 0 1-.11 1.23"></path></svg> Voice Muted`
          : `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path></svg> AI Voice On`;
      });
    }

    // Input mode switch (Spoken vs Typed)
    if (this.inputModeBtn) {
      this.inputModeBtn.addEventListener('click', () => {
        this.isTypedMode = !this.isTypedMode;
        if (this.isTypedMode) {
          this.stt.stop();
          this.inputModeBtn.textContent = "Switch to Spoken Mode (Mic)";
          this.transcriptInputEl.placeholder = "Type your comprehensive answer here...";
          this.transcriptInputEl.focus();
        } else {
          this.inputModeBtn.textContent = "Switch to Typed Fallback";
          this.transcriptInputEl.placeholder = "Click 'Start Answering' or speak. Your live transcript appears here...";
        }
      });
    }

    // Manual typing input tracking
    if (this.transcriptInputEl) {
      this.transcriptInputEl.addEventListener('input', () => {
        this.updateWordCount(this.transcriptInputEl.value);
      });
    }
  }

  async startSession() {
    this.setPersonaStatus("Preparing tailored interview questions...", "status-busy");

    try {
      const response = await fetch(this.startEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.csrfToken
        }
      });

      const data = await response.json();
      if (data.status === 'ok') {
        this.renderQuestion(data.question);
      } else {
        alert("Failed to initialize interview questions: " + (data.message || "Unknown error"));
      }
    } catch (e) {
      console.error("Session start error:", e);
      this.setPersonaStatus("Network connection error.", "status-error");
    }
  }

  renderQuestion(question) {
    this.currentQuestion = question;
    this.transcriptInputEl.value = '';
    this.stt.reset();
    this.updateWordCount('');
    this.resetTimer();

    if (this.hintBoxEl) { this.hintBoxEl.style.display = 'none'; this.hintBoxEl.textContent = ''; }
    if (this.questionTextEl) this.questionTextEl.textContent = question.question_text;
    if (this.questionOrderEl) this.questionOrderEl.textContent = `Question ${question.order} of ${question.total_questions || 5}`;
    if (this.questionCategoryEl) this.questionCategoryEl.textContent = question.category_display || question.category;

    if (this.followUpBadgeEl) {
      this.followUpBadgeEl.style.display = question.is_follow_up ? 'inline-flex' : 'none';
    }

    // Speak the question through TTS
    this.tts.speak(question.question_text, () => {
      this.setPersonaStatus("Awaiting your answer...", "status-ready");
    });
  }

  beginAnswer() {
    this.isAnswering = true;
    this.startTimer();
    this.setPersonaStatus("Listening attentively...", "status-listening");

    if (this.micToggleBtn) {
      this.micToggleBtn.innerHTML = `
        <span class="recording-pulse-dot"></span>
        <span>⏹️ Submit Answer</span>
      `;
      this.micToggleBtn.classList.add('btn-recording-active');
    }

    if (!this.isTypedMode && this.stt.isSupported) {
      this.stt.start();
    } else {
      this.transcriptInputEl.focus();
    }
  }

  async finishAndSubmitAnswer() {
    this.isAnswering = false;
    this.stopTimer();
    this.stt.stop();

    const answerText = this.transcriptInputEl.value.trim();
    if (!answerText) {
      alert("Please provide an answer (speak or type) before submitting.");
      return;
    }

    // Set UI to evaluating
    this.setPersonaStatus("Analyzing response & technical depth...", "status-evaluating");
    if (this.micToggleBtn) {
      this.micToggleBtn.disabled = true;
      this.micToggleBtn.innerHTML = `<span>⏳ Evaluating...</span>`;
    }
    if (this.submitBtn) this.submitBtn.disabled = true;

    try {
      const payload = {
        question_id: this.currentQuestion.id,
        transcript_text: answerText,
        duration_seconds: this.elapsedSeconds,
        input_method: this.isTypedMode ? 'typed' : 'spoken'
      };

      const response = await fetch(this.answerEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.csrfToken
        },
        body: JSON.stringify(payload)
      });

      const result = await response.json();

      if (result.status === 'ok') {
        this.showFeedbackToast(result.score, result.evaluation_summary, result.is_anxiety_free);

        if (result.is_completed) {
          this.handleInterviewCompleted(result.overall_score);
        } else if (result.has_follow_up && result.next_question) {
          setTimeout(() => {
            this.tts.speak("Thank you. Let's follow up on your answer.", () => {
              this.renderQuestion(result.next_question);
              this.resetControls();
            });
          }, 1200);
        } else if (result.next_question) {
          setTimeout(() => {
            this.renderQuestion(result.next_question);
            this.resetControls();
          }, 1200);
        }
      } else {
        alert("Failed to submit answer: " + (result.message || "Unknown error"));
        this.resetControls();
      }
    } catch (e) {
      console.error("Answer submission error:", e);
      alert("Connection error while submitting answer.");
      this.resetControls();
    }
  }


  async requestHint() {
    if (!this.currentQuestion || !this.hintEndpoint) return;
    if (this.hintBtn) { this.hintBtn.disabled = true; this.hintBtn.textContent = "💡 Thinking..."; }
    try {
      const resp = await fetch(this.hintEndpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": this.csrfToken
        },
        body: JSON.stringify({
          question_id: this.currentQuestion.id,
          partial_answer: this.transcriptInputEl ? this.transcriptInputEl.value : ""
        })
      });
      const data = await resp.json();
      if (data.status === "ok" && this.hintBoxEl) {
        this.hintBoxEl.innerHTML = `<strong>Coach Hint:</strong> ${data.hint}`;
        this.hintBoxEl.style.display = "block";
      }
    } catch (e) {
      console.warn("Hint request error:", e);
    } finally {
      if (this.hintBtn) { this.hintBtn.disabled = false; this.hintBtn.textContent = "💡 Need a Hint?"; }
    }
  }

  resetControls() {
    if (this.micToggleBtn) {
      this.micToggleBtn.disabled = false;
      this.micToggleBtn.classList.remove('btn-recording-active');
      this.micToggleBtn.innerHTML = `
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path><line x1="12" y1="19" x2="12" y2="22"></line></svg>
        <span>🎙️ Start Answering</span>
      `;
    }
    if (this.submitBtn) this.submitBtn.disabled = false;
  }

  handleInterviewCompleted(overallScore) {
    if (this.onCompleted) { try { this.onCompleted(); } catch (e) {} }
    this.setPersonaStatus("Interview session completed!", "status-ready");
    if (this.completionModalEl) {
      this.completionModalEl.classList.add('is-active');
      this.completionModalEl.style.display = 'flex';
    }
    const scoreTextEl = document.getElementById('studio-completion-score');
    if (scoreTextEl) {
      scoreTextEl.textContent = this.isAnxietyFree ? "Practice Complete" : (overallScore ? `${overallScore}%` : "--%");
    }
  }

  showFeedbackToast(score, summary, isAnxietyFree = false) {
    if (!this.feedbackToastEl) return;
    this.feedbackToastEl.innerHTML = `
      <div style="display: flex; align-items: center; justify-content: space-between; gap: 1rem;">
        <div>
          <strong style="color: var(--brand-cyan); font-size: 0.95rem;">${isAnxietyFree || this.isAnxietyFree ? 'Coaching Feedback (Anxiety-Free)' : `Answer Evaluated: ${score}%`}</strong>
          <div style="font-size: 0.8rem; color: var(--text-secondary); margin-top: 0.2rem;">${summary}</div>
        </div>
      </div>
    `;
    this.feedbackToastEl.style.display = 'block';
    setTimeout(() => {
      this.feedbackToastEl.style.display = 'none';
    }, 4500);
  }

  updatePersonaSpeakingState(isSpeaking) {
    if (this.personaAvatarEl) {
      if (isSpeaking) {
        this.personaAvatarEl.classList.add('is-speaking-waveform');
        this.setPersonaStatus("Speaking question out loud...", "status-speaking");
      } else {
        this.personaAvatarEl.classList.remove('is-speaking-waveform');
        if (!this.isAnswering) {
          this.setPersonaStatus("Listening to your answer...", "status-ready");
        }
      }
    }
  }

  setPersonaStatus(text, statusClass = "") {
    if (this.personaStatusEl) {
      this.personaStatusEl.textContent = text;
      this.personaStatusEl.className = `persona-status-pill ${statusClass}`;
    }
  }

  updateMicUIState(isListening, errorMsg = null) {
    if (errorMsg) {
      this.setPersonaStatus(errorMsg, "status-error");
    }
  }

  updateWordCount(text) {
    if (!this.wordCountEl) return;
    const words = text.trim() ? text.trim().split(/\s+/).length : 0;
    this.wordCountEl.textContent = `${words} word${words === 1 ? '' : 's'}`;
  }

  startTimer() {
    this.startTime = Date.now() - (this.elapsedSeconds * 1000);
    this.timerInterval = setInterval(() => {
      this.elapsedSeconds = Math.floor((Date.now() - this.startTime) / 1000);
      const mins = String(Math.floor(this.elapsedSeconds / 60)).padStart(2, '0');
      const secs = String(this.elapsedSeconds % 60).padStart(2, '0');
      if (this.timerEl) this.timerEl.textContent = `${mins}:${secs}`;
    }, 1000);
  }

  stopTimer() {
    if (this.timerInterval) {
      clearInterval(this.timerInterval);
      this.timerInterval = null;
    }
  }

  resetTimer() {
    this.stopTimer();
    this.elapsedSeconds = 0;
    if (this.timerEl) this.timerEl.textContent = "00:00";
  }
}

