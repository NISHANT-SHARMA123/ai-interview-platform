/**
 * AI Mock Interview Platform - High-Performance 3D Ambient Canvas Background
 * Renders an interactive 3D neural constellation with real-time camera projection,
 * scroll-driven Z-axis warp, and cursor-reactive parallax depth.
 */

export class Ambient3DBackground {
  constructor(canvasId = 'bg-3d-canvas') {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) return;

    this.ctx = this.canvas.getContext('2d', { alpha: true });
    this.particles = [];
    this.numParticles = window.innerWidth < 768 ? 65 : 130;
    this.width = window.innerWidth;
    this.height = window.innerHeight;
    this.fov = 400; // Focal length for 3D perspective projection

    // 3D Camera / Scene coordinates
    this.camera = { x: 0, y: 0, z: 0, rotX: 0, rotY: 0 };
    this.targetCamera = { x: 0, y: 0, z: 0, rotX: 0, rotY: 0 };
    this.mouse = { x: 0, y: 0, targetX: 0, targetY: 0 };

    this.isReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    this.init();
  }

  init() {
    this.resize();
    window.addEventListener('resize', () => this.resize(), { passive: true });

    // Spawn particles in 3D cuboid space
    for (let i = 0; i < this.numParticles; i++) {
      this.particles.push({
        x: (Math.random() - 0.5) * 1600,
        y: (Math.random() - 0.5) * 1600,
        z: (Math.random() - 0.5) * 1200,
        baseSize: Math.random() * 2 + 1.2,
        vx: (Math.random() - 0.5) * 0.4,
        vy: (Math.random() - 0.5) * 0.4,
        vz: (Math.random() - 0.5) * 0.5,
        hue: Math.random() > 0.5 ? 190 : 265 // Cyan or Violet
      });
    }

    // Scroll listener: shifts camera Z and pitch based on scroll offset
    window.addEventListener('scroll', () => {
      const scrollY = window.scrollY;
      const docHeight = document.documentElement.scrollHeight - window.innerHeight;
      const progress = docHeight > 0 ? scrollY / docHeight : 0;
      
      this.targetCamera.z = progress * 600;
      this.targetCamera.rotX = (progress - 0.5) * 0.35;
    }, { passive: true });

    // Mouse parallax
    window.addEventListener('mousemove', (e) => {
      this.mouse.targetX = (e.clientX / this.width - 0.5) * 0.4;
      this.mouse.targetY = (e.clientY / this.height - 0.5) * 0.4;
    }, { passive: true });

    if (!this.isReducedMotion) {
      this.animate();
    } else {
      this.renderStatic();
    }
  }

  resize() {
    this.width = window.innerWidth;
    this.height = window.innerHeight;
    this.canvas.width = this.width * window.devicePixelRatio;
    this.canvas.height = this.height * window.devicePixelRatio;
    this.ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
  }

  animate() {
    // Smooth camera interpolation (lerp)
    this.camera.x += (this.mouse.targetX * 250 - this.camera.x) * 0.05;
    this.camera.y += (this.mouse.targetY * 250 - this.camera.y) * 0.05;
    this.camera.z += (this.targetCamera.z - this.camera.z) * 0.08;
    this.camera.rotX += (this.targetCamera.rotX + this.mouse.targetY * 0.3 - this.camera.rotX) * 0.05;
    this.camera.rotY += (this.mouse.targetX * 0.4 - this.camera.rotY) * 0.05;

    this.ctx.clearRect(0, 0, this.width, this.height);

    const cosY = Math.cos(this.camera.rotY);
    const sinY = Math.sin(this.camera.rotY);
    const cosX = Math.cos(this.camera.rotX);
    const sinX = Math.sin(this.camera.rotX);

    const projected = [];

    // Transform and project 3D points
    for (let i = 0; i < this.particles.length; i++) {
      const p = this.particles[i];

      // Update positions
      p.x += p.vx;
      p.y += p.vy;
      p.z += p.vz;

      // Wrap around boundary bounds
      if (p.x < -800) p.x = 800;
      if (p.x > 800) p.x = -800;
      if (p.y < -800) p.y = 800;
      if (p.y > 800) p.y = -800;
      if (p.z < -600) p.z = 600;
      if (p.z > 600) p.z = -600;

      // Translate by camera
      let tx = p.x - this.camera.x;
      let ty = p.y - this.camera.y;
      let tz = p.z + this.camera.z;

      // Rotate around Y axis
      let rx = tx * cosY - tz * sinY;
      let rz = tx * sinY + tz * cosY;

      // Rotate around X axis
      let ry = ty * cosX - rz * sinX;
      rz = ty * sinX + rz * cosX;

      // Prevent division by zero / behind camera
      if (rz > -this.fov + 20) {
        const scale = this.fov / (this.fov + rz);
        const projX = rx * scale + this.width / 2;
        const projY = ry * scale + this.height / 2;

        projected.push({
          x: projX,
          y: projY,
          scale: scale,
          z: rz,
          hue: p.hue,
          size: p.baseSize * scale
        });
      }
    }

    // Draw connecting neural lines
    const maxDist = 130;
    this.ctx.lineWidth = 0.8;
    for (let i = 0; i < projected.length; i++) {
      for (let j = i + 1; j < projected.length; j++) {
        const dx = projected[i].x - projected[j].x;
        const dy = projected[i].y - projected[j].y;
        const dist = Math.sqrt(dx * dx + dy * dy);

        if (dist < maxDist) {
          const alpha = (1 - dist / maxDist) * 0.22 * Math.min(projected[i].scale, 1);
          if (alpha > 0.02) {
            this.ctx.strokeStyle = `rgba(6, 182, 212, ${alpha})`;
            this.ctx.beginPath();
            this.ctx.moveTo(projected[i].x, projected[i].y);
            this.ctx.lineTo(projected[j].x, projected[j].y);
            this.ctx.stroke();
          }
        }
      }
    }

    // Draw glowing particles
    for (let i = 0; i < projected.length; i++) {
      const pt = projected[i];
      const alpha = Math.min(1, Math.max(0.15, pt.scale * 0.8));
      
      this.ctx.fillStyle = pt.hue === 190 
        ? `rgba(6, 182, 212, ${alpha})` 
        : `rgba(168, 85, 247, ${alpha})`;

      this.ctx.beginPath();
      this.ctx.arc(pt.x, pt.y, Math.max(0.8, pt.size), 0, Math.PI * 2);
      this.ctx.fill();
    }

    requestAnimationFrame(() => this.animate());
  }

  renderStatic() {
    this.ctx.fillStyle = 'rgba(6, 182, 212, 0.2)';
    for (let i = 0; i < 40; i++) {
      this.ctx.beginPath();
      this.ctx.arc(
        Math.random() * this.width, 
        Math.random() * this.height, 
        1.5, 0, Math.PI * 2
      );
      this.ctx.fill();
    }
  }
}
