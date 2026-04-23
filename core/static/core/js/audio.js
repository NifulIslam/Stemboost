/**
 * STEMboost Audio Engine  v2
 * ─────────────────────────────────────────────────────────────────────────────
 * Uses the Web Speech API (SpeechSynthesis) to provide real-time audio
 * guidance for blind and visually impaired (BVI) users.
 *
 * Features:
 *  - speakText(text)           → speaks any string immediately
 *  - Auto-attaches focus listeners to all [data-audio] elements
 *  - Page intro audio on load (from #page-intro)
 *  - Landing page YES/NO keyboard detection
 *  - Alt+H → repeat page intro
 *  - Alt+R → read currently focused element
 *  - Esc / Alt+S → stop speech
 *  - Mute/unmute button — persists across pages via localStorage
 *  - Error audio on login form — reads validation errors aloud
 *  - Logical Tab focus order (Shift+Tab backward navigation supported natively)
 * ─────────────────────────────────────────────────────────────────────────────
 */

'use strict';

/* ════════════════════════════════════════════════════════════════════════════
   MUTE PREFERENCE  (localStorage key: stemboost_muted)
   ════════════════════════════════════════════════════════════════════════════ */

const MutePreference = (() => {
  const KEY = 'stemboost_muted';

  function isMuted() {
    try { return localStorage.getItem(KEY) === '1'; } catch { return false; }
  }

  function setMuted(val) {
    try { localStorage.setItem(KEY, val ? '1' : '0'); } catch {}
  }

  function toggle() {
    const next = !isMuted();
    setMuted(next);
    return next;
  }

  return { isMuted, setMuted, toggle };
})();


/* ════════════════════════════════════════════════════════════════════════════
   CORE SPEECH ENGINE
   ════════════════════════════════════════════════════════════════════════════ */

const STEMboostAudio = (() => {
  const synth = window.speechSynthesis;
  let _voices = [];
  let _preferredVoice = null;

  function _loadVoices() {
    _voices = synth ? synth.getVoices() : [];
    _preferredVoice = (
      _voices.find(v => v.name === 'Google US English') ||
      _voices.find(v => v.name.includes('Samantha')) ||
      _voices.find(v => v.lang === 'en-US' && !v.localService) ||
      _voices.find(v => v.lang.startsWith('en')) ||
      _voices[0] ||
      null
    );
  }

  _loadVoices();
  if (synth && synth.onvoiceschanged !== undefined) {
    synth.onvoiceschanged = _loadVoices;
  }

  /**
   * Speak text aloud. Respects the global mute preference.
   * @param {string}  text       - Text to speak
   * @param {number}  rate       - Speech rate (default 0.85)
   * @param {boolean} interrupt  - Cancel ongoing speech first (default true)
   */
  function speak(text, rate = 0.85, interrupt = true) {
    if (!text || typeof text !== 'string') return;
    if (!synth) return;
    if (MutePreference.isMuted()) return;  // Honour mute

    if (interrupt) synth.cancel();

    const utt    = new SpeechSynthesisUtterance(text.trim());
    utt.rate     = rate;
    utt.pitch    = 1.05;
    utt.volume   = 1.0;
    if (_preferredVoice) utt.voice = _preferredVoice;

    utt.onerror = (e) => {
      if (e.error !== 'interrupted') {
        console.warn('[STEMboost] Speech error:', e.error);
      }
    };

    synth.speak(utt);
  }

  function stop() {
    if (synth) synth.cancel();
  }

  return { speak, stop };
})();

// Expose globally so inline handlers can call it
window.speakText = (text, rate) => STEMboostAudio.speak(text, rate);


/* ════════════════════════════════════════════════════════════════════════════
   ARIA LIVE REGION
   ════════════════════════════════════════════════════════════════════════════ */

