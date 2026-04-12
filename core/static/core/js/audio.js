/**
 * STEMboost Audio Engine
 * ──────────────────────────────────────────────────────────────
 * Uses the Web Speech API (SpeechSynthesis) to provide real-time
 * audio guidance for blind and visually impaired (BVI) users.
 *
 * Features:
 *  - speakText(text)          → Speaks any string immediately
 *  - Auto-attaches focus listeners to all [data-audio] elements
 *  - Page intro audio on load (from #page-intro)
 *  - Landing page YES/NO keyboard detection
 *  - Alt+H global shortcut → repeats page intro
 *  - Alt+R shortcut → reads currently focused element
 *  - Announces form errors via ARIA live region
 * ──────────────────────────────────────────────────────────────
 */

'use strict';

/* ── Core Speech Engine ──────────────────────────────────────── */

const STEMboostAudio = (() => {
  const synth = window.speechSynthesis;
  let _voices = [];
  let _preferredVoice = null;

  /**
   * Load available voices and pick the best English voice.
   * Voices load asynchronously in some browsers.
   */
  function _loadVoices() {
    _voices = synth.getVoices();
    _preferredVoice = (
      _voices.find(v => v.name === 'Google US English') ||
      _voices.find(v => v.name.includes('Samantha')) ||
      _voices.find(v => v.lang === 'en-US' && !v.localService) ||
      _voices.find(v => v.lang.startsWith('en')) ||
      _voices[0] ||
      null
    );
  }

  // Load voices immediately and again when they change
  _loadVoices();
  if (synth.onvoiceschanged !== undefined) {
    synth.onvoiceschanged = _loadVoices;
  }

  /**
   * Speak text aloud.
   * @param {string} text      - Text to speak
   * @param {number} rate      - Speech rate (0.5 – 1.4, default 0.85)
   * @param {boolean} interrupt - Cancel any ongoing speech first (default true)
   */
  function speak(text, rate = 0.85, interrupt = true) {
    if (!text || typeof text !== 'string') return;
    if (!synth) {
      console.warn('[STEMboost] SpeechSynthesis not supported in this browser.');
      return;
    }

    if (interrupt) synth.cancel();

    const utt = new SpeechSynthesisUtterance(text.trim());
    utt.rate   = rate;
    utt.pitch  = 1.05;
    utt.volume = 1.0;
    if (_preferredVoice) utt.voice = _preferredVoice;

    // Guard against Chrome bug where long text stalls
    utt.onend   = () => {};
    utt.onerror = (e) => {
      if (e.error !== 'interrupted') {
        console.warn('[STEMboost] Speech error:', e.error);
      }
    };

    synth.speak(utt);
  }

  function stop() {
    synth.cancel();
  }

  return { speak, stop, get voices() { return _voices; } };
})();

// Expose globally so inline handlers can call it
window.speakText = (text, rate) => STEMboostAudio.speak(text, rate);


/* ── ARIA Live Region Announcer ─────────────────────────────── */

const Announcer = (() => {
  let _el = null;

  function _init() {
    _el = document.getElementById('sr-announcer');
    if (!_el) {
      _el = document.createElement('div');
      _el.id = 'sr-announcer';
      _el.setAttribute('aria-live', 'polite');
      _el.setAttribute('aria-atomic', 'true');
      _el.className = 'sr-only';
      document.body.prepend(_el);
    }
  }

  function announce(text) {
    if (!_el) _init();
    _el.textContent = '';
    // Small delay ensures screen readers pick up the change
    requestAnimationFrame(() => { _el.textContent = text; });
  }

  return { announce, init: _init };
})();


/* ── Focus Audio Hooks ──────────────────────────────────────── */

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


/* ── Page Intro Audio ───────────────────────────────────────── */

function playPageIntro() {
  const introEl = document.getElementById('page-intro');
  if (!introEl) return;

  const msg = introEl.dataset.message;
  if (!msg) return;

  // Delay slightly so browser audio context is ready
  setTimeout(() => {
    STEMboostAudio.speak(msg, 0.82);
    Announcer.announce(msg);
  }, 900);
}


/* ── Audio Status Indicator ─────────────────────────────────── */

function updateAudioStatus(state) {
  const el = document.getElementById('audio-status-text');
  if (el) el.textContent = state;
}


/* ── Landing Page Logic ─────────────────────────────────────── */

