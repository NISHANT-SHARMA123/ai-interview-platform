/**
 * AI Mock Interview Platform - Client Interaction & UI Controller
 * Vanilla JavaScript (ES Module)
 */

export function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

export function getCSRFToken() {
  const metaToken = document.querySelector('meta[name="csrf-token"]');
  if (metaToken) return metaToken.getAttribute('content');
  return getCookie('csrftoken') || '';
}

// Password Visibility Toggle
function initPasswordToggles() {
  const toggleButtons = document.querySelectorAll('[data-toggle-password]');
  toggleButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetId = btn.getAttribute('data-toggle-password');
      const input = document.getElementById(targetId);
      if (!input) return;

      if (input.type === 'password') {
        input.type = 'text';
        btn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line></svg>`;
      } else {
        input.type = 'password';
        btn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>`;
      }
    });
  });
}

// Live Password Strength Meter
function initPasswordStrengthMeter() {
  const passwordInput = document.getElementById('signup-password');
  const meter = document.getElementById('password-strength-meter');
  if (!passwordInput || !meter) return;

  const segments = meter.querySelectorAll('.strength-segment');

  passwordInput.addEventListener('input', () => {
    const val = passwordInput.value;
    let score = 0;

    if (val.length >= 8) score++;
    if (/[A-Z]/.test(val) && /[a-z]/.test(val)) score++;
    if (/[0-9]/.test(val)) score++;
    if (/[^A-Za-z0-9]/.test(val)) score++;

    segments.forEach((seg, index) => {
      seg.className = 'strength-segment';
      if (index < score) {
        if (score === 1) seg.classList.add('active-weak');
        else if (score === 2) seg.classList.add('active-fair');
        else if (score === 3) seg.classList.add('active-good');
        else if (score === 4) seg.classList.add('active-strong');
      }
    });
  });
}

// Client-Side Email Validation Feedback
function initEmailValidation() {
  const emailInput = document.getElementById('signup-email');
  if (!emailInput) return;

  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  emailInput.addEventListener('blur', () => {
    if (emailInput.value.length > 0 && !emailRegex.test(emailInput.value)) {
      emailInput.classList.add('is-invalid');
    } else {
      emailInput.classList.remove('is-invalid');
    }
  });
}

// Toast Auto-Dismissal
function initToasts() {
  const toasts = document.querySelectorAll('.toast');
  toasts.forEach(toast => {
    setTimeout(() => {
      toast.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(100%)';
      setTimeout(() => toast.remove(), 400);
    }, 4500);
  });
}

// Universal Modal Controller (Open, Close, ESC, Backdrop Click)
export function initModals() {
  function openModal(modal) {
    if (!modal) return;
    modal.classList.add('is-active');
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
  }

  function closeModal(modal) {
    if (!modal) return;
    modal.classList.remove('is-active');
    modal.style.display = 'none';
    document.body.style.overflow = '';
  }

  // Bind all open triggers with [data-open-modal]
  document.querySelectorAll('[data-open-modal]').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const modalId = btn.getAttribute('data-open-modal');
      const modal = document.getElementById(modalId);
      openModal(modal);
    });
  });

  // Bind all close buttons with [data-close-modal]
  document.querySelectorAll('[data-close-modal]').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const modalId = btn.getAttribute('data-close-modal');
      const modal = (modalId && document.getElementById(modalId)) || btn.closest('.modal-overlay');
      closeModal(modal);
    });
  });

  // Close when clicking directly on overlay backdrop
  document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) {
        closeModal(overlay);
      }
    });
  });

  // Close on Escape key press
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      document.querySelectorAll('.modal-overlay.is-active').forEach(modal => {
        closeModal(modal);
      });
    }
  });
}

import { Ambient3DBackground } from './3d-canvas-bg.js';
import { Spatial3DScrollEngine } from './3d-scroll.js';

// DOM Initialization
document.addEventListener('DOMContentLoaded', () => {
  initPasswordToggles();
  initPasswordStrengthMeter();
  initEmailValidation();
  initToasts();
  initModals();

  // Initialize 3D Spatial Systems
  new Ambient3DBackground('bg-3d-canvas');
  new Spatial3DScrollEngine();
});
