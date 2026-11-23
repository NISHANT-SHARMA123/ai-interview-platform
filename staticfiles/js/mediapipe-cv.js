/**
 * AI Mock Interview Platform - Client-Side Computer Vision Engine
 * Features:
 * - Real MediaPipe FaceLandmarker (468-point 3D facial landmarks) via @mediapipe/tasks-vision
 * - Frame-differencing motion & face-centroid fallback when offline or before WASM loads
 * - 10-Second Neutral Posture & Gaze Baseline Calibration
 * - Zero Video Upload Architecture: Raw video frames execute in-browser only
 * - Real-time Slouching, Head Down, Looking Away, Leaning, Fidgeting & Out-of-Frame detection
 */

let sharedFaceLandmarker = null;
let landmarkerInitPromise = null;

async function getFaceLandmarker() {
  if (sharedFaceLandmarker) return sharedFaceLandmarker;
  if (landmarkerInitPromise) return landmarkerInitPromise;

  landmarkerInitPromise = (async () => {
    try {
      const vision = await import('https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/+esm');
      const filesetResolver = await vision.FilesetResolver.forVisionTasks(
        'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm'
      );
      sharedFaceLandmarker = await vision.FaceLandmarker.createFromOptions(filesetResolver, {
        baseOptions: {
          modelAssetPath:
            'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task',
          delegate: 'GPU'
        },
        outputFaceBlendshapes: false,
        runningMode: 'VIDEO',
        numFaces: 1
      });
      return sharedFaceLandmarker;
    } catch (err) {
      console.warn('MediaPipe FaceLandmarker unavailable, using motion+centroid fallback:', err);
      return null;
    }
  })();

  return landmarkerInitPromise;
}

export class PostureBaselineCalibrator {
  constructor(config) {
    this.videoEl = config.videoEl;
    this.saveEndpoint = config.saveEndpoint;
    this.csrfToken = config.csrfToken;
    this.onProgress = config.onProgress || null; // (secondsRemaining, percent)
    this.onComplete = config.onComplete || null; // (baselineData)

    this.durationSeconds = 10;
    this.samples = [];
    this.timerId = null;
    this.sampleIntervalId = null;
    this.isCalibrating = false;
    this.landmarker = null;
    this.lastVideoTime = -1;

    // Offscreen canvas for fallback sampling
    this.canvas = document.createElement('canvas');
    this.canvas.width = 160;
    this.canvas.height = 120;
    this.ctx = this.canvas.getContext('2d', { willReadFrequently: true });
  }

  async start() {
    this.samples = [];
    this.isCalibrating = true;
    this.landmarker = await getFaceLandmarker();

    let elapsedMs = 0;
    const totalMs = this.durationSeconds * 1000;

    // Sample video frame every 120ms
    this.sampleIntervalId = setInterval(() => {
      this.captureCalibrationSample();
    }, 120);

    const startTime = Date.now();
    this.timerId = setInterval(() => {
      elapsedMs = Date.now() - startTime;
      const remainingSecs = Math.max(0, Math.ceil((totalMs - elapsedMs) / 1000));
      const percent = Math.min(100, Math.round((elapsedMs / totalMs) * 100));

      if (this.onProgress) {
        this.onProgress(remainingSecs, percent);
      }

      if (elapsedMs >= totalMs) {
        this.finish();
      }
    }, 200);
  }