function initLandingPage() {
  const yesBtn = document.getElementById('btn-yes');
  const noBtn  = document.getElementById('btn-no');

  if (!yesBtn || !noBtn) return;

  let inputBuffer = '';
  let awaitingResponse = true;

  // Set initial focus to the YES button after intro plays
  setTimeout(() => {
    yesBtn.focus();
  }, 1200);

  // Keyboard shortcut: press Y → go to login
  //                    press N → go to register
  document.addEventListener('keydown', function (e) {
    if (!awaitingResponse) return;

    const key = e.key.toUpperCase();

    if (key === 'Y') {
      awaitingResponse = false;
      STEMboostAudio.speak('You pressed Y for Yes. Taking you to the Login page now.');
      setTimeout(() => { window.location.href = '/login/'; }, 1500);
      return;
    }

    if (key === 'N') {
      awaitingResponse = false;
      STEMboostAudio.speak('You pressed N for No. Taking you to the Registration page now. Let us create your account.');
      setTimeout(() => { window.location.href = '/register/'; }, 1800);
      return;
    }
  });

  // Button click handlers
  yesBtn.addEventListener('click', () => {
    STEMboostAudio.speak('Going to Login page.');
    setTimeout(() => { window.location.href = '/login/'; }, 800);
  });

  noBtn.addEventListener('click', () => {
    STEMboostAudio.speak('Going to Registration page. Let us create your account.');
    setTimeout(() => { window.location.href = '/register/'; }, 1200);
  });

  // Button hover reads audio too (useful when using mouse + screen reader combo)
  yesBtn.addEventListener('mouseenter', () => {
    STEMboostAudio.speak(yesBtn.dataset.audio);
  });
  noBtn.addEventListener('mouseenter', () => {
    STEMboostAudio.speak(noBtn.dataset.audio);
  });
}


/* ── Login / Register Form Enhancements ─────────────────────── */

function initFormPage() {
  const form = document.querySelector('form[data-accessible-form]');
  if (!form) return;

  form.addEventListener('submit', function () {
    STEMboostAudio.speak('Submitting form. Please wait.');
  });

  // Announce field validation errors
  const observer = new MutationObserver(mutations => {
    mutations.forEach(m => {
      m.addedNodes.forEach(node => {
        if (node.nodeType === 1 && node.classList.contains('field-error')) {
          const msg = 'Error: ' + node.textContent;
          STEMboostAudio.speak(msg, 0.9, false);
          Announcer.announce(msg);
        }
      });
    });
  });

  observer.observe(form, { childList: true, subtree: true });
}


/* ── Global Keyboard Shortcuts ──────────────────────────────── */

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

    // Alt+S → stop speaking
    if (e.altKey && e.key === 's') {
      e.preventDefault();
      STEMboostAudio.stop();
      return;
    }

    // Escape → cancel speech
    if (e.key === 'Escape') {
      STEMboostAudio.stop();
    }
  });
}


/* ── Tab navigation announcements ───────────────────────────── */

function announceTabMovement() {
  let lastFocused = null;

  document.addEventListener('focusin', function (e) {
    const el = e.target;
    if (el === lastFocused) return;
    lastFocused = el;

    // If element doesn't have data-audio, try to build a helpful description
    if (!el.dataset.audio) {
      const tag  = el.tagName.toLowerCase();
      const type = el.type || '';
      const labelEl = el.id
        ? document.querySelector(`label[for="${el.id}"]`)
        : null;
      const labelText = labelEl ? labelEl.textContent.trim() : '';
      const ariaLabel = el.getAttribute('aria-label') || '';
      const text = el.textContent.trim().substring(0, 80);

      let msg = '';
      if (tag === 'button' || (tag === 'input' && type === 'submit')) {
        msg = `Button: ${ariaLabel || text || 'unlabeled button'}. Press Enter to activate.`;
      } else if (tag === 'a') {
        msg = `Link: ${ariaLabel || text}. Press Enter to follow.`;
      } else if (tag === 'input') {
        msg = `Input field: ${labelText || ariaLabel || type}. Type to enter text.`;
      } else if (tag === 'select') {
        msg = `Dropdown: ${labelText || ariaLabel}. Use arrow keys to select.`;
      }

      if (msg) {
        STEMboostAudio.speak(msg);
        Announcer.announce(msg);
      }
    }
  });
}


/* ── Admin Dashboard ────────────────────────────────────────── */

function initAdminDashboard() {
  // Confirm before delete
  document.querySelectorAll('.delete-user-btn').forEach(btn => {
    btn.addEventListener('click', function (e) {
      const email = this.dataset.email || 'this user';
      const confirmed = confirm(`Are you sure you want to delete the account for ${email}? This cannot be undone.`);
      if (!confirmed) {
        e.preventDefault();
        STEMboostAudio.speak('Delete cancelled.');
      } else {
        STEMboostAudio.speak(`Deleting user ${email}.`);
      }
    });
  });
}


/* ── Initialise Everything on DOM Ready ─────────────────────── */

document.addEventListener('DOMContentLoaded', function () {
  Announcer.init();
  attachFocusAudio();
  initGlobalShortcuts();
  announceTabMovement();
  playPageIntro();
  initLandingPage();
  initFormPage();
  initAdminDashboard();

  // Announce when Django messages flash
  document.querySelectorAll('.alert').forEach(alertEl => {
    const text = alertEl.textContent.trim();
    if (text) {
      setTimeout(() => {
        STEMboostAudio.speak(text, 0.9, false);
      }, 1200);
    }
  });

  // Make the audio-icon stop animating once speech ends
  const icon = document.querySelector('.audio-icon');
  if (icon && window.speechSynthesis) {
    window.speechSynthesis.addEventListener?.('end', () => {
      icon.style.animation = 'none';
    });
  }
});