const Announcer = (() => {
  let _el = null;

  function _init() {
    _el = document.getElementById('sr-announcer');
    if (!_el) {
      _el = document.createElement('div');
      _el.id = 'sr-announcer';
      _el.setAttribute('role', 'status');
      _el.setAttribute('aria-live', 'polite');
      _el.setAttribute('aria-atomic', 'true');
      _el.className = 'sr-only';
      document.body.prepend(_el);
    }
  }

  function announce(text) {
    if (!_el) _init();
    _el.textContent = '';
    requestAnimationFrame(() => { _el.textContent = text; });
  }

  return { announce, init: _init };
})();


/* ════════════════════════════════════════════════════════════════════════════
   MUTE BUTTON
   Reads from / writes to MutePreference and updates the button label.
   ════════════════════════════════════════════════════════════════════════════ */

function initMuteButton() {
  const btn = document.getElementById('btn-mute-toggle');
  if (!btn) return;

  function _syncButton() {
    const muted = MutePreference.isMuted();
    btn.textContent   = muted ? '🔇 Unmute' : '🔊 Mute';
    btn.setAttribute('aria-label', muted ? 'Unmute audio' : 'Mute audio');
    btn.setAttribute('aria-pressed', muted ? 'true' : 'false');
  }

  _syncButton(); // Reflect stored preference immediately on load

  btn.addEventListener('click', () => {
    const nowMuted = MutePreference.toggle();
    _syncButton();

    if (!nowMuted) {
      // Confirm unmute with a quick spoken message
      STEMboostAudio.speak('Audio unmuted.');
      Announcer.announce('Audio unmuted.');
    } else {
      // Stop any ongoing speech and confirm via ARIA only (no speech when muted)
      STEMboostAudio.stop();
      Announcer.announce('Audio muted. Press Unmute to re-enable spoken guidance.');
    }
  });
}


/* ════════════════════════════════════════════════════════════════════════════
   FOCUS AUDIO HOOKS
   ════════════════════════════════════════════════════════════════════════════ */

function attachFocusAudio() {
  document.querySelectorAll('[data-audio]').forEach(el => {
    el.addEventListener('focus', function () {
      const msg = this.dataset.audio;
      if (msg) {
        STEMboostAudio.speak(msg);
        Announcer.announce(msg);
      }
    });
  });
}


/* ════════════════════════════════════════════════════════════════════════════
   PAGE INTRO AUDIO
   ════════════════════════════════════════════════════════════════════════════ */

function playPageIntro() {
  const introEl = document.getElementById('page-intro');
  if (!introEl) return;
  const msg = introEl.dataset.message;
  if (!msg) return;

  setTimeout(() => {
    STEMboostAudio.speak(msg, 0.82);
    Announcer.announce(msg);
  }, 900);
}


/* ════════════════════════════════════════════════════════════════════════════
   LOGIN PAGE — AUDIO ERROR FEEDBACK  (Requirement 1)
   Read error messages aloud immediately when the page loads with errors.
   ════════════════════════════════════════════════════════════════════════════ */

function initLoginErrorAudio() {
  // Main error banner (wrong credentials)
  const errorBanner = document.getElementById('login-error');
  if (errorBanner) {
    const errText = errorBanner.textContent.replace(/[⚠✗]/g, '').trim();
    if (errText) {
      setTimeout(() => {
        STEMboostAudio.speak('Login error: ' + errText, 0.88, true);
        Announcer.announce('Login error: ' + errText);
        errorBanner.focus();
      }, 600);
    }
  }

  // Field-level errors (email format, password validation)
  const fieldErrors = document.querySelectorAll('.field-error');
  if (fieldErrors.length > 0 && !errorBanner) {
    const msgs = Array.from(fieldErrors)
      .map(el => el.textContent.replace(/[✗]/g, '').trim())
      .filter(Boolean);
    if (msgs.length) {
      setTimeout(() => {
        STEMboostAudio.speak('Form errors: ' + msgs.join('. '), 0.88, true);
        Announcer.announce('Form errors: ' + msgs.join('. '));
      }, 600);
    }
  }
}


