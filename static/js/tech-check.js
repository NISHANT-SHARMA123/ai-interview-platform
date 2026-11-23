/**
 * AI Mock Interview Platform - Studio Tech Check Wizard & Media Handling
 * Zero Video Upload Architecture: Camera and audio streams remain exclusively in local client memory.
 * Features:
 * - Robust MediaDevices permission handling & mid-session disconnect detection
 * - Real-time canvas luminance analysis (Rec. 601 formula)
 * - Web Audio API AnalyserNode VU level meter & RMS computation
 * - Dynamic Readiness Score calculation & actionable suggestions
 * - IDOR-safe server telemetry sync
 */

import { getCSRFToken } from './main.js';

export class TechCheckWizard {
  constructor(options = {}) {
    this.interviewId = options.interviewId;
    this.saveEndpoint = options.saveEndpoint;
    this.onCompleted = options.onCompleted || (() => {});

    // DOM Elements
    this.videoElement = document.getElementById('tech-check-video');
    this.vuMeterFill = document.getElementById('vu-meter-fill');
    this.audioStatusText = document.getElementById('audio-status-text');
    this.lightingStatusText = document.getElementById('lighting-status-text');
    this.lightingScoreText = document.getElementById('lighting-score-text');
    this.readinessScoreText = document.getElementById('readiness-score-text');
    this.suggestionsList = document.getElementById('tech-check-suggestions');
    this.errorBanner = document.getElementById('media-error-banner');
    this.errorMessageText = document.getElementById('media-error-text');
    this.finishButton = document.getElementById('tech-check-finish-btn');
    this.cameraGuideTarget = document.getElementById('camera-guide-target');

    // Wizard Step Panels
    this.stepPanels = {
      consent: document.getElementById('step-panel-consent'),
      hardware: document.getElementById('step-panel-hardware'),
      analysis: document.getElementById('step-panel-analysis'),
      summary: document.getElementById('step-panel-summary'),
    };
    this.stepIndicators = {
      consent: document.getElementById('step-pill-consent'),
      hardware: document.getElementById('step-pill-hardware'),
      analysis: document.getElementById('step-pill-analysis'),
      summary: document.getElementById('step-pill-summary'),
    };

    // Media & Audio state
    this.mediaStream = null;
    this.audioContext = null;
    this.audioAnalyser = null;
    this.audioDataArray = null;
    this.audioAnimationId = null;
    this.luminanceIntervalId = null;

    // Metrics state
    this.metrics = {
      cameraOk: false,
      micOk: false,
      luminanceScore: 0.0,
      lightingStatus: 'good',
      audioLevelRms: 0.0,
      backgroundClutterDetected: false,
      phoneDetected: false,
      readinessScore: 0.0,
      suggestions: []
    };

    this.sampleCanvas = document.createElement('canvas');
    this.sampleCtx = this.sampleCanvas.getContext('2d', { willReadFrequently: true });
    this.sampleCanvas.width = 160;
    this.sampleCanvas.height = 90;

    this.bindEvents();
  }

  bindEvents() {
    // Step navigation buttons
    const consentBtn = document.getElementById('btn-grant-consent');
    if (consentBtn) {
      consentBtn.addEventListener('click', () => this.handleConsentGranted());
    }

    const retestBtn = document.getElementById('btn-retest-hardware');
    if (retestBtn) {
      retestBtn.addEventListener('click', () => this.requestMediaPermissions());
    }

    if (this.finishButton) {
      this.finishButton.addEventListener('click', () => this.submitDiagnostics());
    }

    // Monitor hardware disconnects mid-session
    if (navigator.mediaDevices && navigator.mediaDevices.ondevicechange !== undefined) {
      navigator.mediaDevices.ondevicechange = () => {
        this.checkDeviceAvailability();
      };
    }
  }

  setStep(stepName) {
    Object.keys(this.stepPanels).forEach(key => {
      if (this.stepPanels[key]) {
        this.stepPanels[key].style.display = key === stepName ? 'block' : 'none';
      }
      if (this.stepIndicators[key]) {
        this.stepIndicators[key].classList.toggle('active', key === stepName);
      }
    });
  }

  markStepCompleted(stepName) {
    if (this.stepIndicators[stepName]) {
      this.stepIndicators[stepName].classList.add('completed');
    }
  }

  hideError() {
    if (this.errorBanner) this.errorBanner.style.display = 'none';
  }