  captureCalibrationSample() {
    if (!this.videoEl || this.videoEl.readyState < 2) return;

    // Prefer MediaPipe FaceLandmarker
    if (this.landmarker && this.videoEl.currentTime !== this.lastVideoTime) {
      try {
        this.lastVideoTime = this.videoEl.currentTime;
        const result = this.landmarker.detectForVideo(this.videoEl, performance.now());
        if (result && result.faceLandmarks && result.faceLandmarks.length > 0) {
          const lm = result.faceLandmarks[0];
          const nose = lm[1];
          const leftEye = lm[33];
          const rightEye = lm[263];
          const chin = lm[152];
          const forehead = lm[10];

          const eyeMidX = (leftEye.x + rightEye.x) / 2;
          const eyeMidY = (leftEye.y + rightEye.y) / 2;
          const faceW = Math.abs(rightEye.x - leftEye.x);
          const faceH = Math.abs(chin.y - forehead.y);

          this.samples.push({
            cx: nose.x,
            cy: nose.y,
            scale: +(faceW * faceH).toFixed(4),
            yaw: (nose.x - eyeMidX) / Math.max(0.05, faceW),
            pitch: (nose.y - eyeMidY) / Math.max(0.05, faceH),
            gazeX: eyeMidX,
            gazeY: eyeMidY
          });
          return;
        }
      } catch (e) {
        // Fall through to canvas heuristic
      }
    }

    this.ctx.drawImage(this.videoEl, 0, 0, this.canvas.width, this.canvas.height);
    const frame = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
    const metrics = this.estimateFaceGeometry(frame);
    if (metrics) {
      this.samples.push(metrics);
    }
  }

  estimateFaceGeometry(imageData) {
    const data = imageData.data;
    const w = imageData.width;
    const h = imageData.height;

    let sumX = 0;
    let sumY = 0;
    let massCount = 0;
    let minX = w, maxX = 0, minY = h, maxY = 0;

    // Focus on central 70% of frame to reduce background noise
    for (let y = Math.floor(h * 0.12); y < Math.floor(h * 0.85); y += 3) {
      for (let x = Math.floor(w * 0.18); x < Math.floor(w * 0.82); x += 3) {
        const idx = (y * w + x) * 4;
        const r = data[idx];
        const g = data[idx + 1];
        const b = data[idx + 2];

        const isSkinLike = (r > 60 && g > 40 && b > 20 && (r - g) > 8 && r > b);
        if (isSkinLike) {
          sumX += x;
          sumY += y;
          massCount++;
          if (x < minX) minX = x;
          if (x > maxX) maxX = x;
          if (y < minY) minY = y;
          if (y > maxY) maxY = y;
        }
      }
    }

    if (massCount < 20) return null;

    const centerX = (sumX / massCount) / w;
    const centerY = (sumY / massCount) / h;
    const boxW = Math.max(0.1, (maxX - minX) / w);
    const boxH = Math.max(0.1, (maxY - minY) / h);

    return {
      cx: centerX,
      cy: centerY,
      scale: boxW * boxH,
      yaw: 0.0,
      pitch: 0.15,
      gazeX: centerX,
      gazeY: centerY - 0.04
    };
  }

  async finish() {
    clearInterval(this.timerId);
    clearInterval(this.sampleIntervalId);
    this.isCalibrating = false;

    const baseline = this.computeTrimmedBaseline();

    try {
      await fetch(this.saveEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.csrfToken
        },
        body: JSON.stringify(baseline)
      });
    } catch (e) {
      console.warn('Failed to persist calibration to backend:', e);
    }

    if (this.onComplete) {
      this.onComplete(baseline);
    }
  }

  computeTrimmedBaseline() {
    if (this.samples.length === 0) {
      return {
        face_center_x: 0.50,
        face_center_y: 0.45,
        face_scale: 0.12,
        shoulder_tilt: 0.0,
        gaze_origin_x: 0.50,
        gaze_origin_y: 0.40,
        baseline_yaw: 0.0,
        baseline_pitch: 0.15,
        calibrated_samples: 1
      };
    }

    const sorted = [...this.samples].sort((a, b) => a.cy - b.cy);
    const trimCount = Math.floor(sorted.length * 0.1);
    const valid = sorted.slice(trimCount, sorted.length - trimCount || sorted.length);

    let sumX = 0, sumY = 0, sumScale = 0, sumGazeX = 0, sumGazeY = 0, sumYaw = 0, sumPitch = 0;
    valid.forEach(s => {
      sumX += s.cx;
      sumY += s.cy;
      sumScale += s.scale;
      sumGazeX += s.gazeX;
      sumGazeY += s.gazeY;
      sumYaw += (s.yaw || 0);
      sumPitch += (s.pitch || 0.15);
    });

    const len = valid.length;
    return {
      face_center_x: +(sumX / len).toFixed(4),
      face_center_y: +(sumY / len).toFixed(4),
      face_scale: +(sumScale / len).toFixed(4),
      shoulder_tilt: 0.0,
      gaze_origin_x: +(sumGazeX / len).toFixed(4),
      gaze_origin_y: +(sumGazeY / len).toFixed(4),
      baseline_yaw: +(sumYaw / len).toFixed(4),
      baseline_pitch: +(sumPitch / len).toFixed(4),
      calibrated_samples: len
    };
  }
}