/* ════════════════════════════════════════════════════════════════════════════
   LANDING PAGE LOGIC
   ════════════════════════════════════════════════════════════════════════════ */

function initLandingPage() {
  const yesBtn = document.getElementById('btn-yes');
  const noBtn  = document.getElementById('btn-no');
  if (!yesBtn || !noBtn) return;

  let awaitingResponse = true;

  setTimeout(() => { yesBtn.focus(); }, 1200);

  document.addEventListener('keydown', function (e) {
    if (!awaitingResponse) return;
    const key = e.key.toUpperCase();
    if (key === 'Y') {
      awaitingResponse = false;
      STEMboostAudio.speak('You pressed Y for Yes. Taking you to the Login page now.');
      setTimeout(() => { window.location.href = '/login/'; }, 1500);
    } else if (key === 'N') {
      awaitingResponse = false;
      STEMboostAudio.speak('You pressed N for No. Taking you to the Registration page.');
      setTimeout(() => { window.location.href = '/register/'; }, 1800);
    }
  });

  yesBtn.addEventListener('click', () => {
    STEMboostAudio.speak('Going to Login page.');
    setTimeout(() => { window.location.href = '/login/'; }, 800);
  });
  noBtn.addEventListener('click', () => {
    STEMboostAudio.speak('Going to Registration page.');
    setTimeout(() => { window.location.href = '/register/'; }, 1200);
  });
  yesBtn.addEventListener('mouseenter', () => STEMboostAudio.speak(yesBtn.dataset.audio));
  noBtn.addEventListener('mouseenter', ()  => STEMboostAudio.speak(noBtn.dataset.audio));
}


/* ════════════════════════════════════════════════════════════════════════════
   KEYBOARD NAVIGATION — Tab / Shift+Tab focus management  (Requirements 2 & 3)

   Strategy:
   - All interactive elements inside <main> and <header> receive a managed
     tabindex so the browser's natural Shift+Tab backward traversal works.
   - We do NOT implement a hard focus-trap (which would break browser
     accessibility tools and screen readers). Instead we ensure logical
     tab order: skip-link → nav → main content → footer links.
   - The skip-link (tabindex=1) lets keyboard users jump past nav instantly.
   - We annotate all interactive elements that lack explicit tabindex.
   ════════════════════════════════════════════════════════════════════════════ */

function initFocusManagement() {
  // Selectors for all natively focusable elements that should be in tab order
  const FOCUSABLE = [
    'a[href]',
    'button:not([disabled])',
    'input:not([disabled]):not([type="hidden"])',
    'select:not([disabled])',
    'textarea:not([disabled])',
    '[tabindex]:not([tabindex="-1"])',
  ].join(', ');

  // Ensure every interactive element inside main has tabindex >= 0
  // (browser handles Shift+Tab natively once elements are in the DOM order)
  document.querySelectorAll('#main-content ' + FOCUSABLE).forEach(el => {
    if (!el.hasAttribute('tabindex') || el.getAttribute('tabindex') < 0) {
      // Don't override explicit negative tabindices that mean "not reachable"
      if (el.getAttribute('tabindex') !== '-1') {
        el.setAttribute('tabindex', '0');
      }
    }
  });

  // Announce focus movement for elements without data-audio
  // (supports both Tab forward and Shift+Tab backward)
  let lastFocused = null;
  document.addEventListener('focusin', function (e) {
    const el = e.target;
    if (el === lastFocused) return;
    lastFocused = el;

    if (el.dataset.audio) return; // has its own audio hook

    const tag        = el.tagName.toLowerCase();
    const type       = el.type || '';
    const ariaLabel  = el.getAttribute('aria-label') || '';
    const labelEl    = el.id ? document.querySelector(`label[for="${el.id}"]`) : null;
    const labelText  = labelEl ? labelEl.textContent.trim() : '';
    const text       = el.textContent.trim().substring(0, 80);

    let msg = '';
    if (tag === 'button' || (tag === 'input' && type === 'submit')) {
      msg = `Button: ${ariaLabel || text || 'button'}. Press Enter to activate.`;
    } else if (tag === 'a') {
      msg = `Link: ${ariaLabel || text}. Press Enter to follow.`;
    } else if (tag === 'input') {
      msg = `Input field: ${labelText || ariaLabel || type}. Type to enter text.`;
    } else if (tag === 'select') {
      msg = `Dropdown: ${labelText || ariaLabel}. Use arrow keys to select.`;
    } else if (tag === 'textarea') {
      msg = `Text area: ${labelText || ariaLabel}. Type your message.`;
    }

    if (msg) {
      STEMboostAudio.speak(msg);
      Announcer.announce(msg);
    }
  });
}