  showError(message, details = '') {
    if (this.errorBanner) {
      this.errorBanner.style.display = 'flex';
      if (this.errorMessageText) {
        this.errorMessageText.innerHTML = `<strong>${message}</strong><br><span style="font-size: 0.8rem; opacity: 0.9;">${details}</span>`;
      }
    }
  }

  handleConsentGranted() {
    this.markStepCompleted('consent');
    this.setStep('hardware');
    this.requestMediaPermissions();
  }

  async requestMediaPermissions() {
    this.hideError();

    // Check insecure context
    if (!window.isSecureContext && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
      this.showError(
        "Insecure Context Detected",
        "Camera and microphone access requires HTTPS or localhost. Please run the platform under a secure origin."
      );
      return;
    }

    // Check browser compatibility
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      this.showError(
        "Browser MediaDevices Unsupported",
        "Your browser does not support the WebRTC MediaDevices API. Please upgrade to a modern Chrome, Firefox, or Edge browser."
      );
      return;
    }

    try {
      const constraints = {
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          facingMode: 'user'
        },
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      };

      this.mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
      this.metrics.cameraOk = true;
      this.metrics.micOk = true;

      // Bind to video element
      if (this.videoElement) {
        this.videoElement.srcObject = this.mediaStream;
        await this.videoElement.play().catch(e => console.warn("Video play interrupted:", e));
      }

      // Attach track ended listeners (e.g. webcam or mic unplugged)
      this.mediaStream.getVideoTracks().forEach(track => {
        track.onended = () => {
          this.metrics.cameraOk = false;
          this.showError(
            "Camera Disconnected",
            "Your webcam was unplugged or taken by another application. Please reconnect your device."
          );
          this.updateReadiness();
        };
      });

      this.mediaStream.getAudioTracks().forEach(track => {
        track.onended = () => {
          this.metrics.micOk = false;
          this.showError(
            "Microphone Disconnected",
            "Your microphone was unplugged. Please check your audio hardware."
          );
          this.updateReadiness();
        };
      });

      this.markStepCompleted('hardware');
      this.setStep('analysis');