export class PostureGazeTracker {
  constructor(config) {
    this.videoEl = config.videoEl;
    this.telemetryEndpoint = config.telemetryEndpoint;
    this.csrfToken = config.csrfToken;
    this.baseline = config.baseline || {
      face_center_x: 0.50,
      face_center_y: 0.45,
      face_scale: 0.12,
      baseline_yaw: 0.0,
      baseline_pitch: 0.15
    };
    this.onStatusChange = config.onStatusChange || null; // (status, message, severity)

    this.isRunning = false;
    this.animFrameId = null;
    this.eventBuffer = [];
    this.flushIntervalId = null;
    this.landmarker = null;
    this.lastVideoTime = -1;

    // Temporal state tracking
    this.sessionStartTime = Date.now();
    this.activeEvents = {};
    this.historyBuffer = []; // Rolling window for fidgeting / rapid movement detection
    this.prevGrayFrame = null;

    // Offscreen sampling canvas
    this.canvas = document.createElement('canvas');
    this.canvas.width = 160;
    this.canvas.height = 120;
    this.ctx = this.canvas.getContext('2d', { willReadFrequently: true });
  }

  async start() {
    this.isRunning = true;
    this.sessionStartTime = Date.now();
    this.landmarker = await getFaceLandmarker();
    this.loop();

    // Flush buffered telemetry every 8 seconds
    this.flushIntervalId = setInterval(() => {
      this.flushTelemetry();
    }, 8000);
  }

  stop() {
    this.isRunning = false;
    if (this.animFrameId) cancelAnimationFrame(this.animFrameId);
    if (this.flushIntervalId) clearInterval(this.flushIntervalId);

    // Finalize any currently active events so tail-end movements are never lost
    const nowMs = Date.now() - this.sessionStartTime;
    Object.keys(this.activeEvents).forEach((eventType) => {
      this.handleTemporalCondition(eventType, false, nowMs);
    });

    this.flushTelemetry(true);
  }

  loop() {
    if (!this.isRunning) return;

    this.analyzeCurrentFrame();

    // Throttle to ~12fps (80ms interval)
    setTimeout(() => {
      if (this.isRunning) {
        this.animFrameId = requestAnimationFrame(() => this.loop());
      }
    }, 80);
  }

