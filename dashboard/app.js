/**
 * Job Beeper — Opportunity Radar & Job Intelligence Workspace Engine
 * Production Workspace Architecture with 3-Way Theme System & Custom Accessible Popovers
 * WCAG AAA Contrast · Zero Gradients · Full Keyboard Accessibility
 */

(function () {
  'use strict';

  // =========================================================================
  // 1. API Resolution, Constants, State & SVG Icon Registry
  // =========================================================================
  const requestedApi = new URLSearchParams(location.search).get('api');
  // API overrides are restricted to this dashboard's origin so login credentials
  // can never be sent to a URL supplied in a crafted query string.
  const API = window.JobBeeperAuth.resolveApiBase(requestedApi || '/api', window.location);
  const authClient = window.JobBeeperAuth.createClient({ apiBase: API, locationRef: window.location });

  const LOCAL_STORAGE_APPLIED_KEY = 'job_beeper_applied_jobs_v1';
  const THEME_STORAGE_KEY = 'job_beeper_theme';

  const state = {
    jobs: [],
    selectedJobId: null,
    appliedJobs: [],
    config: null,
    summary: null,
    sourceStatus: [],
    activeSection: 'jobsSection',
    filters: {
      search: '',
      source: '',
      minScore: 0,
      maxAge: 72,
      sort: 'newest',
      alertableOnly: false,
      remoteOnly: false,
    },
    isPolling: false,
    isStaticFallback: false,
  };

  const tagInputs = {};
  const dropdowns = {};
  const activeDropdownInstances = [];
  let jobsFeedRequestSequence = 0;

  const SVG_ICONS = {
    briefcase: '<svg class="icon icon-sm" viewBox="0 0 24 24"><rect width="20" height="14" x="2" y="7" rx="2" ry="2"></rect><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path></svg>',
    checkCircle: '<svg class="icon icon-sm" viewBox="0 0 24 24"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>',
    mapPin: '<svg class="icon icon-sm" viewBox="0 0 24 24"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"></path><circle cx="12" cy="10" r="3"></circle></svg>',
    graduationCap: '<svg class="icon icon-sm" viewBox="0 0 24 24"><path d="M22 10v6M2 10l10-5 10 5-10 5z"></path><path d="M6 12v5c3 3 9 3 12 0v-5"></path></svg>',
    clock: '<svg class="icon icon-sm" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 14 14"></polyline></svg>',
    arrowUpRight: '<svg class="icon icon-sm" viewBox="0 0 24 24"><line x1="7" x2="17" y1="17" y2="7"></line><polyline points="7 7 17 7 17 17"></polyline></svg>',
    rotateCw: '<svg class="icon icon-sm" viewBox="0 0 24 24"><path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"></path><path d="M3 3v5h5"></path><path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"></path><path d="M16 21h5v-5"></path></svg>',
    x: '<svg class="icon icon-sm" viewBox="0 0 24 24"><line x1="18" x2="6" y1="6" y2="18"></line><line x1="6" x2="18" y1="6" y2="18"></line></svg>',
    copy: '<svg class="icon icon-sm" viewBox="0 0 24 24"><rect width="14" height="14" x="8" y="8" rx="2" ry="2"></rect><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"></path></svg>',
    check: '<svg class="icon icon-sm" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"></polyline></svg>',
    trash: '<svg class="icon icon-sm" viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>',
    monitor: '<svg class="icon icon-sm" viewBox="0 0 24 24"><rect width="20" height="14" x="2" y="3" rx="2"></rect><line x1="8" x2="16" y1="21" y2="21"></line><line x1="12" x2="12" y1="17" y2="21"></line></svg>',
    sun: '<svg class="icon icon-sm" viewBox="0 0 24 24"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>',
    moon: '<svg class="icon icon-sm" viewBox="0 0 24 24"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"></path></svg>',
  };

  const $ = id => document.getElementById(id);

  function esc(value) {
    return String(value ?? '').replace(/[&<>"']/g, char => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;',
    }[char]));
  }

  // =========================================================================
  // 2. Complete 3-Way Theme Management System (System / Light / Dark)
  // =========================================================================
  let currentThemeSetting = localStorage.getItem(THEME_STORAGE_KEY) || 'system';

  function getSystemTheme() {
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  function applyTheme(setting, animate = true) {
    currentThemeSetting = setting;
    const effectiveTheme = setting === 'system' ? getSystemTheme() : setting;

    if (animate && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      document.documentElement.classList.add('theme-transitioning');
      setTimeout(() => {
        document.documentElement.classList.remove('theme-transitioning');
      }, 200);
    }

    document.documentElement.setAttribute('data-theme', effectiveTheme);
    document.documentElement.setAttribute('data-theme-setting', setting);

    if (setting === 'system') {
      localStorage.removeItem(THEME_STORAGE_KEY);
    } else {
      localStorage.setItem(THEME_STORAGE_KEY, setting);
    }

    updateThemeUI(setting, effectiveTheme);
  }

  function updateThemeUI(setting, effectiveTheme) {
    const labelEl = $('themeBtnLabel');
    const iconEl = $('themeBtnIcon');
    if (labelEl) {
      labelEl.textContent = setting === 'system' ? 'System' : setting === 'light' ? 'Light' : 'Dark';
    }
    if (iconEl) {
      iconEl.innerHTML = setting === 'system' ? SVG_ICONS.monitor : setting === 'light' ? SVG_ICONS.sun : SVG_ICONS.moon;
    }

    document.querySelectorAll('.theme-option-item').forEach(btn => {
      const val = btn.dataset.themeValue;
      const isSelected = val === setting;
      btn.classList.toggle('selected', isSelected);
      btn.setAttribute('aria-selected', String(isSelected));
    });
  }

  function initThemeSystem() {
    applyTheme(currentThemeSetting, false);

    if (window.matchMedia) {
      window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
        if (currentThemeSetting === 'system') {
          applyTheme('system', true);
        }
      });
    }

    const toggleBtn = $('themeToggleBtn');
    const popoverMenu = $('themePopoverMenu');

    if (toggleBtn && popoverMenu) {
      toggleBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        const isOpen = popoverMenu.classList.contains('is-open');
        closeAllDropdowns('theme');
        if (!isOpen) {
          popoverMenu.classList.add('is-open');
          toggleBtn.classList.add('is-open');
          toggleBtn.setAttribute('aria-expanded', 'true');
        } else {
          closeThemePopover();
        }
      });

      popoverMenu.querySelectorAll('.theme-option-item').forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.stopPropagation();
          const targetTheme = btn.dataset.themeValue;
          applyTheme(targetTheme, true);
          closeThemePopover();
          showToast(`Appearance set to ${targetTheme === 'system' ? 'System Default' : targetTheme.toUpperCase()}`, 'info', 2000);
        });
      });
    }
  }

  function closeThemePopover() {
    const popoverMenu = $('themePopoverMenu');
    const toggleBtn = $('themeToggleBtn');
    if (popoverMenu) popoverMenu.classList.remove('is-open');
    if (toggleBtn) {
      toggleBtn.classList.remove('is-open');
      toggleBtn.setAttribute('aria-expanded', 'false');
    }
  }

  // =========================================================================
  // 3. Reusable Accessible Custom Dropdown Component
  // =========================================================================
  function closeAllDropdowns(exceptInstance) {
    for (let i = activeDropdownInstances.length - 1; i >= 0; i--) {
      const inst = activeDropdownInstances[i];
      if (!inst.container || !document.body.contains(inst.container)) {
        activeDropdownInstances.splice(i, 1);
        continue;
      }
      if (inst !== exceptInstance && inst.isOpen) {
        inst.close();
      }
    }
    if (exceptInstance !== 'theme') {
      closeThemePopover();
    }
  }

  document.addEventListener('click', (e) => {
    if (!e.target.closest('.custom-dropdown-wrap') && !e.target.closest('.theme-dropdown-wrap')) {
      closeAllDropdowns();
    }
  });

  class CustomDropdown {
    constructor({ container, id, ariaLabel, options, value, onChange, align = 'left', minWidth }) {
      this.container = typeof container === 'string' ? document.getElementById(container) : container;
      this.id = id;
      this.ariaLabel = ariaLabel;
      this.options = options || [];
      this.value = value !== undefined ? String(value) : (this.options[0]?.value ?? '');
      this.onChange = onChange;
      this.align = align;
      this.minWidth = minWidth;
      this.isOpen = false;
      this.focusedIndex = -1;

      this.render();
      this.bindEvents();
      activeDropdownInstances.push(this);
    }

    render() {
      if (!this.container) return;
      const selectedOpt = this.options.find(o => String(o.value) === String(this.value)) || this.options[0] || { label: '', value: '' };

      this.container.innerHTML = `
        <div class="custom-dropdown-wrap" id="wrap_${this.id}">
          <button type="button" class="custom-dropdown-trigger" id="trigger_${this.id}" aria-haspopup="listbox" aria-expanded="false" aria-label="${esc(this.ariaLabel)}">
            <span class="custom-dropdown-label">${esc(selectedOpt.label || selectedOpt.value)}</span>
            <svg class="icon icon-sm chevron-icon" viewBox="0 0 24 24"><polyline points="6 9 12 15 18 9"></polyline></svg>
          </button>
          <div class="custom-dropdown-menu ${this.align === 'right' ? 'align-right' : ''}" id="menu_${this.id}" role="listbox" aria-label="${esc(this.ariaLabel)}" tabindex="-1">
            ${this.options.map((opt, idx) => {
              const isSelected = String(opt.value) === String(this.value);
              return `
                <div class="custom-dropdown-option ${isSelected ? 'selected' : ''}" data-value="${esc(opt.value)}" data-index="${idx}" role="option" aria-selected="${isSelected}" tabindex="-1">
                  <span class="option-label">${esc(opt.label || opt.value)}</span>
                  <span class="option-check" aria-hidden="true">
                    <svg class="icon icon-sm" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"></polyline></svg>
                  </span>
                </div>
              `;
            }).join('')}
          </div>
        </div>
      `;

      this.wrapEl = this.container.querySelector('.custom-dropdown-wrap');
      this.triggerEl = this.container.querySelector('.custom-dropdown-trigger');
      this.menuEl = this.container.querySelector('.custom-dropdown-menu');
      this.optionEls = Array.from(this.container.querySelectorAll('.custom-dropdown-option'));

      if (this.minWidth) {
        this.menuEl.style.minWidth = this.minWidth;
      }
    }

    bindEvents() {
      if (!this.triggerEl) return;

      this.triggerEl.addEventListener('click', (e) => {
        e.stopPropagation();
        this.toggle();
      });

      this.triggerEl.addEventListener('keydown', (e) => {
        if (e.key === 'ArrowDown' || e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          this.open();
          this.focusFirstOrSelected();
        } else if (e.key === 'ArrowUp') {
          e.preventDefault();
          this.open();
          this.focusLastOrSelected();
        }
      });

      this.menuEl.addEventListener('click', (e) => {
        const optEl = e.target.closest('.custom-dropdown-option');
        if (optEl) {
          e.stopPropagation();
          this.selectValue(optEl.dataset.value);
        }
      });

      this.menuEl.addEventListener('keydown', (e) => {
        if (e.key === 'ArrowDown') {
          e.preventDefault();
          this.focusNext();
        } else if (e.key === 'ArrowUp') {
          e.preventDefault();
          this.focusPrev();
        } else if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          if (this.focusedIndex >= 0 && this.optionEls[this.focusedIndex]) {
            this.selectValue(this.optionEls[this.focusedIndex].dataset.value);
          }
        } else if (e.key === 'Escape' || e.key === 'Tab') {
          this.close();
          this.triggerEl.focus();
        }
      });
    }

    open() {
      closeAllDropdowns(this);
      this.isOpen = true;
      this.triggerEl.classList.add('is-open');
      this.triggerEl.setAttribute('aria-expanded', 'true');
      this.menuEl.classList.add('is-open');

      const rect = this.menuEl.getBoundingClientRect();
      if (rect.bottom > window.innerHeight - 10) {
        this.menuEl.classList.add('open-upward');
      } else {
        this.menuEl.classList.remove('open-upward');
      }
      if (rect.right > window.innerWidth - 10) {
        this.menuEl.classList.add('align-right');
      }
    }

    close() {
      this.isOpen = false;
      this.triggerEl.classList.remove('is-open');
      this.triggerEl.setAttribute('aria-expanded', 'false');
      this.menuEl.classList.remove('is-open');
      this.focusedIndex = -1;
    }

    toggle() {
      if (this.isOpen) this.close();
      else this.open();
    }

    selectValue(val) {
      const prev = this.value;
      this.value = String(val);
      this.updateSelectedUI();
      this.close();
      this.triggerEl.focus();
      if (prev !== this.value && typeof this.onChange === 'function') {
        this.onChange(this.value);
      }
    }

    setValue(val, triggerCallback = false) {
      this.value = String(val);
      this.updateSelectedUI();
      if (triggerCallback && typeof this.onChange === 'function') {
        this.onChange(this.value);
      }
    }

    getValue() {
      return this.value;
    }

    setOptions(options, selectedValue) {
      const newOpts = options || [];
      const isSame = this.options.length === newOpts.length &&
        this.options.every((opt, i) => String(opt.value) === String(newOpts[i]?.value) && String(opt.label) === String(newOpts[i]?.label));

      const newTargetValue = selectedValue !== undefined ? String(selectedValue) : this.value;
      if (isSame && this.value === newTargetValue) {
        return;
      }

      this.options = newOpts;
      if (selectedValue !== undefined) {
        this.value = String(selectedValue);
      } else if (!this.options.some(o => String(o.value) === String(this.value))) {
        this.value = this.options[0]?.value ?? '';
      }
      const wasOpen = this.isOpen;
      this.render();
      this.bindEvents();
      if (wasOpen) {
        this.open();
      }
    }

    updateSelectedUI() {
      const selectedOpt = this.options.find(o => String(o.value) === String(this.value)) || this.options[0] || { label: '', value: '' };
      const labelEl = this.container.querySelector('.custom-dropdown-label');
      if (labelEl) {
        labelEl.textContent = selectedOpt.label || selectedOpt.value;
      }
      this.optionEls.forEach(el => {
        const isSel = String(el.dataset.value) === String(this.value);
        el.classList.toggle('selected', isSel);
        el.setAttribute('aria-selected', String(isSel));
      });
    }

    focusFirstOrSelected() {
      const selIdx = this.options.findIndex(o => String(o.value) === String(this.value));
      this.focusedIndex = selIdx >= 0 ? selIdx : 0;
      this.focusIndex(this.focusedIndex);
    }

    focusLastOrSelected() {
      const selIdx = this.options.findIndex(o => String(o.value) === String(this.value));
      this.focusedIndex = selIdx >= 0 ? selIdx : this.options.length - 1;
      this.focusIndex(this.focusedIndex);
    }

    focusNext() {
      if (this.options.length === 0) return;
      this.focusedIndex = (this.focusedIndex + 1) % this.options.length;
      this.focusIndex(this.focusedIndex);
    }

    focusPrev() {
      if (this.options.length === 0) return;
      this.focusedIndex = (this.focusedIndex - 1 + this.options.length) % this.options.length;
      this.focusIndex(this.focusedIndex);
    }

    focusIndex(idx) {
      if (this.optionEls[idx]) {
        this.optionEls[idx].focus();
      }
    }
  }

  // =========================================================================
  // 4. Data Normalization & Formatting Helpers
  // =========================================================================
  function normalizeJob(raw) {
    if (!raw) return null;
    const score = Number(raw.match_score ?? raw.score ?? 0);
    const reasons = Array.isArray(raw.match_reasons)
      ? raw.match_reasons
      : Array.isArray(raw.reasons)
        ? raw.reasons
        : [];

    let minExp = raw.experience_min_years ?? raw.experience?.min ?? null;
    let maxExp = raw.experience_max_years ?? raw.experience?.max ?? null;
    let expLabel = raw.experience?.label || (
      minExp !== null || maxExp !== null
        ? (minExp !== null && maxExp !== null ? `${minExp}–${maxExp} yrs` : minExp !== null ? `${minExp}+ yrs` : `Up to ${maxExp} yrs`)
        : 'Not specified'
    );

    let workMode = raw.work_mode || (
      raw.location?.toLowerCase().includes('remote')
        ? 'Remote'
        : raw.location?.toLowerCase().includes('hybrid')
          ? 'Hybrid'
          : 'Not specified'
    );

    let skillsDetected = Array.isArray(raw.skills_detected)
      ? raw.skills_detected
      : reasons.filter(r => !r.includes('fit') && !r.includes('location') && !r.includes('experience') && !r.includes('stated') && !r.includes('target'));

    return {
      id: String(raw.id),
      source: raw.source || 'direct',
      source_job_id: raw.source_job_id || raw.id,
      company: raw.company || 'Unknown Company',
      title: raw.title || 'Untitled Role',
      location: raw.location || raw.jd_location || 'Location not specified',
      url: raw.url || '#',
      description: raw.description || '',
      description_format: raw.description_format === 'markdown' ? 'markdown' : 'plain',
      source_details: raw.source_details && typeof raw.source_details === 'object'
        ? raw.source_details
        : {},
      source_posted_at: raw.source_posted_at || raw.posted || null,
      posted_precision: raw.posted_precision || null,
      discovered_at: raw.discovered_at || null,
      discovery_latency_seconds: raw.discovery_latency_seconds ?? null,
      match_score: score,
      likely_match: Boolean(raw.likely_match),
      match_reasons: reasons,
      alertable: Boolean(raw.alertable),
      alertability_reasons: Array.isArray(raw.alertability_reasons) ? raw.alertability_reasons : [],
      notification_status: String(raw.notification_status || 'not_eligible').toLowerCase(),
      notification_decision_reasons: Array.isArray(raw.notification_decision_reasons) ? raw.notification_decision_reasons : [],
      notification_sent_at: raw.notification_sent_at || null,
      notification_last_error: raw.notification_last_error || null,
      notification_candidate_job_id: raw.notification_candidate_job_id ?? null,
      experience_min_years: minExp,
      experience_max_years: maxExp,
      experience_label: expLabel,
      work_mode: workMode,
      skills_detected: skillsDetected,
      canonical_opportunity_id: raw.canonical_opportunity_id || null,
      canonical_match_method: raw.canonical_match_method || null,
      canonical_match_confidence: raw.canonical_match_confidence ?? null,
    };
  }

  function jobTimestamp(job) {
    return job.source_posted_at || job.discovered_at || null;
  }

  function ageHours(timestamp) {
    if (!timestamp) return 9999;
    const diff = Date.now() - new Date(timestamp).getTime();
    return Math.max(0, diff / 3600000);
  }

  function fmtAge(timestamp) {
    if (!timestamp) return 'time unknown';
    const hours = ageHours(timestamp);
    if (hours < 1) {
      const mins = Math.max(1, Math.round(hours * 60));
      return `${mins}m ago`;
    }
    if (hours < 24) {
      return `${Math.round(hours)}h ago`;
    }
    const days = Math.round(hours / 24);
    return `${days}d ago`;
  }

  function fmtTimestamp(timestamp, precision) {
    if (!timestamp) return 'Not specified';
    const date = new Date(timestamp);
    if (Number.isNaN(date.getTime())) return 'Not specified';
    if (precision === 'date' || precision === 'day') {
      return date.toLocaleString('en-IN', {
        timeZone: 'Asia/Kolkata',
        day: '2-digit',
        month: 'short',
        year: 'numeric',
      }) + ' (date only)';
    }
    return date.toLocaleString('en-IN', {
      timeZone: 'Asia/Kolkata',
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    }) + ' IST';
  }

  function getScoreTierClass(score) {
    if (score >= 90) return 'high';
    if (score >= 70) return 'strong';
    if (score >= 55) return 'mod';
    return 'norm';
  }

  function formatIntelligenceReason(rawReason) {
    if (!rawReason) return { text: '', type: 'neutral', icon: '•' };
    const str = String(rawReason).trim();
    const lower = str.toLowerCase();

    if (lower.startsWith('target location')) {
      return { text: str.replace(/^target location:?/i, 'Location match:').trim(), type: 'success', icon: '✓' };
    }
    if (lower.includes('location outside')) {
      return { text: 'Location outside target', type: 'warning', icon: '✕' };
    }
    if (lower.startsWith('target-role match')) {
      return { text: str.replace(/^target-role match:?/i, 'Role match:').trim(), type: 'success', icon: '✓' };
    }
    if (lower.includes('no configured target-role match')) {
      return { text: 'Role title outside target profile', type: 'neutral', icon: '•' };
    }
    if (lower.includes('experience compatible')) {
      return { text: str.replace(/^experience compatible:?/i, 'Exp match:').trim(), type: 'success', icon: '✓' };
    }
    if (lower.includes('exceeds candidate')) {
      return { text: str.replace(/^experience minimum/i, 'Min exp').trim(), type: 'warning', icon: '✕' };
    }
    if (lower.includes('experience not stated')) {
      return { text: 'Exp unspecified in source', type: 'neutral', icon: '•' };
    }
    if (lower.includes('title exclude') || lower.includes('role category excluded')) {
      return { text: str, type: 'warning', icon: '✕' };
    }
    if (lower.includes('not a profile match')) {
      return { text: 'Below threshold match criteria', type: 'neutral', icon: '•' };
    }
    return { text: str, type: 'skill', icon: '✓' };
  }

  // =========================================================================
  // 5. Local-First Applied Jobs Store
  // =========================================================================
  function loadAppliedJobs() {
    try {
      const raw = localStorage.getItem(LOCAL_STORAGE_APPLIED_KEY);
      state.appliedJobs = raw ? JSON.parse(raw) : [];
      if (!Array.isArray(state.appliedJobs)) state.appliedJobs = [];
    } catch (e) {
      console.warn('Failed to parse applied jobs from localStorage', e);
      state.appliedJobs = [];
    }
    updateAppliedCountBadge();
  }

  function saveAppliedJobs() {
    try {
      localStorage.setItem(LOCAL_STORAGE_APPLIED_KEY, JSON.stringify(state.appliedJobs));
    } catch (e) {
      console.error('Failed to save applied jobs to localStorage', e);
    }
    updateAppliedCountBadge();
  }

  function isJobApplied(jobId) {
    return state.appliedJobs.some(item => String(item.id) === String(jobId));
  }

  function toggleMarkJobApplied(job) {
    const existingIndex = state.appliedJobs.findIndex(item => String(item.id) === String(job.id));
    if (existingIndex >= 0) {
      state.appliedJobs.splice(existingIndex, 1);
      showToast(`Removed "${job.title}" from Applied tracking`, 'info');
    } else {
      state.appliedJobs.unshift({
        id: String(job.id),
        title: job.title,
        company: job.company,
        url: job.url,
        source: job.source,
        score: job.match_score,
        applied_at: new Date().toISOString(),
        status: 'Applied',
        notes: '',
      });
      showToast(`Marked "${job.title}" at ${job.company} as Applied`, 'success');
    }
    saveAppliedJobs();
    renderFeed();
    if (state.selectedJobId === String(job.id)) {
      updateInspectorAppliedButton(job);
    }
    if (state.activeSection === 'appliedSection') {
      renderAppliedTable();
    }
  }

  function updateAppliedJobStatus(jobId, newStatus) {
    const item = state.appliedJobs.find(x => String(x.id) === String(jobId));
    if (item) {
      item.status = newStatus;
      saveAppliedJobs();
      renderAppliedStats();
      showToast(`Status updated to ${newStatus}`, 'info');
    }
  }

  function updateAppliedJobNotes(jobId, notes) {
    const item = state.appliedJobs.find(x => String(x.id) === String(jobId));
    if (item) {
      item.notes = notes;
      saveAppliedJobs();
    }
  }

  function removeAppliedJob(jobId) {
    state.appliedJobs = state.appliedJobs.filter(x => String(x.id) !== String(jobId));
    saveAppliedJobs();
    renderAppliedTable();
    renderFeed();
    showToast('Application record removed', 'info');
  }

  function updateAppliedCountBadge() {
    const badge = $('appliedNavCount');
    if (badge) badge.textContent = state.appliedJobs.length;
  }

  // =========================================================================
  // 6. Tag Input Component Implementation
  // =========================================================================
  function initTagInput(containerId, inputId, initialTags = []) {
    const container = $(containerId);
    const input = $(inputId);
    if (!container || !input) return null;

    let tags = [...initialTags];

    function renderTags() {
      container.querySelectorAll('.tag-chip-item').forEach(el => el.remove());
      tags.forEach((tag, idx) => {
        const chip = document.createElement('span');
        chip.className = 'tag-chip-item';
        chip.innerHTML = `${esc(tag)} <span class="tag-chip-remove" data-index="${idx}" aria-label="Remove ${esc(tag)}">&times;</span>`;
        container.insertBefore(chip, input);
      });
    }

    function addTag(value) {
      const clean = value.trim().replace(/^,+|,+$/g, '');
      if (clean && !tags.includes(clean)) {
        tags.push(clean);
        renderTags();
      }
      input.value = '';
    }

    function removeTag(index) {
      tags.splice(index, 1);
      renderTags();
    }

    input.addEventListener('keydown', e => {
      if (e.key === 'Enter' || e.key === ',') {
        e.preventDefault();
        addTag(input.value);
      } else if (e.key === 'Backspace' && input.value === '' && tags.length > 0) {
        removeTag(tags.length - 1);
      }
    });

    input.addEventListener('blur', () => {
      if (input.value.trim()) addTag(input.value);
    });

    container.addEventListener('click', e => {
      const removeBtn = e.target.closest('.tag-chip-remove');
      if (removeBtn) {
        e.stopPropagation();
        removeTag(Number(removeBtn.dataset.index));
      } else {
        input.focus();
      }
    });

    renderTags();

    tagInputs[containerId] = {
      getTags: () => [...tags],
      setTags: newTags => {
        tags = Array.isArray(newTags) ? [...newTags] : [];
        renderTags();
      },
    };

    return tagInputs[containerId];
  }

  // =========================================================================
  // 7. Toast Notifications System
  // =========================================================================
  function showToast(message, type = 'info', duration = 3000) {
    const container = $('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast-item toast-${type}`;
    const icon = type === 'success' ? SVG_ICONS.check : SVG_ICONS.checkCircle;
    toast.innerHTML = `${icon} <span>${esc(message)}</span>`;

    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(6px)';
      toast.style.transition = 'all 160ms ease';
      setTimeout(() => toast.remove(), 180);
    }, duration);
  }

  // =========================================================================
  // 8. Navigation & Routing
  // =========================================================================
  function setupNavigation() {
    const navLinks = [...document.querySelectorAll('.sidebar-nav-container .nav-link-item, .mobile-tab-btn')];
    const pageViews = [...document.querySelectorAll('.workspace-page')];

    function showSection(sectionId, pushHash = true) {
      const target = $(sectionId) || $('jobsSection');
      state.activeSection = target.id;

      pageViews.forEach(view => {
        const active = view === target;
        view.classList.toggle('active-page', active);
      });

      navLinks.forEach(link => {
        const active = link.dataset.section === target.id;
        link.classList.toggle('active', active);
      });

      const titleEl = $('currentViewTitle');
      if (titleEl) {
        titleEl.textContent =
          target.id === 'jobsSection' ? 'Jobs Feed' :
          target.id === 'appliedSection' ? 'Applied Jobs' :
          target.id === 'preferencesSection' ? 'Matching Preferences' :
          target.id === 'sourcesSection' ? 'Source Health' :
          target.id === 'accessSection' ? 'Account' : 'Jobs Feed';
      }

      if (target.id === 'appliedSection') {
        renderAppliedTable();
      } else if (target.id === 'sourcesSection') {
        renderSourceHealth();
      }

      if (pushHash) {
        const hash =
          target.id === 'appliedSection' ? '#applied' :
          target.id === 'preferencesSection' ? '#preferences' :
          target.id === 'sourcesSection' ? '#sources' :
          target.id === 'accessSection' ? '#access' : '#jobs';
        history.replaceState(null, '', hash);
      }
    }

    window.showSection = showSection;

    navLinks.forEach(link => {
      link.addEventListener('click', e => {
        e.preventDefault();
        showSection(link.dataset.section, true);
      });
    });

    window.addEventListener('popstate', handleHashRoute);
  }

  function handleHashRoute() {
    const hash = (location.hash || '').slice(1);
    if (hash.startsWith('job/')) {
      const id = decodeURIComponent(hash.slice(4));
      window.showSection('jobsSection', false);
      showJobInspector(id, false);
    } else if (hash === 'applied') {
      window.showSection('appliedSection', false);
    } else if (hash === 'preferences' || hash === 'filters') {
      window.showSection('preferencesSection', false);
    } else if (hash === 'sources') {
      window.showSection('sourcesSection', false);
    } else if (hash === 'access' || hash === 'settings') {
      window.showSection('accessSection', false);
    } else {
      window.showSection('jobsSection', false);
    }
  }

  // =========================================================================
  // 9. Opportunity Feed Rendering
  // =========================================================================
  function renderFeed() {
    const container = $('jobsListContainer');
    if (!container) return;

    const query = state.filters.search.toLowerCase().trim();
    const source = state.filters.source;
    const minScore = state.filters.minScore;
    const maxAge = state.filters.maxAge;
    const alertableOnly = state.filters.alertableOnly;
    const remoteOnly = state.filters.remoteOnly;

    let filtered = state.jobs.filter(job => {
      const ts = jobTimestamp(job);
      const textHaystack = [
        job.title,
        job.company,
        job.location,
        job.source,
        job.description,
        JSON.stringify(job.source_details || {}),
        ...(job.match_reasons || []),
        ...(job.skills_detected || []),
      ].join(' ').toLowerCase();

      const matchesQuery = !query || textHaystack.includes(query);
      const matchesSource = !source || job.source.toLowerCase() === source.toLowerCase();
      const configuredThreshold = state.config?.match_threshold ?? 55;
      const matchesScore = job.match_score >= minScore
        && (minScore < configuredThreshold || job.likely_match);
      const matchesAge = ageHours(ts) <= maxAge;
      const matchesAlertable = !alertableOnly || job.alertable;
      const matchesRemote = !remoteOnly || job.work_mode.toLowerCase().includes('remote') || job.location.toLowerCase().includes('remote');

      return matchesQuery && matchesSource && matchesScore && matchesAge && matchesAlertable && matchesRemote;
    });

    // Sorting
    if (state.filters.sort === 'match') {
      filtered.sort((a, b) => b.match_score - a.match_score || String(jobTimestamp(b) || '').localeCompare(String(jobTimestamp(a) || '')));
    } else if (state.filters.sort === 'company') {
      filtered.sort((a, b) => a.company.localeCompare(b.company));
    } else {
      filtered.sort((a, b) => String(jobTimestamp(b) || '').localeCompare(String(jobTimestamp(a) || '')) || b.match_score - a.match_score);
    }

    // Update Counter & Active Filter Pills
    const countText = $('feedCountText');
    if (countText) {
      countText.innerHTML = `Showing <b>${filtered.length}</b> of <b>${state.jobs.length}</b> opportunities`;
    }
    const navBadge = $('jobsNavCount');
    if (navBadge) navBadge.textContent = state.jobs.length;

    renderActiveFiltersBar();

    if (filtered.length === 0) {
      container.innerHTML = `
        <div style="text-align:center;padding:48px 24px;color:var(--text-muted);display:flex;flex-direction:column;align-items:center;gap:12px;">
          <svg class="icon icon-lg" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"></circle><line x1="21" x2="16.65" y1="21" y2="16.65"></line></svg>
          <h3 style="font-size:14px;color:var(--text-primary);font-weight:600;">No matching opportunities found</h3>
          <p style="font-size:12.5px;color:var(--text-muted);max-width:320px;">No job postings meet your active search and filter criteria.</p>
          <button type="button" class="btn-action-primary" id="resetFiltersEmptyBtn" style="margin-top:4px;">Clear all filters</button>
        </div>`;
      const resetBtn = $('resetFiltersEmptyBtn');
      if (resetBtn) resetBtn.onclick = clearAllFilters;
      return;
    }

    // Render Opportunity Rows
    container.innerHTML = filtered.map(job => {
      const ts = jobTimestamp(job);
      const isSelected = String(state.selectedJobId) === String(job.id);
      const applied = isJobApplied(job.id);
      const scoreTier = getScoreTierClass(job.match_score);

      const alertableBadge = job.alertable
        ? `<span class="tag-alertable-compact" title="${esc((job.alertability_reasons || []).join('; '))}">ALERTABLE</span>`
        : '';
      const notificationStatus = String(job.notification_status || 'not_eligible').toLowerCase();
      const configuredThreshold = state.config?.match_threshold ?? 55;
      const qualifiesForAlertPolicy = job.likely_match && job.match_score >= configuredThreshold;
      const notificationTooltip = [
        ...(job.notification_decision_reasons || []),
        ...(job.notification_last_error ? [`Delivery error: ${job.notification_last_error}`] : []),
      ].join('; ') || (job.alertability_reasons || []).join('; ');
      let notificationBadge = '';
      if (qualifiesForAlertPolicy) {
        if (notificationStatus === 'sent') {
          notificationBadge = `<span class="tag-alertable-compact" title="Telegram sent${job.notification_sent_at ? ` at ${esc(fmtTimestamp(job.notification_sent_at))}` : ''}">TELEGRAM SENT</span>`;
        } else if (notificationStatus === 'queued' || notificationStatus === 'sending') {
          notificationBadge = `<span class="tag-alertable-compact" title="${esc(notificationTooltip || 'Eligible opportunity queued for Telegram')}">TELEGRAM QUEUED</span>`;
        } else if (notificationStatus === 'failed') {
          notificationBadge = `<span class="tag-applied-compact" title="${esc(notificationTooltip || 'Telegram delivery failed')}">TELEGRAM FAILED</span>`;
        } else if (notificationStatus === 'suppressed') {
          notificationBadge = `<span class="tag-applied-compact" title="${esc(notificationTooltip || 'Suppressed by freshness or canonical-opportunity policy')}">NOT ALERTED</span>`;
        } else if (notificationStatus === 'pending' && job.alertable) {
          notificationBadge = `<span class="tag-alertable-compact" title="${esc(notificationTooltip || 'Waiting for the next notification decision cycle')}">TELEGRAM PENDING</span>`;
        } else if (!job.alertable) {
          const alertabilityText = (job.alertability_reasons || []).join('; ');
          const label = alertabilityText.toLowerCase().includes('disabled') ? 'TELEGRAM OFF' : 'NOT ALERTABLE';
          notificationBadge = `<span class="tag-applied-compact" title="${esc(notificationTooltip || alertabilityText || 'Does not pass notification policy')}">${label}</span>`;
        } else if (notificationStatus === 'not_eligible') {
          notificationBadge = `<span class="tag-applied-compact" title="No notification-ledger entry found for this job">NO ALERT RECORD</span>`;
        }
      }
      const appliedBadge = applied
        ? `<span class="tag-applied-compact">APPLIED</span>`
        : '';

      const reasons = job.match_reasons || [];
      const skills = job.skills_detected || [];
      
      const signalsList = [];
      skills.slice(0, 3).forEach(s => {
        signalsList.push(`<span class="signal-pill signal-skill">${esc(s)}</span>`);
      });
      reasons.slice(0, 3).forEach(r => {
        const formatted = formatIntelligenceReason(r);
        if (formatted.text && !skills.includes(r)) {
          signalsList.push(`<span class="signal-pill signal-${formatted.type}">${esc(formatted.text)}</span>`);
        }
      });

      const signalsHtml = signalsList.slice(0, 4).join('');

      return `
        <article class="opportunity-row ${isSelected ? 'is-selected' : ''} ${job.alertable ? 'is-alertable' : ''}" data-job-id="${esc(job.id)}" tabindex="0" role="article" aria-label="${esc(job.title)} at ${esc(job.company)}">
          <div class="opportunity-score-col score-tier-${scoreTier}">
            <span class="score-display-num">${job.match_score}%</span>
            <span class="score-display-label">MATCH</span>
            ${alertableBadge}
            ${notificationBadge}
            ${appliedBadge}
          </div>

          <div class="opportunity-main-col">
            <div class="opportunity-headline-row">
              <span class="opportunity-title">${esc(job.title)}</span>
              <span class="opportunity-source-text">${esc(job.source)}${job.canonical_opportunity_id ? ' · multi-source' : ''}</span>
            </div>
            <div class="opportunity-company-row">
              <span class="opportunity-company">${esc(job.company)}</span>
            </div>
            <div class="opportunity-meta-row">
              <span class="meta-item">${SVG_ICONS.mapPin} ${esc(job.location)}</span>
              <span class="meta-dot">·</span>
              <span class="meta-item">${SVG_ICONS.graduationCap} ${esc(job.experience_label)}</span>
              <span class="meta-dot">·</span>
              <span class="meta-item">${SVG_ICONS.clock} ${esc(fmtAge(ts))}</span>
            </div>
            ${signalsHtml ? `<div class="opportunity-signals-row">${signalsHtml}</div>` : ''}
          </div>

          <div class="opportunity-actions-col">
            <a href="${esc(job.url)}" target="_blank" rel="noopener" class="btn-action-primary" data-job-id="${esc(job.id)}" title="Apply directly on source website">
              <span>Apply Direct</span> ${SVG_ICONS.arrowUpRight}
            </a>
            <button type="button" class="btn-action-secondary ${applied ? 'is-applied' : ''} btn-action-applied" data-job-id="${esc(job.id)}" title="Track application">
              ${applied ? SVG_ICONS.check : SVG_ICONS.checkCircle}
              <span>${applied ? 'Applied' : 'Mark Applied'}</span>
            </button>
          </div>
        </article>
      `;
    }).join('');
  }

  function renderActiveFiltersBar() {
    const bar = $('activeFiltersBar');
    if (!bar) return;

    const tags = [];
    if (state.filters.search) {
      tags.push(`Query: "${esc(state.filters.search)}"`);
    }
    if (state.filters.source) {
      tags.push(`Source: ${esc(state.filters.source)}`);
    }
    if (state.filters.minScore > 0) {
      tags.push(`Score &ge; ${state.filters.minScore}%`);
    }
    if (state.filters.maxAge < 72) {
      tags.push(`Age &le; ${state.filters.maxAge}h`);
    }
    if (state.filters.alertableOnly) {
      tags.push('Alertable Only');
    }
    if (state.filters.remoteOnly) {
      tags.push('Remote Only');
    }

    if (tags.length === 0) {
      bar.innerHTML = '';
      return;
    }

    bar.innerHTML = tags.map(t => `<span class="active-pill">${t}</span>`).join('') +
      `<span class="clear-all-link" id="clearAllFiltersBtn">Clear all</span>`;

    const clearBtn = $('clearAllFiltersBtn');
    if (clearBtn) clearBtn.onclick = clearAllFilters;
  }

  function clearAllFilters() {
    const hadSearch = Boolean(String(state.filters.search || '').trim());
    state.filters.search = '';
    state.filters.source = '';
    state.filters.minScore = 0;
    state.filters.maxAge = 72;
    state.filters.sort = 'newest';
    state.filters.alertableOnly = false;
    state.filters.remoteOnly = false;

    $('searchInput').value = '';
    $('searchClearBtn').style.display = 'none';

    dropdowns.source?.setValue('', false);
    dropdowns.score?.setValue('0', false);
    dropdowns.age?.setValue('72', false);
    dropdowns.sort?.setValue('newest', false);

    $('toggleAlertable').classList.remove('active');
    $('toggleAlertable').setAttribute('aria-pressed', 'false');
    $('toggleRemote').classList.remove('active');
    $('toggleRemote').setAttribute('aria-pressed', 'false');

    if (hadSearch) {
      loadJobsFeed();
    } else {
      renderFeed();
    }
  }

  // =========================================================================
  // 10. Inspector Research Pane Logic
  // =========================================================================
  function showJobInspector(jobId, pushHistory = true) {
    const job = state.jobs.find(j => String(j.id) === String(jobId));
    if (!job) return;

    state.selectedJobId = String(job.id);

    document.querySelectorAll('.opportunity-row').forEach(row => {
      const active = row.dataset.jobId === String(job.id);
      row.classList.toggle('is-selected', active);
    });

    const pane = $('jobInspector');
    if (!pane) return;

    pane.classList.remove('is-hidden');

    $('inspSource').textContent = (job.source || 'DIRECT').toUpperCase();
    $('inspPostedAgo').textContent = fmtAge(jobTimestamp(job));
    $('inspTitle').textContent = job.title;
    $('inspCompany').textContent = job.company;
    $('inspScore').textContent = `${job.match_score}%`;
    $('inspExperience').textContent = job.experience_label;
    $('inspLocation').textContent = job.location;
    $('inspWorkMode').textContent = job.work_mode;
    $('inspSourcePosted').textContent = fmtTimestamp(job.source_posted_at, job.posted_precision);
    $('inspDiscovered').textContent = fmtTimestamp(job.discovered_at, 'minute');

    const alertBadge = $('inspAlertabilityBadge');
    if (alertBadge) {
      alertBadge.textContent = job.alertable ? 'High Priority Alert' : 'Standard Match';
      alertBadge.style.color = job.alertable ? 'var(--status-success)' : 'var(--text-muted)';
    }

    const applyBtn = $('inspApplyBtn');
    if (applyBtn) {
      applyBtn.href = job.url || '#';
    }

    const copyBtn = $('inspCopyBtn');
    if (copyBtn) {
      copyBtn.onclick = () => {
        navigator.clipboard.writeText(job.url || window.location.href);
        showToast('Opportunity link copied to clipboard', 'success');
      };
    }

    updateInspectorAppliedButton(job);

    const reasonsContainer = $('inspReasonsList');
    if (reasonsContainer) {
      const reasons = job.match_reasons || [];
      const alertReasons = job.alertability_reasons || [];
      const combined = [
        ...reasons.map(r => formatIntelligenceReason(r)),
        ...alertReasons.map(r => ({ text: r, type: 'neutral', icon: '•' })),
      ].filter(x => Boolean(x.text));

      if (combined.length === 0) {
        reasonsContainer.innerHTML = '<div style="font-size:12px;color:var(--text-muted);">No explicit match reasons recorded.</div>';
      } else {
        reasonsContainer.innerHTML = combined.map(item => `
          <div class="reason-bullet-row">
            <span class="reason-icon-check" style="color:${item.type === 'success' ? 'var(--status-success)' : item.type === 'warning' ? 'var(--status-warning)' : 'var(--text-muted)'};">${item.icon}</span>
            <span>${esc(item.text)}</span>
          </div>
        `).join('');
      }
    }

    const skillsContainer = $('inspSkillsContainer');
    const skillsCount = $('inspSkillsCount');
    if (skillsContainer && skillsCount) {
      const skills = job.skills_detected || [];
      skillsCount.textContent = `${skills.length} detected`;
      skillsContainer.innerHTML = skills.length > 0
        ? skills.map(s => `<span class="signal-pill signal-skill">${esc(s)}</span>`).join('')
        : '<span style="font-size:12px;color:var(--text-muted);">No configured skills detected.</span>';
    }

    renderSourceDetails(job);

    const descEl = $('inspDescription');
    if (descEl) {
      const description = job.description || 'The source did not expose a full description in this scan. Use the Apply Direct link to view the complete posting.';
      if (job.description_format === 'markdown') {
        descEl.innerHTML = renderMarkdownDescription(description);
      } else {
        descEl.textContent = description;
      }
    }

    if (pushHistory) {
      history.replaceState(null, '', `#job/${encodeURIComponent(job.id)}`);
    }
  }

  function renderMarkdownDescription(markdown) {
    const lines = String(markdown || '').replace(/\r\n?/g, '\n').split('\n');
    const blocks = [];

    const inline = value => {
      let html = esc(value);
      html = html.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
        '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
      html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
      html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
      const tick = String.fromCharCode(96);
      const codePattern = new RegExp(tick + '([^' + tick + ']+)' + tick, 'g');
      html = html.replace(codePattern, '<code>$1</code>');
      return html;
    };

    const isBullet = line => /^\s*[-*+]\s+/.test(line);
    const isNumbered = line => /^\s*\d+[.)]\s+/.test(line);
    const isHeading = line => /^\s*#{1,4}\s+/.test(line);

    let index = 0;
    while (index < lines.length) {
      const line = lines[index].trim();
      if (!line) {
        index += 1;
        continue;
      }

      if (isHeading(line)) {
        const heading = line.replace(/^#{1,4}\s+/, '');
        blocks.push('<h4>' + inline(heading) + '</h4>');
        index += 1;
        continue;
      }

      if (isBullet(line)) {
        const items = [];
        while (index < lines.length && isBullet(lines[index])) {
          const item = lines[index].replace(/^\s*[-*+]\s+/, '');
          items.push('<li>' + inline(item) + '</li>');
          index += 1;
        }
        blocks.push('<ul>' + items.join('') + '</ul>');
        continue;
      }

      if (isNumbered(line)) {
        const items = [];
        while (index < lines.length && isNumbered(lines[index])) {
          const item = lines[index].replace(/^\s*\d+[.)]\s+/, '');
          items.push('<li>' + inline(item) + '</li>');
          index += 1;
        }
        blocks.push('<ol>' + items.join('') + '</ol>');
        continue;
      }

      const paragraph = [line];
      index += 1;
      while (
        index < lines.length &&
        lines[index].trim() &&
        !isHeading(lines[index]) &&
        !isBullet(lines[index]) &&
        !isNumbered(lines[index])
      ) {
        paragraph.push(lines[index].trim());
        index += 1;
      }
      blocks.push('<p>' + paragraph.map(inline).join(' ') + '</p>');
    }

    return blocks.join('');
  }

  function renderSourceDetails(job) {
    const section = $('inspSourceDetailsSection');
    const metaContainer = $('inspSourceDetailsMeta');
    const skillsContainer = $('inspSourceKeySkills');
    if (!section || !metaContainer || !skillsContainer) return;

    const details = job.source_details || {};
    const education = details.education && typeof details.education === 'object'
      ? details.education
      : {};
    const valueText = value => Array.isArray(value)
      ? value.filter(Boolean).join(', ')
      : String(value || '').trim();

    const rows = [
      ['Role', valueText(details.role)],
      ['Industry Type', valueText(details.industry_type)],
      ['Department', valueText(details.department)],
      ['Employment Type', valueText(details.employment_type)],
      ['Role Category', valueText(details.role_category)],
      ['UG Education', valueText(education.ug)],
      ['PG Education', valueText(education.pg)],
      ['Other Education', valueText(education.ppg)],
    ].filter(([, value]) => value);

    const skills = Array.isArray(details.key_skills)
      ? [...new Set(details.key_skills.map(valueText).filter(Boolean))]
      : [];

    metaContainer.innerHTML = rows.map(([label, value]) =>
      '<div class="source-detail-row"><span class="source-detail-label">' +
      esc(label) + '</span><span class="source-detail-value">' +
      esc(value) + '</span></div>'
    ).join('');

    skillsContainer.innerHTML = skills.map(skill =>
      '<span class="signal-pill signal-skill">' + esc(skill) + '</span>'
    ).join('');

    section.classList.toggle('is-hidden', rows.length === 0 && skills.length === 0);
    const skillsHeading = $('inspSourceKeySkillsHeading');
    if (skillsHeading) skillsHeading.classList.toggle('is-hidden', skills.length === 0);
  }

  function closeJobInspector() {
    state.selectedJobId = null;
    const pane = $('jobInspector');
    if (pane) pane.classList.add('is-hidden');
    document.querySelectorAll('.opportunity-row').forEach(row => row.classList.remove('is-selected'));
    if (location.hash.startsWith('#job/')) {
      history.replaceState(null, '', '#jobs');
    }
  }

  function updateInspectorAppliedButton(job) {
    const markBtn = $('inspMarkAppliedBtn');
    const label = $('inspAppliedBtnLabel');
    if (!markBtn || !label) return;

    const applied = isJobApplied(job.id);
    markBtn.className = `btn-action-secondary ${applied ? 'is-applied' : ''}`;
    label.textContent = applied ? 'Applied (Click to Remove)' : 'Mark Applied';
    markBtn.onclick = () => toggleMarkJobApplied(job);
  }

  // =========================================================================
  // 11. Applied Jobs View Controller
  // =========================================================================
  function renderAppliedTable() {
    renderAppliedStats();
    const tbody = $('appliedTableBody');
    if (!tbody) return;

    if (state.appliedJobs.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="6">
            <div style="text-align:center;padding:48px 24px;color:var(--text-muted);display:flex;flex-direction:column;align-items:center;gap:12px;">
              ${SVG_ICONS.checkCircle}
              <h3 style="font-size:14px;color:var(--text-primary);font-weight:600;">No applied opportunities recorded</h3>
              <p style="font-size:12.5px;color:var(--text-muted);max-width:320px;">Click "Mark Applied" on any opportunity in the feed to track your submissions here.</p>
              <button type="button" class="btn-action-primary" onclick="window.showSection('jobsSection')">Go to Jobs Feed</button>
            </div>
          </td>
        </tr>`;
      return;
    }

    tbody.innerHTML = state.appliedJobs.map(item => `
      <tr data-applied-id="${esc(item.id)}">
        <td>
          <a href="${esc(item.url)}" target="_blank" rel="noopener" style="font-weight:600;color:var(--text-primary);display:block;">${esc(item.title)}</a>
          <span style="font-size:12px;color:var(--text-muted);">${esc(item.company)}</span>
        </td>
        <td><span class="signal-pill">${esc(item.source || 'direct')}</span></td>
        <td class="meta-mono" style="font-size:12px;">${esc(fmtTimestamp(item.applied_at, 'minute'))}</td>
        <td>
          <div id="statusMount_${esc(item.id)}" style="min-width:140px;"></div>
        </td>
        <td>
          <input type="text" class="inline-notes-field" placeholder="Add notes…" value="${esc(item.notes || '')}" data-id="${esc(item.id)}">
        </td>
        <td>
          <div style="display:flex;gap:6px;">
            <a href="${esc(item.url)}" target="_blank" rel="noopener" class="btn-action-secondary" title="View original posting">
              ${SVG_ICONS.arrowUpRight}
            </a>
            <button type="button" class="btn-action-secondary btn-delete-applied" data-id="${esc(item.id)}" title="Delete record" style="color:var(--status-error) !important;">
              ${SVG_ICONS.trash}
            </button>
          </div>
        </td>
      </tr>
    `).join('');

    state.appliedJobs.forEach(item => {
      const mount = $(`statusMount_${item.id}`);
      if (mount) {
        new CustomDropdown({
          container: mount,
          id: `status_${item.id}`,
          ariaLabel: 'Application Status',
          options: [
            { value: 'Applied', label: 'Applied' },
            { value: 'Interviewing', label: 'Interviewing' },
            { value: 'Offer', label: 'Offer' },
            { value: 'Rejected', label: 'Rejected' },
          ],
          value: item.status || 'Applied',
          onChange: (val) => updateAppliedJobStatus(item.id, val),
        });
      }
    });

    tbody.querySelectorAll('.inline-notes-field').forEach(inp => {
      inp.addEventListener('change', e => updateAppliedJobNotes(e.target.dataset.id, e.target.value));
    });

    tbody.querySelectorAll('.btn-delete-applied').forEach(btn => {
      btn.addEventListener('click', e => {
        const id = e.currentTarget.dataset.id;
        if (confirm('Remove this opportunity from Applied tracking?')) {
          removeAppliedJob(id);
        }
      });
    });
  }

  function renderAppliedStats() {
    const total = state.appliedJobs.length;
    const interviewing = state.appliedJobs.filter(x => x.status === 'Interviewing').length;
    const offers = state.appliedJobs.filter(x => x.status === 'Offer').length;
    const rejected = state.appliedJobs.filter(x => x.status === 'Rejected').length;

    if ($('appliedStatTotal')) $('appliedStatTotal').textContent = total;
    if ($('appliedStatInterviewing')) $('appliedStatInterviewing').textContent = interviewing;
    if ($('appliedStatOffers')) $('appliedStatOffers').textContent = offers;
    if ($('appliedStatRejected')) $('appliedStatRejected').textContent = rejected;
  }

  function exportAppliedData(format) {
    if (state.appliedJobs.length === 0) {
      showToast('No applied jobs to export', 'info');
      return;
    }

    if (format === 'json') {
      const blob = new Blob([JSON.stringify(state.appliedJobs, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `job_beeper_applied_${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } else {
      const headers = ['ID', 'Job Title', 'Company', 'Source', 'Score', 'Status', 'Date Applied', 'URL', 'Notes'];
      const rows = state.appliedJobs.map(j => [
        `"${j.id}"`,
        `"${(j.title || '').replace(/"/g, '""')}"`,
        `"${(j.company || '').replace(/"/g, '""')}"`,
        `"${j.source || ''}"`,
        `"${j.score || 0}"`,
        `"${j.status || 'Applied'}"`,
        `"${j.applied_at || ''}"`,
        `"${j.url || ''}"`,
        `"${(j.notes || '').replace(/"/g, '""')}"`,
      ]);
      const csvContent = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
      const blob = new Blob([csvContent], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `job_beeper_applied_${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    }
    showToast(`Exported ${state.appliedJobs.length} applied records`, 'success');
  }

  // =========================================================================
  // 12. Source Health Matrix Controller
  // =========================================================================
  function renderSourceHealth() {
    const tbody = $('sourceHealthTableBody');
    if (!tbody) return;

    if (state.sourceStatus.length === 0) {
      tbody.innerHTML = `<tr><td colspan="12" style="text-align:center;color:var(--text-muted);padding:var(--space-20);">Loading source telemetry…</td></tr>`;
      return;
    }

    tbody.innerHTML = state.sourceStatus.map(src => {
      const runtime = src.runtime || {};
      const metrics24h = src.last_24h || {};
      const measuredRuns = Number(metrics24h.measured_runs || 0);
      const totalRuns = Number(metrics24h.runs || 0);
      const metricsMeasured = measuredRuns > 0;
      const runCoverage = metricsMeasured
        ? `${measuredRuns} / ${totalRuns}`
        : '<span style="color:var(--text-muted);">Not measured</span>';
      const metricValue = value => metricsMeasured ? esc(value ?? 0) : '<span style="color:var(--text-muted);">Not measured</span>';
      const pageBoardFailures = metricsMeasured
        ? `${Number(metrics24h.pages_failed || 0)}/${Number(metrics24h.pages_attempted || 0)} pages · ${Number(metrics24h.boards_failed || 0)}/${Number(metrics24h.boards_attempted || 0)} boards`
        : '<span style="color:var(--text-muted);">Not measured</span>';
      const errorText = runtime.error || src.last_error || '';
      const relayFeed = src.source === 'naukri' ? src.last_feed : null;
      const relayFeedNote = relayFeed
        ? '<div style="color:' + (relayFeed.fresh ? 'var(--text-muted)' : 'var(--status-warning)') + ';font-size:11px;margin-bottom:4px;">Last good relay: ' + Math.floor(Number(relayFeed.age_seconds || 0) / 60) + 'm old · ' + esc(relayFeed.jobs_count ?? 0) + ' jobs · ' + (relayFeed.fresh ? 'fresh' : 'STALE') + ' · ' + (relayFeed.snapshot_unchanged ? 'same snapshot' : 'updated snapshot') + '</div>'
        : '';
      const runOutcome = src.last_run_outcome || runtime.last_run_outcome || '';
      const isPartial = runOutcome === 'partial_failed' || runOutcome === 'partial_rate_limited';
      const isError = Boolean(errorText) && !isPartial;
      const isRunning = Boolean(runtime.running);
      const isDisabled = src.enabled === false;
      const sourceLabels = {
        linkedin: 'LinkedIn',
        naukri: 'Naukri (Relay)',
        instahyre: 'Instahyre',
        greenhouse: 'Greenhouse',
        ashby: 'Ashby',
      };
      const sourceName = sourceLabels[src.source] || src.source;
      let statusBadge = `<span class="signal-pill signal-success">${SVG_ICONS.check} ACTIVE</span>`;
      if (isDisabled) {
        statusBadge = `<span class="signal-pill" style="background:var(--surface-muted);color:var(--text-muted);border-color:var(--border-default);">DISABLED</span>`;
      } else if (isRunning) {
        statusBadge = `<span class="signal-pill signal-warning">${SVG_ICONS.rotateCw} RUNNING</span>`;
      } else if (isPartial) {
        statusBadge = `<span class="signal-pill signal-warning">PARTIAL</span>`;
      } else if (isError) {
        statusBadge = `<span class="signal-pill" style="background:var(--status-error-subtle);color:var(--status-error);border-color:var(--status-error-border);">${SVG_ICONS.x} ERROR</span>`;
      }

      return `
        <tr>
          <td><b style="color:var(--text-primary);">${esc(sourceName)}</b></td>
          <td>${statusBadge}</td>
          <td class="meta-mono">${esc(src.jobs_seen ?? 0)}</td>
          <td class="meta-mono">${esc(src.new_jobs ?? 0)}</td>
          <td class="meta-mono">${runCoverage}</td>
          <td class="meta-mono">${metricValue(metrics24h.requests_attempted)}</td>
          <td class="meta-mono">${metricValue(metrics24h.http_429)}</td>
          <td class="meta-mono">${metricValue(metrics24h.retry_attempts)}</td>
          <td class="meta-mono">${metricsMeasured ? `${esc(metrics24h.avg_request_duration_ms ?? '—')} ms` : '<span style="color:var(--text-muted);">Not measured</span>'}</td>
          <td class="meta-mono">${pageBoardFailures}</td>
          <td class="meta-mono" style="font-size:12px;">${esc(fmtTimestamp(runtime.last_success, 'minute'))}</td>
          <td>
            ${relayFeedNote}
            ${errorText ? `<code style="color:${isPartial ? 'var(--status-warning)' : 'var(--status-error)'};font-family:var(--font-mono);font-size:11px;">${esc(errorText)}</code>` : '<span style="color:var(--text-muted);font-size:12px;">Operational</span>'}
          </td>
        </tr>
      `;
    }).join('');
  }

  // =========================================================================
  // 13. Configuration & Preferences Management
  // =========================================================================
  function populatePreferencesForm() {
    if (!state.config) return;
    const c = state.config;

    tagInputs.rolesTagContainer?.setTags(c.target_roles || []);
    tagInputs.locationsTagContainer?.setTags(c.locations || []);
    tagInputs.skillsTagContainer?.setTags(c.skills || []);
    tagInputs.excludeTitlesTagContainer?.setTags(c.title_exclude || []);
    tagInputs.excludeRolesTagContainer?.setTags(c.excluded_role_terms || []);

    if ($('cfgCandidateExp')) $('cfgCandidateExp').value = c.candidate_experience_years ?? '';
    if ($('cfgMinExp')) $('cfgMinExp').value = c.min_experience_years ?? '';
    if ($('cfgMaxExp')) $('cfgMaxExp').value = c.max_experience_years ?? 3;
    if ($('cfgMatchThreshold')) $('cfgMatchThreshold').value = c.match_threshold ?? 55;
    if ($('cfgMaxAge')) $('cfgMaxAge').value = c.max_age_hours ?? 72;

    if ($('cfgRemoteOnly')) $('cfgRemoteOnly').checked = Boolean(c.remote_only);
    if ($('cfgRequireExp')) $('cfgRequireExp').checked = Boolean(c.require_explicit_experience_for_alerts);
    if ($('cfgTelegramAlerts')) $('cfgTelegramAlerts').checked = c.notifications_enabled !== false;

    const enabled = c.source_enabled || {};
    document.querySelectorAll('#cfgSourcesWrap input[data-source]').forEach(input => {
      const src = input.dataset.source;
      input.checked = enabled[src] !== false;
    });

  }

  function collectPreferencesPayload() {
    const next = JSON.parse(JSON.stringify(state.config || {}));

    next.target_roles = tagInputs.rolesTagContainer?.getTags() || [];
    next.locations = tagInputs.locationsTagContainer?.getTags() || [];
    next.skills = tagInputs.skillsTagContainer?.getTags() || [];
    next.title_exclude = tagInputs.excludeTitlesTagContainer?.getTags() || [];
    next.excluded_role_terms = tagInputs.excludeRolesTagContainer?.getTags() || [];

    const cand = $('cfgCandidateExp')?.value.trim();
    const min = $('cfgMinExp')?.value.trim();

    next.candidate_experience_years = cand === '' ? null : Number(cand);
    next.min_experience_years = min === '' ? null : Number(min);
    next.max_experience_years = Number($('cfgMaxExp')?.value || 3);
    next.match_threshold = Number($('cfgMatchThreshold')?.value || 55);
    next.max_age_hours = Number($('cfgMaxAge')?.value || 72);

    next.remote_only = Boolean($('cfgRemoteOnly')?.checked);
    next.require_explicit_experience_for_alerts = Boolean($('cfgRequireExp')?.checked);
    next.notifications_enabled = Boolean($('cfgTelegramAlerts')?.checked);

    next.source_enabled = {};
    document.querySelectorAll('#cfgSourcesWrap input[data-source]').forEach(input => {
      next.source_enabled[input.dataset.source] = input.checked;
    });

    return next;
  }

  async function savePreferences() {
    const payload = collectPreferencesPayload();
    if ($('saveStatusMessage')) $('saveStatusMessage').textContent = 'Saving preferences…';

    try {
      const response = await authClient.request('/config', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (response.status === 401) {
        window.location.reload();
        return;
      }
      if (!response.ok) {
        showToast('Failed to save configuration', 'error');
        if ($('saveStatusMessage')) $('saveStatusMessage').textContent = 'Save failed.';
        return;
      }

      const data = await response.json();
      state.config = data.config;
      populatePreferencesForm();
      showToast('Preferences saved successfully. Live matching updated.', 'success');
      if ($('saveStatusMessage')) $('saveStatusMessage').textContent = 'Saved.';
    } catch (e) {
      showToast('Backend API unreachable', 'error');
      if ($('saveStatusMessage')) $('saveStatusMessage').textContent = 'API unreachable.';
    }
  }

  // =========================================================================
  // 14. API Fetchers & Live Background Polling
  // =========================================================================
  async function loadConfig() {
    try {
      const res = await authClient.request('/config', { cache: 'no-store' });
      if (res.status === 401) { window.location.reload(); return; }
      if (!res.ok) throw new Error('Config endpoint unavailable');
      const data = await res.json();
      state.config = data.config;
      populatePreferencesForm();
    } catch (e) {
      state.config = null;
      showToast('Live backend configuration unavailable. Check the dashboard API URL.', 'error', 5000);
    }
  }

  async function loadJobsFeed() {
    const requestId = ++jobsFeedRequestSequence;
    const refreshBtn = $('refreshFeedBtn');
    if (refreshBtn) refreshBtn.classList.add('is-loading');

    const params = new URLSearchParams({
      minutes: '4320',
      limit: '500',
    });
    const searchQuery = String(state.filters.search || '').trim();
    if (searchQuery) params.set('q', searchQuery);

    try {
      const [jobsRes, summaryRes] = await Promise.all([
        authClient.request('/jobs?' + params.toString(), { cache: 'no-store' }),
        authClient.request('/daily-summary', { cache: 'no-store' }),
      ]);

      if (jobsRes.status === 401 || summaryRes.status === 401) { window.location.reload(); return; }
      if (!jobsRes.ok || !summaryRes.ok) throw new Error('V2 API not available');

      const jobsData = await jobsRes.json();
      const summaryData = await summaryRes.json();
      if (requestId !== jobsFeedRequestSequence) return;

      state.jobs = (jobsData.jobs || []).map(normalizeJob).filter(Boolean);
      state.summary = summaryData;
      state.isStaticFallback = false;

      updateTelemetry(
        summaryData.total_jobs_discovered ?? state.jobs.length,
        summaryData.matched_jobs ?? 0,
        summaryData.alerts_sent ?? 0,
        `Live Feed`
      );
      populateSourceFilterOptions(state.jobs);
      renderFeed();
    } catch (err) {
      if (requestId !== jobsFeedRequestSequence) return;
      state.jobs = [];
      state.summary = null;
      state.isStaticFallback = false;
      updateTelemetry(0, 0, 0, 'Feed Offline');
      populateSourceFilterOptions([]);
      renderFeed();
      showToast('Live jobs API unavailable. Dashboard is offline; no fallback feed is shown.', 'error', 5000);
    } finally {
      if (requestId === jobsFeedRequestSequence && refreshBtn) {
        refreshBtn.classList.remove('is-loading');
      }
    }
  }

  async function loadSourceStatusTelemetry() {
    try {
      const res = await authClient.request('/source-status', { cache: 'no-store' });
      if (res.status === 401) { window.location.reload(); return; }
      if (!res.ok) throw new Error();
      const data = await res.json();
      state.sourceStatus = data.sources || [];
      if (state.activeSection === 'sourcesSection') {
        renderSourceHealth();
      }
    } catch (e) {
      state.sourceStatus = [
        { source: 'linkedin', runtime: { running: false, error: 'Dashboard API unavailable', last_success: null }, jobs_seen: 0, new_jobs: 0 },
        { source: 'naukri', runtime: { running: false, error: 'Dashboard API unavailable', last_success: null }, jobs_seen: 0, new_jobs: 0 },
        { source: 'greenhouse', runtime: { running: false, error: 'Dashboard API unavailable', last_success: null }, jobs_seen: 0, new_jobs: 0 },
        { source: 'instahyre', runtime: { running: false, error: 'Dashboard API unavailable', last_success: null }, jobs_seen: 0, new_jobs: 0 },
      ];
      if (state.activeSection === 'sourcesSection') {
        renderSourceHealth();
      }
    }
  }

  function updateTelemetry(discovered, matched, alerts, statusText) {
    if ($('telemetryDiscovered')) $('telemetryDiscovered').textContent = discovered;
    if ($('telemetryMatched')) $('telemetryMatched').textContent = matched;
    if ($('telemetryAlerts')) $('telemetryAlerts').textContent = alerts;
    if ($('connStatusText')) $('connStatusText').textContent = statusText;

    const dot = $('liveDot');
    if (dot) {
      dot.className = statusText.includes('Live') ? 'pulse-dot' : 'pulse-dot dot-warning';
    }
  }

  function populateSourceFilterOptions(_jobs) {
    const opts = [
      { value: '', label: 'All Sources' },
      { value: 'linkedin', label: 'LinkedIn' },
      { value: 'naukri', label: 'Naukri' },
      { value: 'greenhouse', label: 'Greenhouse' },
      { value: 'instahyre', label: 'Instahyre' },
    ];
    if (dropdowns.source) {
      const selected = opts.some(opt => opt.value === state.filters.source) ? state.filters.source : '';
      state.filters.source = selected;
      dropdowns.source.setOptions(opts, selected);
    }
  }

  // =========================================================================
  // 15. DOM Event Listeners & Hotkey (⌘K / Ctrl+K)
  // =========================================================================
  function bindEventListeners() {
    let searchDebounceTimer;
    const searchInp = $('searchInput');
    const searchClear = $('searchClearBtn');

    if (searchInp) {
      searchInp.addEventListener('input', e => {
        clearTimeout(searchDebounceTimer);
        const val = e.target.value;
        if (searchClear) searchClear.style.display = val ? 'inline-flex' : 'none';
        searchDebounceTimer = setTimeout(() => {
          state.filters.search = val.trim();
          loadJobsFeed();
        }, 250);
      });
    }

    if (searchClear) {
      searchClear.addEventListener('click', () => {
        if (searchInp) searchInp.value = '';
        searchClear.style.display = 'none';
        state.filters.search = '';
        loadJobsFeed();
      });
    }

    // Keyboard Shortcuts (⌘K / Ctrl+K for search, Escape for inspector)
    document.addEventListener('keydown', e => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        window.showSection('jobsSection');
        if (searchInp) {
          searchInp.focus();
          searchInp.select();
        }
      } else if (e.key === 'Escape') {
        if (state.selectedJobId) {
          closeJobInspector();
        } else if (searchInp && document.activeElement === searchInp) {
          searchInp.blur();
        }
      }
    });

    // Quick Toggles
    const alertableBtn = $('toggleAlertable');
    if (alertableBtn) {
      alertableBtn.addEventListener('click', () => {
        state.filters.alertableOnly = !state.filters.alertableOnly;
        alertableBtn.classList.toggle('active', state.filters.alertableOnly);
        alertableBtn.setAttribute('aria-pressed', String(state.filters.alertableOnly));
        renderFeed();
      });
    }

    const remoteBtn = $('toggleRemote');
    if (remoteBtn) {
      remoteBtn.addEventListener('click', () => {
        state.filters.remoteOnly = !state.filters.remoteOnly;
        remoteBtn.classList.toggle('active', state.filters.remoteOnly);
        remoteBtn.setAttribute('aria-pressed', String(state.filters.remoteOnly));
        renderFeed();
      });
    }

    // Refresh buttons
    if ($('refreshFeedBtn')) $('refreshFeedBtn').addEventListener('click', () => loadJobsFeed());
    if ($('refreshSourcesBtn')) $('refreshSourcesBtn').addEventListener('click', () => loadSourceStatusTelemetry());

    // Inspector close button
    if ($('inspCloseBtn')) $('inspCloseBtn').addEventListener('click', closeJobInspector);

    // Feed delegation for clicks
    const container = $('jobsListContainer');
    if (container) {
      container.addEventListener('click', e => {
        const row = e.target.closest('.opportunity-row');
        const appliedBtn = e.target.closest('.btn-action-applied');
        const applyDirectBtn = e.target.closest('.btn-action-primary');

        if (appliedBtn) {
          e.stopPropagation();
          const jobId = appliedBtn.dataset.jobId;
          const job = state.jobs.find(j => String(j.id) === String(jobId));
          if (job) toggleMarkJobApplied(job);
        } else if (applyDirectBtn) {
          e.stopPropagation();
        } else if (row) {
          showJobInspector(row.dataset.jobId, true);
        }
      });
    }

    // Applied exports
    if ($('exportAppliedJsonBtn')) $('exportAppliedJsonBtn').addEventListener('click', () => exportAppliedData('json'));
    if ($('exportAppliedCsvBtn')) $('exportAppliedCsvBtn').addEventListener('click', () => exportAppliedData('csv'));

    // Preferences save button
    if ($('savePreferencesBtn')) $('savePreferencesBtn').addEventListener('click', savePreferences);


  }

  // =========================================================================
  // 16. Initialize Filter Dropdowns
  // =========================================================================
  function initFilterDropdowns() {
    dropdowns.source = new CustomDropdown({
      container: 'sourceFilterMount',
      id: 'sourceFilter',
      ariaLabel: 'Filter by source',
      options: [{ value: '', label: 'All Sources' }],
      value: state.filters.source,
      onChange: (val) => {
        state.filters.source = val;
        renderFeed();
      },
    });

    dropdowns.score = new CustomDropdown({
      container: 'scoreFilterMount',
      id: 'scoreFilter',
      ariaLabel: 'Filter by match score',
      options: [
        { value: '0', label: 'All Matches' },
        { value: '90', label: '90%+ (High Priority)' },
        { value: '70', label: '70%+ (Strong Match)' },
        { value: '55', label: '55%+ (Threshold)' },
      ],
      value: String(state.filters.minScore),
      onChange: (val) => {
        state.filters.minScore = Number(val);
        renderFeed();
      },
    });

    dropdowns.age = new CustomDropdown({
      container: 'ageFilterMount',
      id: 'ageFilter',
      ariaLabel: 'Filter by freshness',
      options: [
        { value: '72', label: 'Last 72 hours' },
        { value: '24', label: 'Last 24 hours' },
        { value: '6', label: 'Last 6 hours' },
        { value: '1', label: 'Last hour' },
      ],
      value: String(state.filters.maxAge),
      onChange: (val) => {
        state.filters.maxAge = Number(val);
        renderFeed();
      },
    });

    dropdowns.sort = new CustomDropdown({
      container: 'sortFilterMount',
      id: 'sortFilter',
      ariaLabel: 'Sort order',
      options: [
        { value: 'newest', label: 'Newest First' },
        { value: 'match', label: 'Highest Match' },
        { value: 'company', label: 'Company (A-Z)' },
      ],
      value: state.filters.sort,
      onChange: (val) => {
        state.filters.sort = val;
        renderFeed();
      },
    });
  }

  // =========================================================================
  // 17. Authentication Gate & Main Application Lifecycle
  // =========================================================================
  let workspaceInitialized = false;

  function setAuthPanel(panelId) {
    ['authLoginPanel', 'authUserPanel', 'authUnavailablePanel'].forEach(id => {
      const panel = $(id);
      if (panel) panel.hidden = id !== panelId;
    });
    document.body.classList.remove('auth-ready');
  }

  function showLoginPanel(message = '') {
    setAuthPanel('authLoginPanel');
    if ($('authStatusMsg')) $('authStatusMsg').textContent = message;
  }

  function showUserPanel(user) {
    setAuthPanel('authUserPanel');
    if ($('authUserEmail')) $('authUserEmail').textContent = user.email;
  }

  function showUnavailablePanel() {
    setAuthPanel('authUnavailablePanel');
  }

  async function initializeWorkspace() {
    if (workspaceInitialized) return;
    workspaceInitialized = true;

    loadAppliedJobs();
    setupNavigation();
    initFilterDropdowns();

    initTagInput('rolesTagContainer', 'rolesInput');
    initTagInput('locationsTagContainer', 'locationsInput');
    initTagInput('skillsTagContainer', 'skillsInput');
    initTagInput('excludeTitlesTagContainer', 'excludeTitlesInput');
    initTagInput('excludeRolesTagContainer', 'excludeRolesInput');

    bindEventListeners();
    handleHashRoute();

    await loadConfig();
    await loadJobsFeed();
    await loadSourceStatusTelemetry();

    setInterval(loadJobsFeed, 10000);
    setInterval(loadSourceStatusTelemetry, 30000);
  }

  async function refreshAuthentication() {
    const result = await authClient.bootstrap({
      onAdmin: user => {
        document.body.classList.add('auth-ready');
        if ($('accountEmail')) $('accountEmail').textContent = user.email;
        if ($('accountRole')) $('accountRole').textContent = user.role;
      },
      onUser: showUserPanel,
      onLogin: () => showLoginPanel(),
      onError: showUnavailablePanel,
    });

    if (result.access === 'admin') await initializeWorkspace();
    return result;
  }

  async function signOut() {
    const buttons = [$('headerLogoutBtn'), $('accountLogoutBtn'), $('authUserLogoutBtn')].filter(Boolean);
    buttons.forEach(button => { button.disabled = true; });
    try {
      const response = await authClient.logout();
      if (!response.ok && response.status !== 401) {
        buttons.forEach(button => { button.disabled = false; });
        showToast('Could not sign out. Please try again.', 'error');
        return;
      }
      // Reload clears in-memory job data and stops all dashboard polling timers.
      window.location.reload();
    } catch (_error) {
      buttons.forEach(button => { button.disabled = false; });
      showToast('Authentication service unavailable. Please try again.', 'error');
    }
  }

  function bindAuthEvents() {
    const form = $('authLoginForm');
    if (form) {
      form.addEventListener('submit', async event => {
        event.preventDefault();
        const email = $('authEmail')?.value.trim() || '';
        const passwordInput = $('authPassword');
        const password = passwordInput?.value || '';
        const button = $('authLoginBtn');
        if (button) button.disabled = true;
        if ($('authStatusMsg')) $('authStatusMsg').textContent = 'Signing in…';

        try {
          const response = await authClient.login(email, password);
          if (!response.ok) {
            let detail = 'Sign-in failed. Check your credentials and try again.';
            try {
              const payload = await response.json();
              if (payload.detail) detail = payload.detail;
            } catch (_error) { /* Keep the generic message. */ }
            if ($('authStatusMsg')) $('authStatusMsg').textContent = detail;
            return;
          }
          if (passwordInput) passwordInput.value = '';
          await refreshAuthentication();
        } catch (_error) {
          if ($('authStatusMsg')) $('authStatusMsg').textContent = 'Authentication service unavailable. Please try again.';
        } finally {
          if (button) button.disabled = false;
        }
      });
    }

    ['headerLogoutBtn', 'accountLogoutBtn', 'authUserLogoutBtn'].forEach(id => {
      const button = $(id);
      if (button) button.addEventListener('click', signOut);
    });

    const retryButton = $('authRetryBtn');
    if (retryButton) retryButton.addEventListener('click', refreshAuthentication);
  }

  async function init() {
    initThemeSystem();
    bindAuthEvents();
    await refreshAuthentication();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
