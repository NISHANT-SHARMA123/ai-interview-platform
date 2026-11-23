/**
 * AI Mock Interview Platform - Zero-Dependency Canvas Radar & Trend Charts
 * High-performance, retina-scaled 2D rendering for candidate skill breakdowns.
 */

export class MultimodalRadarChart {
  constructor(canvasId, metricsData) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) return;

    this.ctx = this.canvas.getContext('2d');
    this.labels = metricsData.labels || ["Technical", "Posture", "Gaze", "Speech", "STAR"];
    this.values = metricsData.values || [75, 80, 85, 80, 85];
    this.maxValue = 100;
    this.numAxes = this.labels.length;

    this.init();
  }

  init() {
    this.resize();
    window.addEventListener('resize', () => {
      this.resize();
      this.draw();
    }, { passive: true });
    this.draw();
  }

  resize() {
    const rect = this.canvas.parentElement.getBoundingClientRect();
    const size = Math.min(rect.width, 360);
    this.canvas.width = size * window.devicePixelRatio;
    this.canvas.height = size * window.devicePixelRatio;
    this.canvas.style.width = `${size}px`;
    this.canvas.style.height = `${size}px`;
    this.ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
    this.width = size;
    this.height = size;
    this.centerX = size / 2;
    this.centerY = size / 2;
    this.radius = size * 0.36;
  }

  draw() {
    this.ctx.clearRect(0, 0, this.width, this.height);

    // 1. Draw web grid rings (20%, 40%, 60%, 80%, 100%)
    const rings = 5;
    for (let r = 1; r <= rings; r++) {
      const ringRadius = (this.radius / rings) * r;
      this.ctx.beginPath();
      for (let i = 0; i < this.numAxes; i++) {
        const angle = (Math.PI * 2 / this.numAxes) * i - Math.PI / 2;
        const x = this.centerX + Math.cos(angle) * ringRadius;
        const y = this.centerY + Math.sin(angle) * ringRadius;
        if (i === 0) this.ctx.moveTo(x, y);
        else this.ctx.lineTo(x, y);
      }
      this.ctx.closePath();
      this.ctx.strokeStyle = r === rings ? 'rgba(255, 255, 255, 0.15)' : 'rgba(255, 255, 255, 0.06)';
      this.ctx.lineWidth = 1;
      this.ctx.stroke();
    }

    // 2. Draw axis lines & text labels
    this.ctx.font = '500 11px Outfit, sans-serif';
    this.ctx.textAlign = 'center';
    this.ctx.textBaseline = 'middle';

    for (let i = 0; i < this.numAxes; i++) {
      const angle = (Math.PI * 2 / this.numAxes) * i - Math.PI / 2;
      const x = this.centerX + Math.cos(angle) * this.radius;
      const y = this.centerY + Math.sin(angle) * this.radius;

      // Axis line
      this.ctx.beginPath();
      this.ctx.moveTo(this.centerX, this.centerY);
      this.ctx.lineTo(x, y);
      this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
      this.ctx.stroke();

      // Label text
      const labelDist = this.radius + 24;
      const lx = this.centerX + Math.cos(angle) * labelDist;
      const ly = this.centerY + Math.sin(angle) * labelDist;
      this.ctx.fillStyle = '#94a3b8';
      this.ctx.fillText(this.labels[i], lx, ly);
    }

    // 3. Draw score polygon
    const points = [];
    this.ctx.beginPath();
    for (let i = 0; i < this.numAxes; i++) {
      const val = Math.min(this.maxValue, Math.max(0, this.values[i]));
      const ratio = val / this.maxValue;
      const angle = (Math.PI * 2 / this.numAxes) * i - Math.PI / 2;
      const px = this.centerX + Math.cos(angle) * (this.radius * ratio);
      const py = this.centerY + Math.sin(angle) * (this.radius * ratio);
      points.push({ x: px, y: py, val: val });

      if (i === 0) this.ctx.moveTo(px, py);
      else this.ctx.lineTo(px, py);
    }
    this.ctx.closePath();

    // Polygon fill gradient
    const gradient = this.ctx.createRadialGradient(
      this.centerX, this.centerY, 10, 
      this.centerX, this.centerY, this.radius
    );
    gradient.addColorStop(0, 'rgba(6, 182, 212, 0.45)');
    gradient.addColorStop(1, 'rgba(139, 92, 246, 0.15)');
    this.ctx.fillStyle = gradient;
    this.ctx.fill();

    // Polygon stroke
    this.ctx.strokeStyle = '#06b6d4';
    this.ctx.lineWidth = 2.2;
    this.ctx.stroke();

    // 4. Draw vertex dots
    for (let i = 0; i < points.length; i++) {
      const pt = points[i];
      this.ctx.beginPath();
      this.ctx.arc(pt.x, pt.y, 4, 0, Math.PI * 2);
      this.ctx.fillStyle = '#38bdf8';
      this.ctx.fill();
      this.ctx.strokeStyle = '#ffffff';
      this.ctx.lineWidth = 1.5;
      this.ctx.stroke();
    }
  }
}
