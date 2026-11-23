/**
 * AI Mock Interview Platform - 3D Scroll & Spatial Interaction Engine
 * Features:
 * - Scroll-driven 3D perspective tilts on the hero preview frame
 * - IntersectionObserver 3D card entry transitions
 * - Dynamic mouse hover 3D tilt with specular lighting sheen
 */

export class Spatial3DScrollEngine {
  constructor() {
    this.heroFrame = document.querySelector('.interview-preview-frame');
    this.tiltCards = document.querySelectorAll('.glass-panel-hover, .stat-card, .pricing-card');
    this.isReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    this.init();
  }

  init() {
    this.initScrollReveal();
    if (this.isReducedMotion) return;

    this.initHeroParallax();
    this.init3DCardTilt();
  }

  // 1. Scroll-driven 3D Parallax on Hero Frame
  initHeroParallax() {
    if (!this.heroFrame) return;

    window.addEventListener('scroll', () => {
      const scrollY = window.scrollY;
      if (scrollY > 900) return; // Only process while hero is visible

      const rotX = Math.min(22, scrollY * 0.045);
      const scale = Math.max(0.92, 1 - scrollY * 0.00015);
      const transY = scrollY * 0.12;

      this.heroFrame.style.transform = `perspective(1200px) rotateX(${rotX}deg) translateY(${transY}px) scale(${scale})`;
      this.heroFrame.style.boxShadow = `0 ${25 + scrollY * 0.08}px ${50 + scrollY * 0.1}px rgba(0, 0, 0, 0.7), 0 0 ${40 - scrollY * 0.03}px var(--brand-cyan-glow)`;
    }, { passive: true });
  }

  // 2. 3D Scroll Reveal via IntersectionObserver
  initScrollReveal() {
    const revealElements = document.querySelectorAll('.feature-card, .domain-card, .workflow-card, .pricing-card, .stat-card');
    
    revealElements.forEach(el => {
      el.classList.add('reveal-3d-item');
    });

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible-3d');
          observer.unobserve(entry.target);
        }
      });
    }, {
      threshold: 0.15,
      rootMargin: '0px 0px -40px 0px'
    });

    revealElements.forEach(el => observer.observe(el));
  }

  // 3. Interactive Mouse Hover 3D Tilt
  init3DCardTilt() {
    this.tiltCards.forEach(card => {
      // Add dynamic specular reflection overlay
      const sheen = document.createElement('div');
      sheen.className = 'glass-specular-sheen';
      card.appendChild(sheen);

      card.addEventListener('mousemove', (e) => {
        const rect = card.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        const centerX = rect.width / 2;
        const centerY = rect.height / 2;
        
        // Tilt angles max 12 deg
        const rotY = ((x - centerX) / centerX) * 10;
        const rotX = -((y - centerY) / centerY) * 10;

        card.style.transform = `perspective(1000px) rotateX(${rotX.toFixed(2)}deg) rotateY(${rotY.toFixed(2)}deg) translateZ(12px)`;
        
        // Move specular sheen highlight
        sheen.style.background = `radial-gradient(circle at ${x}px ${y}px, rgba(255, 255, 255, 0.12) 0%, transparent 70%)`;
        sheen.style.opacity = '1';
      });

      card.addEventListener('mouseleave', () => {
        card.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg) translateZ(0)';
        sheen.style.opacity = '0';
      });
    });
  }
}