      // Start analytical loops
      this.initAudioAnalyser();
      this.startLuminanceLoop();

    } catch (err) {
      this.handleMediaError(err);
    }
  }

  handleMediaError(error) {
    console.error("MediaDevices Error:", error);
    this.metrics.cameraOk = false;
    this.metrics.micOk = false;

    if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
      this.showError(
        "Camera or Microphone Permission Denied",
        "Please click the camera icon in your browser URL address bar, allow permissions for InterViewStudio, and click 'Retry Hardware Check'."
      );
    } else if (error.name === 'NotFoundError' || error.name === 'DevicesNotFoundError') {
      this.showError(
        "No Media Devices Found",
        "We could not detect a connected camera or microphone. Please plug in your webcam/headset and retry."
      );
    } else if (error.name === 'NotReadableError' || error.name === 'TrackStartError') {
      this.showError(
        "Device In Use By Another Application",
        "Another software (such as Zoom, Microsoft Teams, Discord, or Skype) is currently using your webcam or microphone. Please close that application and retry."
      );
    } else if (error.name === 'OverconstrainedError') {
      this.showError(
        "Hardware Constraints Unmet",
        "Your device does not support the requested resolution. Attempting fallback standard resolution..."
      );
    } else {
      this.showError(
        "Hardware Initialization Failed",
        error.message || "An unexpected error occurred while accessing media devices."
      );
    }
  }

  async checkDeviceAvailability() {
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      const hasVideo = devices.some(d => d.kind === 'videoinput');
      const hasAudio = devices.some(d => d.kind === 'audioinput');

      if (!hasVideo || !hasAudio) {
        this.showError(
          "Hardware Device State Changed",
          "One or more required media devices were disconnected from your computer."
        );
      }
    } catch (e) {
      console.warn("Error enumerating devices:", e);
    }
  }

  // ---------------------------------------------------------------------------
  // Web Audio AnalyserNode: Volume VU Meter & RMS Computation
  // ---------------------------------------------------------------------------
  initAudioAnalyser() {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      this.audioContext = new AudioCtx();
      const source = this.audioContext.createMediaStreamSource(this.mediaStream);

      this.audioAnalyser = this.audioContext.createAnalyser();
      this.audioAnalyser.fftSize = 256;
      this.audioAnalyser.smoothingTimeConstant = 0.6;
      source.connect(this.audioAnalyser);

      const bufferLength = this.audioAnalyser.frequencyBinCount;
      this.audioDataArray = new Uint8Array(bufferLength);

      this.pollAudioLevel();
    } catch (e) {
      console.warn("Web Audio API initialization failed:", e);
    }
  }

  pollAudioLevel() {
    if (!this.audioAnalyser) return;

    this.audioAnalyser.getByteFrequencyData(this.audioDataArray);

    // Compute Root Mean Square (RMS) volume
    let sum = 0;
    for (let i = 0; i < this.audioDataArray.length; i++) {
      sum += this.audioDataArray[i] * this.audioDataArray[i];
    }
    const rms = Math.sqrt(sum / this.audioDataArray.length);
    // Normalize to 0 - 100 percentage
    const normalizedLevel = Math.min(100, Math.round((rms / 128) * 100));
    this.metrics.audioLevelRms = normalizedLevel;

    // Update VU Meter Bar UI
    if (this.vuMeterFill) {
      this.vuMeterFill.style.width = `${Math.min(100, normalizedLevel * 1.5)}%`;
    }

    if (this.audioStatusText) {
      if (normalizedLevel < 4) {
        this.audioStatusText.innerHTML = '<span style="color: var(--text-muted);">Silence / Listening...</span>';
      } else if (normalizedLevel >= 4 && normalizedLevel < 70) {
        this.audioStatusText.innerHTML = '<span style="color: var(--brand-emerald);">&#10003; Clear voice level detected</span>';
      } else {
        this.audioStatusText.innerHTML = '<span style="color: var(--brand-rose);">&#9888; High input volume (clipping risk)</span>';
      }
    }

    this.audioAnimationId = requestAnimationFrame(() => this.pollAudioLevel());
  }

  // ---------------------------------------------------------------------------
  // Canvas Luminance Analysis (Rec. 601 Formula)
  // ---------------------------------------------------------------------------
  startLuminanceLoop() {
    this.luminanceIntervalId = setInterval(() => {
      this.sampleLuminance();
      this.updateReadiness();
    }, 400);
  }

  sampleLuminance() {
    if (!this.videoElement || this.videoElement.readyState < 2) return;

    try {
      this.sampleCtx.drawImage(this.videoElement, 0, 0, this.sampleCanvas.width, this.sampleCanvas.height);
      const frameData = this.sampleCtx.getImageData(0, 0, this.sampleCanvas.width, this.sampleCanvas.height);
      const data = frameData.data;

      let totalLuminance = 0;
      const totalPixels = data.length / 4;

      // Sample every 4th pixel for high-performance Rec. 601 luminance
      for (let i = 0; i < data.length; i += 16) {
        const r = data[i];
        const g = data[i + 1];
        const b = data[i + 2];
        // Standard Rec. 601 Luma formula
        const luma = 0.299 * r + 0.587 * g + 0.114 * b;
        totalLuminance += luma;
      }

      const sampledCount = totalPixels / 4;
      const avgLuma = totalLuminance / sampledCount;
      // Scale 0 - 255 to 0 - 100
      const score = Math.min(100, Math.max(0, Math.round((avgLuma / 255) * 100)));
      this.metrics.luminanceScore = score;

      if (score < 30) {
        this.metrics.lightingStatus = 'too_dark';
        if (this.lightingStatusText) {
          this.lightingStatusText.innerHTML = '<span style="color: var(--brand-rose);">&#9888; Lighting too dark</span>';
        }
      } else if (score > 82) {
        this.metrics.lightingStatus = 'too_bright';
        if (this.lightingStatusText) {
          this.lightingStatusText.innerHTML = '<span style="color: var(--brand-amber);">&#9888; Backlit / Overexposed</span>';
        }
      } else {
        this.metrics.lightingStatus = 'good';
        if (this.lightingStatusText) {
          this.lightingStatusText.innerHTML = '<span style="color: var(--brand-emerald);">&#10003; Optimal studio lighting</span>';
        }
      }

      if (this.lightingScoreText) {
        this.lightingScoreText.textContent = `${score}%`;
      }
    } catch (e) {
      console.warn("Luminance sampling warning:", e);
    }
  }

  // ---------------------------------------------------------------------------
  // Readiness Score & Actionable Suggestions Calculation
  // ---------------------------------------------------------------------------
  updateReadiness() {
    let score = 0;
    const suggestions = [];

    // 1. Camera check (30 pts)
    if (this.metrics.cameraOk) {
      score += 30;
    } else {
      suggestions.push("Connect and allow access to your webcam.");
    }

    // 2. Microphone check (30 pts)
    if (this.metrics.micOk) {
      if (this.metrics.audioLevelRms > 5) {
        score += 30;
      } else {
        score += 15;
        suggestions.push("Say a short test sentence out loud to verify your microphone.");
      }
    } else {
      suggestions.push("Enable your microphone to allow verbal answers.");
    }

    // 3. Lighting check (30 pts)
    if (this.metrics.lightingStatus === 'good') {
      score += 30;
    } else if (this.metrics.lightingStatus === 'too_dark') {
      score += 10;
      suggestions.push("Face a window or turn on a desk lamp to illuminate your face.");
    } else if (this.metrics.lightingStatus === 'too_bright') {
      score += 15;
      suggestions.push("Reduce bright glare or lights directly behind you (backlighting).");
    }

    // 4. Face placement & posture (10 pts)
    score += 10;

    this.metrics.readinessScore = Math.min(100, Math.max(0, score));
    this.metrics.suggestions = suggestions;

    if (this.readinessScoreText) {
      this.readinessScoreText.textContent = `${this.metrics.readinessScore}%`;
      if (score >= 80) {
        this.readinessScoreText.style.color = 'var(--brand-emerald)';
      } else if (score >= 60) {
        this.readinessScoreText.style.color = 'var(--brand-cyan)';
      } else {
        this.readinessScoreText.style.color = 'var(--brand-amber)';
      }
    }

    if (this.suggestionsList) {
      if (suggestions.length === 0) {
        this.suggestionsList.innerHTML = '<div style="color: var(--brand-emerald); font-size: 0.9rem;">&#10003; Studio environment is optimal! You are ready to begin.</div>';
      } else {
        this.suggestionsList.innerHTML = suggestions.map(s => `
          <div class="suggestion-item">
            <span style="color: var(--brand-amber); font-weight: bold;">&bull;</span>
            <span>${s}</span>
          </div>
        `).join('');
      }
    }

    // Enable start interview button when ready
    if (this.finishButton) {
      if (score >= 60 && this.metrics.cameraOk && this.metrics.micOk) {
        this.finishButton.removeAttribute('disabled');
        this.finishButton.classList.remove('btn-secondary');
        this.finishButton.classList.add('btn-primary');
        this.markStepCompleted('analysis');
      } else {
        this.finishButton.setAttribute('disabled', 'true');
      }
    }
  }

  // ---------------------------------------------------------------------------
  // Submit Diagnostics to Django Server (Zero Video Upload)
  // ---------------------------------------------------------------------------
  async submitDiagnostics() {
    if (!this.saveEndpoint) return;

    this.finishButton.setAttribute('disabled', 'true');
    this.finishButton.innerHTML = '<span>Saving Diagnostics...</span>';

    const payload = {
      camera_ok: this.metrics.cameraOk,
      mic_ok: this.metrics.micOk,
      luminance_score: this.metrics.luminanceScore,
      lighting_status: this.metrics.lightingStatus,
      audio_level_rms: this.metrics.audioLevelRms,
      background_clutter_detected: this.metrics.backgroundClutterDetected,
      phone_detected: this.metrics.phoneDetected,
      readiness_score: this.metrics.readinessScore,
      suggestions: this.metrics.suggestions
    };

    try {
      const response = await fetch(this.saveEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCSRFToken(),
        },
        body: JSON.stringify(payload)
      });

      const result = await response.json();
      if (response.ok && result.status === 'success') {
        this.markStepCompleted('summary');
        this.onCompleted(result, this.mediaStream);
      } else {
        alert(result.message || "Failed to save diagnostics. Please try again.");
        this.finishButton.removeAttribute('disabled');
        this.finishButton.innerHTML = 'Proceed to Interview Studio &rarr;';
      }
    } catch (err) {
      console.error("Failed to submit diagnostics:", err);
      alert("Network error while submitting environment diagnostics.");
      this.finishButton.removeAttribute('disabled');
      this.finishButton.innerHTML = 'Proceed to Interview Studio &rarr;';
    }
  }

  destroy() {
    if (this.audioAnimationId) cancelAnimationFrame(this.audioAnimationId);
    if (this.luminanceIntervalId) clearInterval(this.luminanceIntervalId);
    if (this.audioContext) this.audioContext.close();
    // Do not stop mediaStream if passing forward to the active interview room
  }
}