  analyzeCurrentFrame() {
    if (!this.videoEl || this.videoEl.readyState < 2) return;
    const nowMs = Date.now() - this.sessionStartTime;

    let currentGeometry = null;

    // 1. Try MediaPipe 468-point FaceLandmarker first
    if (this.landmarker && this.videoEl.currentTime !== this.lastVideoTime) {
      try {
        this.lastVideoTime = this.videoEl.currentTime;
        const result = this.landmarker.detectForVideo(this.videoEl, performance.now());
        if (result && result.faceLandmarks && result.faceLandmarks.length > 0) {
          const lm = result.faceLandmarks[0];
          const nose = lm[1];
          const leftEye = lm[33];
          const rightEye = lm[263];
          const chin = lm[152];
          const forehead = lm[10];

          const eyeMidX = (leftEye.x + rightEye.x) / 2;
          const eyeMidY = (leftEye.y + rightEye.y) / 2;
          const faceW = Math.abs(rightEye.x - leftEye.x);
          const faceH = Math.abs(chin.y - forehead.y);

          currentGeometry = {
            cx: nose.x,
            cy: nose.y,
            yaw: (nose.x - eyeMidX) / Math.max(0.05, faceW),
            pitch: (nose.y - eyeMidY) / Math.max(0.05, faceH),
            source: 'mediapipe'
          };
        } else {
          // MediaPipe ran and confirmed no face in frame
          currentGeometry = null;
        }
      } catch (e) {
        currentGeometry = this.extractFallbackGeometry();
      }
    } else if (!this.landmarker) {
      currentGeometry = this.extractFallbackGeometry();
    } else {
      return; // Same video frame
    }

    if (!currentGeometry) {
      this.handleTemporalCondition('out_of_frame', true, nowMs, 'medium', { reason: 'Face not detected in frame' });
      if (this.onStatusChange) {
        this.onStatusChange('out_of_frame', 'Keep your face inside camera frame', 'high');
      }
      return;
    }

    this.handleTemporalCondition('out_of_frame', false, nowMs);

    // Adaptive baseline: if user never ran calibration, lock first detected frame as neutral baseline
    if (!this.baseline || this.baseline.calibrated_samples === undefined) {
      this.baseline = {
        face_center_x: currentGeometry.cx,
        face_center_y: currentGeometry.cy,
        baseline_yaw: currentGeometry.yaw || 0.0,
        baseline_pitch: currentGeometry.pitch || 0.15,
        calibrated_samples: 1
      };
    }

    const deltaY = currentGeometry.cy - this.baseline.face_center_y;
    const deltaX = Math.abs(currentGeometry.cx - this.baseline.face_center_x);
    const deltaYaw = Math.abs((currentGeometry.yaw || 0) - (this.baseline.baseline_yaw || 0));
    const deltaPitch = (currentGeometry.pitch || 0.15) - (this.baseline.baseline_pitch || 0.15);

    // 1. Slouching detection (Vertical drop > 6% below baseline)
    const isSlouching = deltaY > 0.065;
    const slouchSeverity = deltaY > 0.16 ? 'high' : (deltaY > 0.10 ? 'medium' : 'low');
    this.handleTemporalCondition('slouching', isSlouching, nowMs, slouchSeverity, { delta_y: +deltaY.toFixed(3) });

    // 2. Head down detection (Pitch drop > 0.12)
    const isHeadDown = deltaPitch > 0.12;
    this.handleTemporalCondition('head_down', isHeadDown, nowMs, deltaPitch > 0.20 ? 'high' : 'medium', { delta_pitch: +deltaPitch.toFixed(3) });

    // 3. Gaze / Looking away detection (Head turn yaw > 0.20 OR horizontal shift > 0.09)
    const isLookingAway = deltaYaw > 0.20 || deltaX > 0.09;
    const gazeSeverity = (deltaYaw > 0.35 || deltaX > 0.18) ? 'high' : 'medium';
    this.handleTemporalCondition('looking_away', isLookingAway, nowMs, gazeSeverity, { delta_x: +deltaX.toFixed(3), delta_yaw: +deltaYaw.toFixed(3) });

    // 4. Excessive leaning (Lateral shift 5.5% - 9%)
    const isLeaning = deltaX > 0.055 && !isLookingAway;
    this.handleTemporalCondition('leaning', isLeaning, nowMs, 'low', { delta_x: +deltaX.toFixed(3) });

    // 5. Rapid movement / Fidgeting detection via rolling 1.5s motion path
    this.historyBuffer.push({ t: nowMs, x: currentGeometry.cx, y: currentGeometry.cy });
    this.historyBuffer = this.historyBuffer.filter(p => nowMs - p.t <= 1500);
    let pathDistance = 0;
    for (let i = 1; i < this.historyBuffer.length; i++) {
      const dx = this.historyBuffer[i].x - this.historyBuffer[i - 1].x;
      const dy = this.historyBuffer[i].y - this.historyBuffer[i - 1].y;
      pathDistance += Math.hypot(dx, dy);
    }
    const isFidgeting = this.historyBuffer.length >= 6 && pathDistance > 0.18;
    this.handleTemporalCondition('fidgeting', isFidgeting, nowMs, pathDistance > 0.32 ? 'high' : 'medium', { motion_path: +pathDistance.toFixed(3) });

    // 6. Live HUD feedback
    if (this.onStatusChange) {
      if (isSlouching) {
        this.onStatusChange('slouching', 'Slouching detected: Sit upright', slouchSeverity);
      } else if (isHeadDown) {
        this.onStatusChange('head_down', 'Head tilted down: Look toward camera', 'medium');
      } else if (isLookingAway) {
        this.onStatusChange('looking_away', 'Head turned / Looking away from camera', gazeSeverity);
      } else if (isFidgeting) {
        this.onStatusChange('fidgeting', 'Rapid movement detected: Stay steady', 'medium');
      } else if (isLeaning) {
        this.onStatusChange('leaning', 'Leaning off-center: Re-align with camera', 'low');
      } else {
        this.onStatusChange('good', 'Neutral Posture & Alignment Solid', 'low');
      }
    }
  }