/* ════════════════════════════════════════════════════════════════════════════
   GLOBAL KEYBOARD SHORTCUTS
   ════════════════════════════════════════════════════════════════════════════ */

function initGlobalShortcuts() {
  document.addEventListener('keydown', function (e) {

    // Alt+H → repeat page intro
    if (e.altKey && e.key === 'h') {
      e.preventDefault();
      const introEl = document.getElementById('page-intro');
      if (introEl && introEl.dataset.message) {
        STEMboostAudio.speak(introEl.dataset.message);
      } else {
        STEMboostAudio.speak('No page instructions available.');
      }
      return;
    }

    // Alt+R → read focused element
    if (e.altKey && e.key === 'r') {
      e.preventDefault();
      const focused = document.activeElement;
      if (focused && focused.dataset.audio) {
        STEMboostAudio.speak(focused.dataset.audio);
      } else if (focused) {
        const label = focused.getAttribute('aria-label') ||
                      focused.textContent.trim() ||
                      focused.tagName.toLowerCase();
        STEMboostAudio.speak('Currently focused: ' + label);
      }
      return;
    }

    // Alt+S or Escape → stop speaking
    if ((e.altKey && e.key === 's') || e.key === 'Escape') {
      if (e.key !== 'Escape') e.preventDefault();
      STEMboostAudio.stop();
    }
  });
}


/* ════════════════════════════════════════════════════════════════════════════
   ADMIN DASHBOARD
   ════════════════════════════════════════════════════════════════════════════ */

function initAdminDashboard() {
  document.querySelectorAll('.delete-user-btn').forEach(btn => {
    btn.addEventListener('click', function (e) {
      const email = this.dataset.email || 'this user';
      const confirmed = confirm(`Delete account for ${email}? This cannot be undone.`);
      if (!confirmed) {
        e.preventDefault();
        STEMboostAudio.speak('Delete cancelled.');
      } else {
        STEMboostAudio.speak(`Deleting user ${email}.`);
      }
    });
  });
}


/* ════════════════════════════════════════════════════════════════════════════
   FLASH MESSAGE AUDIO
   Reads Django flash messages (success/error) aloud on page load.
   ════════════════════════════════════════════════════════════════════════════ */

function initFlashMessageAudio() {
  document.querySelectorAll('[data-flash-msg]').forEach((el, i) => {
    const text = el.dataset.flashMsg || el.textContent.trim();
    if (text) {
      setTimeout(() => {
        STEMboostAudio.speak(text, 0.9, i === 0);
        Announcer.announce(text);
      }, 1200 + i * 300);
    }
  });
}


/* ════════════════════════════════════════════════════════════════════════════
   INITIALISE ON DOM READY
   ════════════════════════════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', function () {
  Announcer.init();
  initMuteButton();       // Mute/unmute control (Requirement 4)
  attachFocusAudio();
  initGlobalShortcuts();
  initFocusManagement();  // Tab / Shift+Tab management (Requirements 2 & 3)
  initLoginErrorAudio();  // Audio errors on login (Requirement 1)
  initFlashMessageAudio();
  playPageIntro();
  initLandingPage();
  initAdminDashboard();
});