  extractFallbackGeometry() {
    this.ctx.drawImage(this.videoEl, 0, 0, this.canvas.width, this.canvas.height);
    const frame = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
    const data = frame.data;
    const w = frame.width;
    const h = frame.height;

    let sumX = 0, sumY = 0, count = 0;
    let motionX = 0, motionY = 0, motionCount = 0;
    const gray = new Uint8Array(w * h);

    for (let y = Math.floor(h * 0.10); y < Math.floor(h * 0.88); y += 3) {
      for (let x = Math.floor(w * 0.15); x < Math.floor(w * 0.85); x += 3) {
        const pIdx = y * w + x;
        const idx = pIdx * 4;
        const r = data[idx];
        const g = data[idx + 1];
        const b = data[idx + 2];
        const luma = (0.299 * r + 0.587 * g + 0.114 * b) | 0;
        gray[pIdx] = luma;

        if (this.prevGrayFrame) {
          if (Math.abs(luma - this.prevGrayFrame[pIdx]) > 18) {
            motionX += x;
            motionY += y;
            motionCount++;
          }
        }

        if (r > 60 && g > 40 && b > 20 && (r - g) > 8 && r > b) {
          sumX += x;
          sumY += y;
          count++;
        }
      }
    }

    this.prevGrayFrame = gray;

    if (count < 15 && motionCount < 15) return null;

    // Blend skin-centroid with active motion centroid when significant motion occurs
    const cx = motionCount > 25 ? (motionX / motionCount) / w : (sumX / Math.max(1, count)) / w;
    const cy = motionCount > 25 ? (motionY / motionCount) / h : (sumY / Math.max(1, count)) / h;

    return {
      cx,
      cy,
      yaw: 0.0,
      pitch: 0.15,
      source: 'fallback'
    };
  }

  handleTemporalCondition(eventType, isActive, nowMs, severity = 'low', details = {}) {
    const minSustainedDurationMs = 800; // Record movements sustained for >= 0.8s

    if (isActive) {
      if (!this.activeEvents[eventType]) {
        this.activeEvents[eventType] = {
          startMs: nowMs,
          severity: severity,
          details: details
        };
      } else if (severity === 'high') {
        this.activeEvents[eventType].severity = 'high';
      }
    } else if (this.activeEvents[eventType]) {
      const duration = nowMs - this.activeEvents[eventType].startMs;
      if (duration >= minSustainedDurationMs) {
        this.eventBuffer.push({
          event_type: eventType,
          severity: this.activeEvents[eventType].severity,
          start_offset_ms: this.activeEvents[eventType].startMs,
          end_offset_ms: nowMs,
          details: { ...this.activeEvents[eventType].details, duration_ms: duration }
        });
      }
      delete this.activeEvents[eventType];
    }
  }

  async flushTelemetry(useKeepalive = false) {
    if (this.eventBuffer.length === 0) return;

    const payload = { events: [...this.eventBuffer] };
    this.eventBuffer = [];

    try {
      await fetch(this.telemetryEndpoint, {
        method: 'POST',
        keepalive: useKeepalive,
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.csrfToken
        },
        body: JSON.stringify(payload)
      });
    } catch (e) {
      console.warn('Telemetry flush warning:', e);
      this.eventBuffer.push(...payload.events);
    }
  }
}
