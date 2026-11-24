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

  const LEGACY_APPLIED_STORAGE_KEY = 'job_beeper_applied_jobs_v1';
  const legacyAppliedStorageKey = () => state.currentUser && state.currentUser.id ? `${LEGACY_APPLIED_STORAGE_KEY}_user_${state.currentUser.id}` : LEGACY_APPLIED_STORAGE_KEY;
  const THEME_STORAGE_KEY = 'job_beeper_theme';

  const state = {
    jobs: [],
    feedPage: 1,
    feedPageSize: 20,
    pagination: null,
    selectedJobId: null,
    appliedJobs: [],
    config: null,
    summary: null,
    currentUser: null,
    isAdmin: false,
    userPreferences: null,
    sourceStatus: [],
    sourceStatusError: false,
    boardSchedulerStatus: null,
    discoveredBoards: [],
    globalCandidates: [],
    discoveredCompanies: [],
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

    const workplace = { remote: 'Remote', hybrid: 'Hybrid', on_site: 'On-site' }[raw.source_details?.workplace_type];
    let workMode = raw.work_mode || workplace || (
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
      experience_provenance: raw.experience_provenance || 'unknown',
      experience_confidence: raw.experience_confidence || 'unknown',
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
  // 5. Server-Owned Applied Jobs Store
  // =========================================================================
  async function loadAppliedJobs() {
    const storageKey = legacyAppliedStorageKey();
    let legacyRecords = [];
    try {
      const raw = localStorage.getItem(storageKey);
      const parsed = raw ? JSON.parse(raw) : [];
      legacyRecords = Array.isArray(parsed) ? parsed : [];
    } catch (error) {
      console.warn('Failed to read legacy applied jobs from localStorage', error);
    }

    const response = await authClient.request('/applications');
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || `Could not load applications (HTTP ${response.status}).`);

    if (legacyRecords.length) {
      let imported = 0;
      let alreadyPresent = 0;
      let skipped = 0;
      let importFailed = false;
      for (let offset = 0; offset < legacyRecords.length; offset += 500) {
        const batch = legacyRecords.slice(offset, offset + 500);
        const importResponse = await authClient.request('/applications/import', {
          method: 'POST', body: { applications: batch },
        });
        const importData = await importResponse.json().catch(() => ({}));
        if (!importResponse.ok) {
          importFailed = true;
          console.warn('Legacy application import failed', importData.detail || importResponse.status);
          break;
        }
        imported += Number(importData.imported || 0);
        alreadyPresent += Number(importData.already_present || 0);
        skipped += Number(importData.skipped || 0);
      }
      if (!importFailed && skipped === 0) {
        localStorage.removeItem(storageKey);
      }
      if (imported) showToast(`Imported ${imported} application record(s) from this browser`, 'success');
      if (skipped) showToast(`${skipped} old application record(s) could not be matched to a saved job. Your local copy was kept.`, 'warning', 7000);
      if (importFailed) showToast('Older application records could not all be imported. The browser copy was kept.', 'warning', 7000);
      if (imported || alreadyPresent) {
        const refreshed = await authClient.request('/applications');
        const refreshedData = await refreshed.json().catch(() => ({}));
        if (!refreshed.ok) throw new Error(refreshedData.detail || 'Could not refresh application records after import.');
        state.appliedJobs = Array.isArray(refreshedData.applications) ? refreshedData.applications : [];
      } else {
        state.appliedJobs = Array.isArray(data.applications) ? data.applications : [];
      }
    } else {
      state.appliedJobs = Array.isArray(data.applications) ? data.applications : [];
    }
    updateAppliedCountBadge();
  }

  function isJobApplied(jobId) {
    return state.appliedJobs.some(item => String(item.job_id ?? item.id) === String(jobId));
  }

  async function toggleMarkJobApplied(job) {
    try {
      const existing = state.appliedJobs.find(item => String(item.job_id ?? item.id) === String(job.id));
      const url = existing ? `/applications/${encodeURIComponent(existing.id)}` : '/applications';
      const response = await authClient.request(url, existing
        ? { method: 'DELETE' }
        : { method: 'POST', body: { job_id: Number(job.id) } });
      const data = response.status === 204 ? {} : await response.json().catch(() => ({}));
      if (!response.ok) {
        showToast(data.detail || `Could not update application tracking (HTTP ${response.status}).`, 'error', 7000);
        return;
      }

      if (existing) {
        state.appliedJobs = state.appliedJobs.filter(item => String(item.id) !== String(existing.id));
        showToast(`Removed "${job.title}" from Applied tracking`, 'info');
      } else {
        const item = data.application;
        if (item && !state.appliedJobs.some(current => String(current.id) === String(item.id))) {
          state.appliedJobs.unshift(item);
        }
        showToast(`Marked "${job.title}" at ${job.company} as Applied`, 'success');
      }
      updateAppliedCountBadge();
      renderFeed();
      if (state.selectedJobId === String(job.id)) updateInspectorAppliedButton(job);
      if (state.activeSection === 'appliedSection') renderAppliedTable();
    } catch (error) {
      showToast(error.message || 'Application tracking is temporarily unavailable.', 'error', 7000);
    }
  }

  async function updateAppliedJobStatus(applicationId, newStatus) {
    try {
      const response = await authClient.request(`/applications/${encodeURIComponent(applicationId)}`, {
        method: 'PATCH', body: { status: newStatus },
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        showToast(data.detail || 'Could not update application status.', 'error', 7000);
        return;
      }
      const index = state.appliedJobs.findIndex(item => String(item.id) === String(applicationId));
      if (index >= 0) state.appliedJobs[index] = data.application;
      renderAppliedStats();
      showToast(`Status updated to ${newStatus}`, 'info');
    } catch (error) {
      showToast(error.message || 'Could not update application status.', 'error', 7000);
    }
  }

  async function updateAppliedJobNotes(applicationId, notes) {
    try {
      const response = await authClient.request(`/applications/${encodeURIComponent(applicationId)}`, {
        method: 'PATCH', body: { notes },
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) showToast(data.detail || 'Could not save application notes.', 'error', 7000);
      else {
        const index = state.appliedJobs.findIndex(item => String(item.id) === String(applicationId));
        if (index >= 0) state.appliedJobs[index] = data.application;
      }
    } catch (error) {
      showToast(error.message || 'Could not save application notes.', 'error', 7000);
    }
  }

  async function removeAppliedJob(applicationId) {
    try {
      const response = await authClient.request(`/applications/${encodeURIComponent(applicationId)}`, { method: 'DELETE' });
      const data = response.status === 204 ? {} : await response.json().catch(() => ({}));
      if (!response.ok) {
        showToast(data.detail || 'Could not remove application record.', 'error', 7000);
        return;
      }
      state.appliedJobs = state.appliedJobs.filter(item => String(item.id) !== String(applicationId));
      updateAppliedCountBadge();
      renderAppliedTable();
      renderFeed();
      showToast('Application record removed', 'info');
    } catch (error) {
      showToast(error.message || 'Could not remove application record.', 'error', 7000);
    }
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

    function readRenderedTags() {
      return [...container.querySelectorAll('.tag-chip-item')]
        .map(chip => {
          const label = chip.cloneNode(true);
          label.querySelectorAll('.tag-chip-remove').forEach(remove => remove.remove());
          return label.textContent.trim();
        })
        .filter(Boolean);
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
      getTags: () => {
        // Commit any text still in the input, then prefer the chips the user
        // can actually see. This keeps a visual tag and the submitted payload
        // in sync even if the browser's blur/click ordering differs.
        if (input.value.trim()) addTag(input.value);
        const rendered = readRenderedTags();
        return rendered.length ? rendered : [...tags];
      },
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
      let target = $(sectionId) || $('jobsSection');
      if (!state.isAdmin && target.id === 'sourcesSection') {
        target = $('jobsSection');
        history.replaceState(null, '', '#jobs');
      }
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
        void loadSourceStatusTelemetry();
        loadOpenSourceTools();
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
      window.showSection('jobsSection', false);
      void openJobFromRoute(hash.slice(4));
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

    // The API applies filters and sorting before cutting the page.
    const jobs = state.jobs;
    const pagination = state.pagination || {
      page: state.feedPage, per_page: state.feedPageSize,
      total: jobs.length, total_pages: 1,
      has_previous: state.feedPage > 1, has_next: false,
    };
    const firstItem = jobs.length ? ((pagination.page - 1) * pagination.per_page) + 1 : 0;
    const lastItem = firstItem ? firstItem + jobs.length - 1 : 0;
    const countText = $('feedCountText');
    if (countText) {
      countText.innerHTML = 'Showing <b>' + firstItem +
        (lastItem > firstItem ? '–' + lastItem : '') +
        '</b> of <b>' + pagination.total + '</b> opportunities';
    }
    const navBadge = $('jobsNavCount');
    if (navBadge) navBadge.textContent = pagination.total;
    updateFeedPagination(pagination);

    renderActiveFiltersBar();

    if (jobs.length === 0) {
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
    container.innerHTML = jobs.map(job => {
      const ts = jobTimestamp(job);
      const isSelected = String(state.selectedJobId) === String(job.id);
      const applied = isJobApplied(job.id);
      const scoreTier = getScoreTierClass(job.match_score);
      const experienceProvenanceLabel = ({
        employer_stated: 'Employer-stated',
        description: 'From description',
        inferred: 'Text inference',
      })[job.experience_provenance] || '';
      const experienceEvidenceTitle = experienceProvenanceLabel
        ? 'Experience source: ' + experienceProvenanceLabel
          + '; rule-based evidence strength: ' + job.experience_confidence
        : 'Experience source or confidence unavailable';

      const alertableBadge = state.isAdmin && job.alertable
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
      if (state.isAdmin && qualifiesForAlertPolicy) {
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
              <span class="meta-item" title="${esc(experienceEvidenceTitle)}">${SVG_ICONS.graduationCap} ${esc(job.experience_label)}${experienceProvenanceLabel ? '<span class="experience-provenance-label">' + esc(experienceProvenanceLabel) + '</span>' : ''}</span>
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

  function updateFeedPagination(pagination) {
    const nav = $('feedPagination');
    const label = $('feedPageLabel');
    const previous = $('previousJobsPageBtn');
    const next = $('nextJobsPageBtn');
    if (!nav || !label || !previous || !next) return;
    const totalPages = Math.max(1, Number(pagination.total_pages || 0));
    nav.hidden = Number(pagination.total || 0) <= Number(pagination.per_page || state.feedPageSize);
    label.textContent = 'Page ' + pagination.page + ' of ' + totalPages;
    previous.disabled = !pagination.has_previous;
    next.disabled = !pagination.has_next;
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
    if (state.filters.maxAge > 0 && state.filters.maxAge < 72) {
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

    state.feedPage = 1;
    loadJobsFeed();
  }

  // =========================================================================
  // 10. Inspector Research Pane Logic
  // =========================================================================
  async function openJobFromRoute(id) {
    if (!/^\d+$/.test(id)) return;
    const onFeed = state.jobs.find(job => job.id === id);
    if (onFeed) {
      showJobInspector(onFeed, false);
      return;
    }

    const hash = location.hash;
    try {
      const response = await authClient.request(`/jobs/${id}`, { cache: 'no-store' });
      if (!response.ok) throw new Error(response.status === 404 ? 'Job not found.' : 'Could not open the job.');
      const job = normalizeJob(await response.json());
      if (location.hash === hash) showJobInspector(job, false);
    } catch (error) {
      if (location.hash === hash) showToast(error.message, 'error', 5000);
    }
  }

  function showJobInspector(job, pushHistory = true) {
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
    const inspectorExperienceSource = ({
      employer_stated: 'Employer-stated',
      description: 'From description',
      inferred: 'Text inference',
    })[job.experience_provenance] || 'Source unknown';
    const inspectorExperienceConfidence = job.experience_confidence !== 'unknown'
      ? ' · ' + job.experience_confidence + ' evidence'
      : '';
    $('inspExperience').textContent = job.experience_label + ' · ' + inspectorExperienceSource + inspectorExperienceConfidence;
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
    const title = $('inspSourceDetailsTitle');
    const metaContainer = $('inspSourceDetailsMeta');
    const skillsContainer = $('inspSourceKeySkills');
    if (!section || !metaContainer || !skillsContainer) return;
    const sourceLabel = sourceLabels[job.source];
    if (title) title.textContent = sourceLabel ? `${sourceLabel} Listing Details` : 'Listing Details';

    const details = job.source_details || {};
    const education = details.education && typeof details.education === 'object'
      ? details.education
      : {};
    const valueText = value => Array.isArray(value)
      ? value.filter(Boolean).join(', ')
      : String(value || '').trim();

    const rows = [
      ['Experience on listing', valueText(details.listing_experience)],
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
          <input type="text" class="inline-notes-field" maxlength="2000" placeholder="Add notes…" value="${esc(item.notes || '')}" data-id="${esc(item.id)}">
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
      const headers = ['Application ID', 'Job ID', 'Job Title', 'Company', 'Source', 'Score', 'Status', 'Date Applied', 'URL', 'Notes'];
      const rows = state.appliedJobs.map(j => [
        `"${j.id}"`,
        `"${j.job_id}"`,
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
  const sourceLabels = {
    linkedin: 'LinkedIn', naukri: 'Naukri', instahyre: 'Instahyre',
    greenhouse: 'Greenhouse', ashby: 'Ashby', lever: 'Lever', workday: 'Workday',
    smartrecruiters: 'SmartRecruiters', workable: 'Workable', keka: 'Keka',
    darwinbox: 'Darwinbox', recruitee: 'Recruitee', hirebase: 'Hirebase',
    teamtailor: 'Teamtailor', breezy: 'Breezy HR', bamboohr: 'BambooHR',
    jobvite: 'Jobvite', hireology: 'Hireology',
    rippling: 'Rippling ATS', oraclecloud: 'Oracle Cloud Recruiting', avature: 'Avature',
    ycombinator: 'Y Combinator', icims: 'iCIMS',
    freshteam: 'Freshteam', cutshort: 'Cutshort',
    hrsmart: 'HRsmart', ukg: 'UKG Pro / UltiPro', phenom: 'Phenom People', zoho: 'Zoho Recruit',
    taleo: 'Oracle Taleo', successfactors: 'SAP SuccessFactors', peoplestrong: 'PeopleStrong',
    eightfold: 'Eightfold AI', jibe: 'Jibe (iCIMS)',
  };

  function describeSourceStatus(source) {
    const runtime = source.runtime || {};
    const outcome = source.last_run_outcome || runtime.last_run_outcome;
    if (Date.parse(runtime.rate_limited_until) > Date.now() || outcome === 'rate_limited' || outcome === 'partial_rate_limited') {
      return { rank: 0, label: 'Rate limited', detail: 'The provider asked us to slow down.' };
    }
    if (source.source === 'naukri' && source.last_feed?.fresh === false) {
      return { rank: 0, label: 'Feed is stale', detail: 'Waiting for a fresh snapshot from the relay.' };
    }
    if (outcome === 'partial_failed') {
      return { rank: 0, label: 'Partial results', detail: 'Some boards or pages could not be fetched.' };
    }
    if (outcome === 'failed' || runtime.error || source.last_error) {
      return { rank: 0, label: 'Fetch failed', detail: 'Open Technical diagnostics for the error.' };
    }
    if (runtime.running) return { rank: 1, label: 'Fetching now' };
    if (!source.last_run) return { rank: 1, label: 'Waiting for first check' };
    return { rank: 2, label: 'Healthy' };
  }

  function renderSourceHealth() {
    const sources = state.sourceStatus;
    const enabled = [];
    const paused = [];
    for (const source of sources) {
      const name = sourceLabels[source.source] || source.source;
      if (source.enabled === false) {
        paused.push(name);
      } else {
        enabled.push({ ...source, name, status: describeSourceStatus(source) });
      }
    }
    enabled.sort((a, b) => a.status.rank - b.status.rank || a.name.localeCompare(b.name));
    paused.sort((a, b) => a.localeCompare(b));
    const issues = enabled.filter(source => source.status.rank === 0).length;
    const overview = $('sourceOverviewStatus');
    const message = state.sourceStatusError ? 'Source status is unavailable. Try Refresh status.'
      : !sources.length ? 'Loading sources…'
        : !enabled.length ? 'No sources enabled. Use Configure sources to turn on a provider.'
          : `${enabled.length} enabled · ${issues} ${issues === 1 ? 'needs' : 'need'} attention`;
    if (overview.textContent !== message) overview.textContent = message;
    $('sourceOverviewTable').hidden = !enabled.length;
    $('sourceOverviewTableBody').innerHTML = enabled.map(source => `
      <tr>
        <th scope="row">${esc(source.name)}</th>
        <td><span class="signal-pill ${source.status.rank === 0 ? 'signal-warning' : source.status.rank === 2 ? 'signal-success' : 'signal-neutral'}">${esc(source.status.label)}</span>
          ${source.status.detail ? `<span class="source-status-detail">${esc(source.status.detail)}</span>` : ''}</td>
        <td class="meta-mono">${Number(source.last_24h?.new_jobs || 0).toLocaleString('en-IN')}</td>
        <td>${esc(source.last_run ? fmtTimestamp(source.last_run, 'minute') : '—')}</td>
      </tr>
    `).join('');
    $('pausedSourcesPanel').hidden = !paused.length;
    $('pausedSourcesLabel').textContent = `Paused sources (${paused.length})`;
    $('pausedSourcesList').innerHTML = paused.map(name => `<li>${esc(name)}</li>`).join('');
    if ($('sourceDiagnostics').open) renderSourceDiagnostics();
  }

  function renderSourceDiagnostics() {
    const tbody = $('sourceHealthTableBody');
    if (!tbody) return;

    if (state.sourceStatus.length === 0) {
      tbody.innerHTML = `<tr><td colspan="12" style="text-align:center;color:var(--text-muted);padding:var(--space-20);">${state.sourceStatusError ? 'Source telemetry is unavailable.' : 'Loading source telemetry…'}</td></tr>`;
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

  function renderBoardSchedulerStatus() {
    const summary = $('boardSchedulerSummary');
    const tbody = $('boardSchedulerTableBody');
    const hostBody = $('boardSchedulerHostTableBody');
    if (!summary || !tbody || !hostBody) return;
    const data = state.boardSchedulerStatus;
    if (!data) {
      summary.textContent = 'Persistent board scheduler status is not available yet.';
      tbody.innerHTML = '<tr><td colspan="10" style="text-align:center;color:var(--text-muted);padding:var(--space-10);">No scheduler data.</td></tr>';
      hostBody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-muted);padding:var(--space-8);">No host budget data.</td></tr>';
      return;
    }
    const boards = Array.isArray(data.boards) ? data.boards : [];
    const hosts = Array.isArray(data.hosts) ? data.hosts : [];
    const active = Number(data.active_boards || 0);
    const inactive = Number(data.inactive_boards || 0);
    summary.textContent = `${active} active employer boards · ${inactive} inactive history records · up to ${Number(data.max_concurrent_hosts || 0)} concurrent API hosts · one active board per host · ${Number(data.host_min_interval_seconds || 0)}s minimum host spacing. ${boards.length ? 'All due times and outcomes are persisted in SQLite.' : 'No explicitly configured ATS employer boards are currently scheduled.'}`;

    tbody.innerHTML = boards.length ? boards.map(board => {
      const isActive = Boolean(board.is_active);
      const leased = Boolean(board.lease_until);
      const outcome = board.last_outcome || 'Not run yet';
      const outcomeClass = ['success'].includes(outcome) ? 'signal-success'
        : ['rate_limited', 'partial_rate_limited', 'partial_failed'].includes(outcome) ? 'signal-warning'
          : ['failed'].includes(outcome) ? 'signal-warning' : '';
      const result = leased
        ? `<span class="signal-pill signal-warning">RUNNING</span><div class="auth-description">Lease until ${esc(fmtTimestamp(board.lease_until, 'minute'))}</div>`
        : `<span class="signal-pill ${outcomeClass}">${esc(outcome.toUpperCase())}</span>`;
      const due = isActive ? fmtTimestamp(board.next_due_at, 'minute') : 'Inactive';
      const baseline = board.baseline_pending
        ? '<span class="signal-pill signal-warning">PENDING</span>'
        : '<span class="signal-pill signal-success">CLEAR</span>';
      return `<tr>
        <td><b>${esc(sourceLabels[board.source] || board.source)}</b></td>
        <td>${esc(board.company_name || 'Unknown employer')}</td>
        <td class="meta-mono">${esc(board.board_key)}</td>
        <td class="meta-mono">${esc(board.host_key)}</td>
        <td class="meta-mono">${esc(board.poll_interval_seconds)}s</td>
        <td class="meta-mono">${esc(due || '—')}</td>
        <td>${result}${board.last_error_type ? `<div class="auth-description">${esc(board.last_error_type)}</div>` : ''}</td>
        <td class="meta-mono">${esc(board.last_jobs_seen ?? 0)} / ${esc(board.last_jobs_new ?? 0)}</td>
        <td class="meta-mono">${esc(board.consecutive_failures ?? 0)}</td>
        <td>${baseline}</td>
      </tr>`;
    }).join('') : '<tr><td colspan="10" style="text-align:center;color:var(--text-muted);padding:var(--space-10);">No enabled, explicitly configured ATS employer boards.</td></tr>';

    hostBody.innerHTML = hosts.length ? hosts.map(host => {
      const leased = Boolean(host.lease_until);
      const cooldown = host.cooldown_until && Date.parse(host.cooldown_until) > Date.now();
      const leaseLabel = leased ? `${esc(host.lease_source || '')} · ${esc(host.lease_board_key || '')}` : 'Idle';
      const result = host.last_outcome ? esc(host.last_outcome.toUpperCase()) : 'Not run yet';
      return `<tr>
        <td class="meta-mono">${esc(host.host_key)}</td>
        <td>${leased ? '<span class="signal-pill signal-warning">IN USE</span>' : 'Idle'}<div class="auth-description">${leaseLabel}</div></td>
        <td class="meta-mono">${esc(fmtTimestamp(host.next_allowed_at, 'minute') || 'Now')}</td>
        <td class="meta-mono">${cooldown ? `<span class="signal-pill signal-warning">${esc(fmtTimestamp(host.cooldown_until, 'minute'))}</span>` : 'None active'}</td>
        <td class="meta-mono">${esc(host.http_429_count ?? 0)}</td>
        <td>${result}</td>
      </tr>`;
    }).join('') : '<tr><td colspan="6" style="text-align:center;color:var(--text-muted);padding:var(--space-8);">No API-host budgets have been recorded.</td></tr>';
  }

  async function loadBoardSchedulerStatus() {
    if (!state.isAdmin) return;
    try {
      const response = await authClient.request('/discovery/scheduler/status', { cache: 'no-store' });
      if (response.status === 401) { window.location.reload(); return; }
      if (!response.ok) throw new Error(`Persistent scheduler status unavailable (HTTP ${response.status}).`);
      state.boardSchedulerStatus = await response.json();
    } catch (error) {
      state.boardSchedulerStatus = null;
      const summary = $('boardSchedulerSummary');
      if (summary) summary.textContent = error.message || 'Persistent scheduler status unavailable.';
    }
    renderBoardSchedulerStatus();
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
      input.checked = enabled[src] === true;
    });
    const workdayBoards = $('cfgWorkdayBoards');
    if (workdayBoards) workdayBoards.value = JSON.stringify(c.workday_boards || [], null, 2);
    const smartRecruitersBoards = $('cfgSmartRecruitersBoards');
    if (smartRecruitersBoards) smartRecruitersBoards.value = JSON.stringify(c.smartrecruiters_boards || [], null, 2);
    const workableBoards = $('cfgWorkableBoards');
    if (workableBoards) workableBoards.value = JSON.stringify(c.workable_boards || [], null, 2);
    const kekaBoards = $('cfgKekaBoards');
    if (kekaBoards) kekaBoards.value = JSON.stringify(c.keka_boards || [], null, 2);
    const darwinboxBoards = $('cfgDarwinboxBoards');
    if (darwinboxBoards) darwinboxBoards.value = JSON.stringify(c.darwinbox_boards || [], null, 2);

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
    next.max_experience_years = Number($('cfgMaxExp')?.value || (state.isAdmin ? 3 : 30));
    next.match_threshold = Number($('cfgMatchThreshold')?.value || 55);
    next.max_age_hours = Number($('cfgMaxAge')?.value || 72);

    next.remote_only = Boolean($('cfgRemoteOnly')?.checked);
    next.require_explicit_experience_for_alerts = Boolean($('cfgRequireExp')?.checked);
    next.notifications_enabled = Boolean($('cfgTelegramAlerts')?.checked);

    next.source_enabled = {};
    document.querySelectorAll('#cfgSourcesWrap input[data-source]').forEach(input => {
      next.source_enabled[input.dataset.source] = input.checked;
    });
    const boardArrays = [
      ['cfgWorkdayBoards', 'workday_boards', 'Workday'],
      ['cfgSmartRecruitersBoards', 'smartrecruiters_boards', 'SmartRecruiters'],
      ['cfgWorkableBoards', 'workable_boards', 'Workable'],
      ['cfgKekaBoards', 'keka_boards', 'Keka'],
      ['cfgDarwinboxBoards', 'darwinbox_boards', 'Darwinbox'],
    ];
    for (const [elementId, configKey, label] of boardArrays) {
      const raw = $(elementId)?.value.trim() || '[]';
      try {
        next[configKey] = JSON.parse(raw);
      } catch {
        throw new Error(`${label} board configuration must be valid JSON.`);
      }
      if (!Array.isArray(next[configKey])) {
        throw new Error(`${label} board configuration must be a JSON array.`);
      }
    }

    return next;
  }

  function collectUserPreferencesPayload() {
    const payload = collectPreferencesPayload();
    return {
      target_roles: payload.target_roles, locations: payload.locations, skills: payload.skills,
      title_exclude: payload.title_exclude, excluded_role_terms: payload.excluded_role_terms,
      candidate_experience_years: payload.candidate_experience_years,
      min_experience_years: payload.min_experience_years, max_experience_years: payload.max_experience_years,
      match_threshold: payload.match_threshold, max_age_hours: payload.max_age_hours, remote_only: payload.remote_only,
    };
  }

  async function loadTelegramStatus() {
    const panel = $('telegramConnectPanel');
    if (panel) panel.hidden = true;
    const status = $('telegramConnectionStatus');
    try {
      const response = await authClient.request('/telegram/status', { cache: 'no-store' });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || 'Could not load Telegram status.');
      if (panel) panel.hidden = false;
      const connected = Boolean(data.connection?.connected);
      if (status) status.textContent = connected
        ? 'Telegram is connected to your Job Beeper account. Notifications are not enabled by this link.'
        : data.configured
          ? 'Telegram is not connected yet.'
          : 'Telegram linking is not configured by the administrator yet.';
      const createButton = $('createTelegramLinkBtn');
      if (createButton) createButton.hidden = !data.configured;
      const disconnectButton = $('disconnectTelegramBtn');
      if (disconnectButton) disconnectButton.hidden = !connected;
      const notificationToggle = $('telegramNotificationsEnabled');
      const notificationStatus = $('telegramNotificationSettingsStatus');
      try {
        const settingsResponse = await authClient.request('/notifications/settings', { cache: 'no-store' });
        const settingsData = await settingsResponse.json().catch(() => ({}));
        if (!settingsResponse.ok) throw new Error(settingsData.detail || 'Could not load notification settings.');
        if (notificationToggle) {
          notificationToggle.checked = Boolean(settingsData.settings?.enabled);
          notificationToggle.disabled = !connected;
        }
        if (notificationStatus) notificationStatus.textContent = settingsData.settings?.enabled
          ? `Job alerts are on. Only jobs discovered after ${new Date(settingsData.settings.enabled_at).toLocaleString()} are eligible.`
          : connected ? 'Job alerts are off. Turn them on to receive matching jobs discovered from that point forward.' : 'Connect Telegram before enabling alerts. Alerts are off by default.';
      } catch (settingsError) {
        if (notificationStatus) notificationStatus.textContent = settingsError.message || 'Could not load notification settings.';
      }
    } catch (error) {
      if (panel) panel.hidden = Boolean(state.isAdmin);
      if (!state.isAdmin && status) status.textContent = error.message || 'Could not load Telegram status.';
    }
  }

  const GOOGLE_ALERTS_GMAIL_DISCLOSURE_VERSION = '2026-11-22-v2';

  function formatGmailMessageCounts(counts = {}) {
    const entries = ['queued', 'processing', 'retry', 'processed', 'skipped', 'dead']
      .map(key => [key, Number(counts[key] || 0)])
      .filter(([, value]) => value > 0);
    return entries.length ? entries.map(([key, value]) => `${value} ${key}`).join(' · ') : 'No message counts yet';
  }

  function formatGmailDeliveryCounts(counts = {}) {
    const labels = [
      ['queued', 'queued'], ['sending', 'sending'], ['sent', 'sent'],
      ['failed', 'failed'], ['dead', 'dead'], ['cancelled', 'cancelled'],
    ];
    const entries = labels.map(([key, label]) => [label, Number(counts[key] || 0)])
      .filter(([, value]) => value > 0);
    return entries.length ? entries.map(([label, value]) => `${value} ${label}`).join(' · ') : 'No eligible historical alerts yet';
  }

  async function loadGoogleAlertsGmailStatus() {
    const panel = $('googleAlertsGmailPanel');
    if (!panel) return;
    panel.hidden = !state.isAdmin;
    if (!state.isAdmin) return;

    const status = $('googleAlertsGmailStatus');
    const syncProgress = $('googleAlertsGmailSyncProgress');
    const deliveryProgress = $('googleAlertsGmailDeliveryProgress');
    const connectButton = $('connectGoogleAlertsGmailBtn');
    const dataUseConsent = $('googleAlertsGmailDataUseConsent');
    const disconnectButton = $('disconnectGoogleAlertsGmailBtn');
    const pauseButton = $('pauseGoogleAlertsBackfillBtn');
    const resumeButton = $('resumeGoogleAlertsBackfillBtn');
    const retryButton = $('retryGoogleAlertsBackfillBtn');
    try {
      const response = await authClient.request('/integrations/google-alerts/gmail/status', { cache: 'no-store' });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || 'Could not load Gmail integration status.');

      const configured = Boolean(data.configured);
      const enabled = Boolean(data.enabled);
      const connected = Boolean(data.connected);
      if (status) {
        status.textContent = !configured
          ? 'Personal Gmail integration is not configured on the server yet.'
          : !enabled
            ? 'Personal Gmail integration is configured but disabled. The live-access and Google restricted-data policy gates must be cleared before connecting.'
            : connected
              ? 'Personal Gmail is connected. Only the dedicated Google Alerts label is processed; message bodies and alert search queries are not shown here.'
              : 'Ready to connect. Use the personal Gmail account that owns your Google Alerts and has the dedicated label/filter.';
      }
      if (connectButton) {
        connectButton.hidden = !configured || !enabled || connected;
        connectButton.disabled = !dataUseConsent || !dataUseConsent.checked;
      }
      if (disconnectButton) disconnectButton.hidden = !connected;

      const sync = data.sync || null;
      if (syncProgress) {
        if (!connected) {
          syncProgress.textContent = 'Sync will start after the Gmail connection is enabled.';
        } else if (!sync) {
          syncProgress.textContent = 'Connected. The initial label-scoped backfill has not started yet.';
        } else {
          const stageLabels = {
            scanning: 'Scanning historical messages',
            history_catchup: 'Catching up arrivals during the initial scan',
            draining: 'Processing verified historical results',
            complete: 'Initial backfill complete; incremental history reconciliation is active',
          };
          const updated = sync.updated_at ? ` · updated ${new Date(sync.updated_at).toLocaleString()}` : '';
          const lastError = sync.last_error_code ? ` · last sync error: ${sync.last_error_code}` : '';
          syncProgress.textContent = `${stageLabels[sync.backfill_state] || `Sync stage: ${sync.backfill_state || 'unknown'}`} · ${formatGmailMessageCounts(sync.message_counts)}${updated}${lastError}`;
        }
      }

      const notifications = data.notifications || {};
      const settings = notifications.settings || {};
      const delivery = notifications.historical_delivery || {};
      const paused = Boolean(settings.gmail_backfill_paused);
      if (deliveryProgress) {
        deliveryProgress.textContent = `Historical Telegram alerts: ${formatGmailDeliveryCounts(delivery)}${paused ? ' · paused' : ''}. Current preferences, freshness checks and Telegram opt-in still apply.`;
      }
      if (pauseButton) pauseButton.hidden = !connected || paused;
      if (resumeButton) resumeButton.hidden = !connected || !paused;
      const retryable = Number(delivery.failed || 0) + Number(delivery.dead || 0) + Number(delivery.cancelled || 0);
      if (retryButton) retryButton.hidden = !connected || retryable === 0;
    } catch (error) {
      if (status) status.textContent = error.message || 'Could not load Gmail integration status.';
    }
  }

  async function updateGoogleAlertsGmailBackfill(action) {
    const status = $('googleAlertsGmailDeliveryProgress');
    const buttons = [
      $('pauseGoogleAlertsBackfillBtn'), $('resumeGoogleAlertsBackfillBtn'),
      $('retryGoogleAlertsBackfillBtn'),
    ].filter(Boolean);
    buttons.forEach(button => { button.disabled = true; });
    try {
      const response = await authClient.request(`/integrations/google-alerts/gmail/notifications/${action}`, { method: 'POST' });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || `Could not ${action} historical Telegram alerts.`);
      if (status && action === 'retry') status.textContent = `${Number(data.requeued || 0)} failed historical notification(s) requeued. Delivery checks will run again before sending.`;
      await loadGoogleAlertsGmailStatus();
    } catch (error) {
      if (status) status.textContent = error.message || 'Could not update historical Telegram delivery.';
    } finally {
      buttons.forEach(button => { button.disabled = false; });
    }
  }

  async function disconnectGoogleAlertsGmail() {
    const button = $('disconnectGoogleAlertsGmailBtn');
    if (!window.confirm('Disconnect personal Gmail? This revokes the grant where possible and deletes Gmail-only credentials, sync metadata and private Gmail discoveries. Public jobs discovered independently are retained.')) return;
    if (button) button.disabled = true;
    try {
      const response = await authClient.request('/integrations/google-alerts/gmail/disconnect', { method: 'POST' });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || 'Could not disconnect personal Gmail.');
      await loadGoogleAlertsGmailStatus();
      showToast('Personal Gmail disconnected and Gmail-only data cleanup completed.', 'success');
    } catch (error) {
      showToast(error.message || 'Could not disconnect personal Gmail.', 'error', 7000);
    } finally {
      if (button) button.disabled = false;
    }
  }

  async function connectGoogleAlertsGmail() {
    const consent = $('googleAlertsGmailDataUseConsent');
    const button = $('connectGoogleAlertsGmailBtn');
    const status = $('googleAlertsGmailStatus');
    if (!consent || !consent.checked) {
      if (status) status.textContent = 'Read the Google Alerts data-use notice and confirm it before connecting Gmail.';
      return;
    }
    if (button) button.disabled = true;
    try {
      const response = await authClient.request('/integrations/google-alerts/gmail/consent', {
        method: 'POST',
        body: {
          accepted: true,
          disclosure_version: GOOGLE_ALERTS_GMAIL_DISCLOSURE_VERSION,
        },
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(authClient.formatErrorDetail(data.detail) || 'Could not record Gmail data-use consent.');
      window.location.assign(`${API}/integrations/google-alerts/gmail/connect`);
    } catch (error) {
      if (status) status.textContent = error.message || 'Could not record Gmail data-use consent.';
      if (button) button.disabled = false;
    }
  }

  async function updateTelegramNotificationSetting() {
    const toggle = $('telegramNotificationsEnabled');
    const status = $('telegramNotificationSettingsStatus');
    if (!toggle) return;
    toggle.disabled = true;
    try {
      const response = await authClient.request('/notifications/settings', {
        method: 'PUT', body: { enabled: Boolean(toggle.checked) },
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || 'Could not update notification settings.');
      if (status) status.textContent = data.settings.enabled
        ? 'Job alerts are on. Only jobs discovered after now are eligible; older jobs will not be sent.'
        : 'Job alerts are off. No further member alerts will be sent.';
    } catch (error) {
      toggle.checked = !toggle.checked;
      if (status) status.textContent = error.message || 'Could not update notification settings.';
    } finally {
      await loadTelegramStatus();
    }
  }

  async function createTelegramLink() {
    const status = $('telegramConnectionStatus');
    const button = $('createTelegramLinkBtn');
    const anchor = $('openTelegramLink');
    if (button) button.disabled = true;
    if (status) status.textContent = 'Generating a secure, one-time link…';
    try {
      const response = await authClient.request('/telegram/link', { method: 'POST' });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || 'Could not create Telegram link.');
      if (anchor) {
        anchor.href = data.url;
        anchor.hidden = false;
        anchor.textContent = `Open Job Beeper in Telegram (link expires in ${Math.ceil(data.expires_in_seconds / 60)} minutes)`;
      }
      if (status) status.textContent = 'Link created. Open it in Telegram and press Start. Return here and refresh the connection status. Generate a new link if this one expires.';
    } catch (error) {
      if (status) status.textContent = error.message || 'Could not create Telegram link.';
    } finally {
      if (button) button.disabled = false;
    }
  }

  async function disconnectTelegram() {
    const status = $('telegramConnectionStatus');
    const button = $('disconnectTelegramBtn');
    if (button) button.disabled = true;
    try {
      const response = await authClient.request('/telegram/link', { method: 'DELETE' });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || 'Could not disconnect Telegram.');
      const anchor = $('openTelegramLink');
      if (anchor) { anchor.hidden = true; anchor.removeAttribute('href'); }
      if (status) status.textContent = 'Telegram has been disconnected from this account.';
      await loadTelegramStatus();
    } catch (error) {
      if (status) status.textContent = error.message || 'Could not disconnect Telegram.';
    } finally {
      if (button) button.disabled = false;
    }
  }

  async function parseResumeForSuggestions() {
    const input = $('resumeUploadInput');
    const status = $('resumeParseStatus');
    const file = input?.files?.[0];
    if (!file) {
      if (status) status.textContent = 'Choose a PDF or DOCX resume first.';
      return;
    }
    if (status) status.textContent = 'Reading resume and extracting suggestions…';
    const body = new FormData();
    body.append('file', file);
    try {
      const response = await authClient.request('/preferences/resume', { method: 'POST', body });
      if (response.status === 401) { window.location.reload(); return; }
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.detail || 'Could not parse this resume.');
      const suggestions = result.suggestions || {};
      const mergeTags = (containerId, values) => {
        const existing = tagInputs[containerId]?.getTags() || [];
        const merged = [...existing];
        for (const value of (values || [])) {
          if (!merged.some(item => item.toLowerCase() === value.toLowerCase())) merged.push(value);
        }
        tagInputs[containerId]?.setTags(merged);
      };
      // Existing user edits take precedence; resume suggestions only fill empty controls.
      mergeTags('rolesTagContainer', suggestions.target_roles);
      mergeTags('locationsTagContainer', suggestions.locations);
      mergeTags('skillsTagContainer', suggestions.skills);
      const exp = $('cfgCandidateExp');
      if (exp && !exp.value && suggestions.candidate_experience_years != null) {
        exp.value = suggestions.candidate_experience_years;
      }
      const remote = $('cfgRemoteOnly');
      if (remote && suggestions.remote_only === true) remote.checked = true;
      const missing = result.missing_required_fields || [];
      if (status) {
        status.textContent = `Suggestions added for review. ${missing.length ? 'Still add: ' + missing.join(' and ') + '. ' : ''}Nothing has been saved yet. Review the fields, edit as needed, then choose Save Preferences.`;
      }
      input.value = '';
    } catch (error) {
      if (status) status.textContent = error.message || 'Resume parsing failed. You can still enter preferences manually.';
    }
  }

  async function savePreferences() {
    let payload;
    try {
      payload = state.isAdmin ? collectPreferencesPayload() : collectUserPreferencesPayload();
    } catch (error) {
      const message = error.message || 'Please check the configuration fields.';
      if ($('saveStatusMessage')) $('saveStatusMessage').textContent = message;
      showToast(message, 'error', 7000);
      return;
    }
    if ($('saveStatusMessage')) $('saveStatusMessage').textContent = 'Saving preferences…';

    if (!state.isAdmin) {
      const missing = [];
      if (!payload.target_roles?.length) missing.push('at least one target role');
      if (!payload.locations?.length && !payload.remote_only) missing.push('a target location or enable Remote only for worldwide remote jobs');
      if (missing.length) {
        const message = `Add ${missing.join(' and ')} before saving your preferences.`;
        if ($('saveStatusMessage')) $('saveStatusMessage').textContent = message;
        showToast(message, 'error', 7000);
        return;
      }
    }

    try {
      const response = await authClient.request(state.isAdmin ? '/config' : '/preferences', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (response.status === 401) {
        window.location.reload();
        return;
      }
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const detail = typeof errorData.detail === 'string' ? errorData.detail.trim() : '';
        const message = (detail || `Save failed (HTTP ${response.status}).`).slice(0, 320);
        showToast(message, 'error', 7000);
        if ($('saveStatusMessage')) $('saveStatusMessage').textContent = message;
        return;
      }

      const data = await response.json();
      state.config = data.config || data.preferences;
      state.userPreferences = state.isAdmin ? state.userPreferences : data.preferences;
      populatePreferencesForm();
      if (!state.isAdmin) {
        const notice = $('userOnboardingNotice');
        if (notice) notice.hidden = true;
        window.showSection?.('jobsSection', true);
        // Do not make preference persistence wait for the much heavier feed refresh.
        void loadJobsFeed();
      }
      showToast('Preferences saved successfully. Your personalized matching has been updated.', 'success');
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
      const res = await authClient.request(state.isAdmin ? '/config' : '/preferences', { cache: 'no-store' });
      if (res.status === 401) { window.location.reload(); return; }
      if (!res.ok) throw new Error('Config endpoint unavailable');
      const data = await res.json();
      state.config = data.config || data.preferences;
      state.userPreferences = state.isAdmin ? state.userPreferences : data.preferences;
      populatePreferencesForm();
      const onboardingNotice = $('userOnboardingNotice');
      if (onboardingNotice) onboardingNotice.hidden = Boolean(data.preferences?.onboarding_complete || state.isAdmin);
      const resumePanel = $('resumeAssistPanel');
      if (resumePanel) resumePanel.hidden = Boolean(state.isAdmin || data.preferences?.onboarding_complete);
      const telegramPanel = $('telegramConnectPanel');
      if (telegramPanel) telegramPanel.hidden = Boolean(state.isAdmin);
      if (!state.isAdmin && !data.preferences?.onboarding_complete) {
        window.showSection?.('preferencesSection', false);
      }
    } catch (e) {
      state.config = null;
      showToast('Live backend configuration unavailable. Check the dashboard API URL.', 'error', 5000);
    }
  }

  async function loadJobsFeed() {
    const requestId = ++jobsFeedRequestSequence;
    const refreshBtn = $('refreshFeedBtn');
    if (refreshBtn) refreshBtn.classList.add('is-loading');

    const sortParameters = {
      newest: { sort_by: 'created_at', sort_order: 'desc' },
      match: { sort_by: 'match_score', sort_order: 'desc' },
      company: { sort_by: 'company', sort_order: 'asc' },
    }[state.filters.sort] || { sort_by: 'created_at', sort_order: 'desc' };
    const params = new URLSearchParams({
      minutes: '4320',
      page: String(state.feedPage),
      per_page: String(state.feedPageSize),
      // Members without preferences browse the shared inventory until they
      // opt into personalized matching.
      status: state.isAdmin || !state.userPreferences?.onboarding_complete ? 'all' : 'matched',
      sort_by: sortParameters.sort_by,
      sort_order: sortParameters.sort_order,
    });
    const searchQuery = String(state.filters.search || '').trim();
    if (searchQuery) params.set('search', searchQuery);
    if (state.filters.source) params.set('source', state.filters.source);
    if (state.filters.minScore > 0) params.set('min_score', String(state.filters.minScore));
    if (state.filters.maxAge > 0) params.set('max_age_hours', String(state.filters.maxAge));
    if (state.filters.alertableOnly) params.set('alertable_only', 'true');
    if (state.filters.remoteOnly) params.set('remote_only', 'true');

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
      state.pagination = jobsData.pagination || {
        page: state.feedPage, per_page: state.feedPageSize,
        total: state.jobs.length, total_pages: 1,
        has_previous: false, has_next: false,
      };
      state.feedPage = state.pagination.page || state.feedPage;
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
      state.pagination = { page: state.feedPage, per_page: state.feedPageSize, total: 0, total_pages: 0, has_previous: false, has_next: false };
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
    if (!state.isAdmin) {
      state.sourceStatus = [];
      return;
    }
    if (state.activeSection !== 'sourcesSection') return;
    try {
      const res = await authClient.request('/source-status', { cache: 'no-store' });
      if (res.status === 401) { window.location.reload(); return; }
      if (!res.ok) throw new Error();
      const data = await res.json();
      state.sourceStatus = data.sources || [];
      state.sourceStatusError = false;
    } catch (e) {
      state.sourceStatus = [];
      state.sourceStatusError = true;
    }
    if (state.activeSection === 'sourcesSection') renderSourceHealth();
  }

  const sourceToolLoaders = {
    sourceBoardTools: loadDiscoveredBoards,
    sourceImportTools: () => Promise.all([
      loadDirectoryCoverageSummary(), loadGlobalDiscoveryCompanies(),
      loadGlobalDiscoveryCandidates(), loadCompanyWatchManifest(),
    ]),
    sourceDiagnostics: () => {
      renderSourceDiagnostics();
      return Promise.all([loadWorkdayInventoryStatus(), loadBoardSchedulerStatus()]);
    },
    hirebaseBudgetPanel: loadHirebaseBudgetStatus,
  };

  function loadOpenSourceTools() {
    for (const [id, load] of Object.entries(sourceToolLoaders)) {
      if ($(id)?.open) void load();
    }
  }

  function revealSourcePanel(sectionId, panelId) {
    if (!state.isAdmin) return;
    window.showSection(sectionId);
    const panel = $(panelId);
    if (!panel) return;
    panel.open = true;
    panel.querySelector('summary')?.focus({ preventScroll: true });
    panel.scrollIntoView({ block: 'start' });
  }

  async function loadDirectoryCoverageSummary() {
    if (!state.isAdmin) return;
    const target = $('directoryCoverageSummary');
    if (!target) return;
    try {
      const response = await authClient.request('/discovery/coverage-summary', { cache: 'no-store' });
      if (!response.ok) throw new Error(`Coverage summary unavailable (HTTP ${response.status}).`);
      const data = await response.json();
      const providers = Object.entries(data.providers || {}).map(([provider, item]) => {
        const statuses = item.by_status || {};
        return `${provider}: ${Number(item.total || 0).toLocaleString()} known · ${Number(statuses.active || 0)} monitoring · ${Number(statuses.verified || 0)} verified · ${Number(statuses.discovered || 0) + Number(statuses.reviewed || 0)} candidates`;
      });
      target.textContent = `${Number(data.employer_boards_known || 0).toLocaleString()} employer boards in the registry (${Number(data.directory_seed_candidates || 0).toLocaleString()} directory candidates). ${providers.join(' | ') || 'No boards yet.'} Market coverage percentage is not estimated.`;
    } catch (error) {
      target.textContent = error.message || 'Registry coverage summary unavailable.';
    }
  }

  async function loadWorkdayInventoryStatus() {
    if (!state.isAdmin) return;
    const target = $('workdayInventoryStatus');
    if (!target) return;
    try {
      const response = await authClient.request('/workday/inventory-status', { cache: 'no-store' });
      if (!response.ok) throw new Error(`Workday inventory status unavailable (HTTP ${response.status}).`);
      const data = await response.json();
      const boards = data.boards || [];
      target.textContent = boards.length
        ? boards.map(board => {
          const progress = ['truncated', 'in_progress_incomplete'].includes(board.status)
            ? `INCOMPLETE${board.status === 'in_progress_incomplete' ? ' · remaining partitions still processing' : ''}: ${board.truncated_reason || 'facet partition required'}`
            : board.status === 'complete'
              ? `Inventory completed; next weekly refresh ${board.next_inventory_due_at || 'not scheduled'}`
              : board.status === 'in_progress'
                ? `Next inventory offset ${Number(board.next_inventory_offset || 0).toLocaleString()} · next page after ${board.next_inventory_due_at || 'the throttle window'}`
                : 'Inventory scan not started';
          const partitions = board.facet_partitioned
            ? ` · facet partitions pending ${Number(board.pending_facet_partitions || 0)}${board.active_facet_query ? ` · active ${JSON.stringify(board.active_applied_facets || {})}` : ''}`
            : '';
          return `${board.company} (${board.board_key}): ${progress} · reported total ${board.reported_total ?? 'unknown'} · facets ${Number(board.facets_available || 0)}${partitions}`;
        }).join(' | ')
        : 'No Workday employer boards are configured.';
    } catch (error) {
      target.textContent = error.message || 'Workday inventory progress unavailable.';
    }
  }

  async function loadHirebaseBudgetStatus() {
    if (!state.isAdmin) return;
    const target = $('hirebaseBudgetStatus');
    if (!target) return;
    try {
      const response = await authClient.request('/hirebase/status', { cache: 'no-store' });
      if (!response.ok) throw new Error(`Budget status unavailable (HTTP ${response.status}).`);
      const data = await response.json();
      const budget = data.budget || {};
      const usage = Number(budget.locally_counted_period_jobs || 0);
      const today = Number(budget.locally_counted_today_jobs || 0);
      const provider = budget.provider_today || {};
      document.querySelectorAll('.hirebase-estimate-btn').forEach(button => {
        button.disabled = !data.api_key_configured;
        button.title = data.api_key_configured ? 'Run a zero-job-credit estimate.' : 'Add HIREBASE_API_KEY to the isolated development server environment first.';
      });
      target.textContent = `API key: ${data.api_key_configured ? 'configured on server' : 'not configured'} · Source: ${data.source_enabled ? 'enabled' : 'disabled'} · Local budget: ${usage}/${budget.monthly_hard_cap || 400} this billing period · ${today}/${budget.daily_hard_cap || 12} today · per ATS: ${budget.per_provider_daily_cap || 4}/day (Workday ${provider.workday || 0}, Keka ${provider.keka || 0}, Darwinbox ${provider.darwinbox || 0}). Uncertain requests remain reserved.`;
    } catch (error) {
      target.textContent = error.message || 'Hirebase budget status unavailable.';
    }
  }

  async function estimateHirebase(provider, button) {
    const results = $('hirebaseEstimateResults');
    if (!button || !results) return;
    button.disabled = true;
    results.textContent = `Estimating ${provider} results. This endpoint does not spend job credits…`;
    try {
      const response = await authClient.request('/hirebase/estimate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider, limit: 4 }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || `Estimate failed (HTTP ${response.status}).`);
      results.textContent = `${provider}: estimated ${Number(data.estimated_job_credits || 0)} result credits for a maximum ${data.result_limit} result query. Estimate cost: ${data.estimate_costs_job_credits}. Run is not started.`;
      await loadHirebaseBudgetStatus();
    } catch (error) {
      results.textContent = error.message || `${provider} estimate failed.`;
    } finally {
      button.disabled = false;
    }
  }

  function renderDiscoveredBoards() {
    const tbody = $('discoveredBoardsTableBody');
    if (!tbody) return;
    const boards = state.discoveredBoards || [];
    if (!boards.length) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--text-muted);padding:var(--space-12);">No discovered boards yet. Add a company website above.</td></tr>';
      return;
    }
    tbody.innerHTML = boards.map(board => {
      const collector = board.collector_available
        ? `<span style="color:var(--status-success);">${esc(board.collector_source)} available</span>`
        : '<span style="color:var(--text-muted);">Discovery only</span>';
      const review = esc(board.review_status || 'discovered');
      const verifyButton = board.collector_available && board.review_status !== 'verified' && board.review_status !== 'active'
        ? `<button type="button" class="btn-pill btn-pill-secondary board-verify-btn" data-board-id="${esc(board.id)}">Verify endpoint</button>`
        : '';
      const activateButton = board.review_status === 'verified'
        ? `<button type="button" class="btn-pill btn-pill-primary board-activate-btn" data-board-id="${esc(board.id)}">Activate source</button>`
        : '';
      const actions = board.review_status === 'active'
        ? `<span style="color:var(--status-success);">Active</span><button type="button" class="btn-pill btn-pill-secondary board-disable-btn" data-board-id="${esc(board.id)}">Disable board</button>`
        : `${verifyButton}${activateButton}<button type="button" class="btn-pill btn-pill-secondary board-review-btn" data-board-id="${esc(board.id)}" data-status="reviewed">Mark reviewed</button><button type="button" class="btn-pill btn-pill-secondary board-review-btn" data-board-id="${esc(board.id)}" data-status="rejected">Reject</button>`;
      return `<tr>
        <td><b>${esc(board.company_name)}</b><div style="font-size:11px;color:var(--text-muted);">${esc(board.domain)}</div></td>
        <td>${esc(board.provider)}</td>
        <td><a href="${esc(board.board_url)}" target="_blank" rel="noopener noreferrer">${esc(board.board_key)}</a>${board.directory_last_crawled ? `<div style="font-size:11px;color:var(--text-muted);">Directory snapshot: ${esc(board.directory_last_crawled)}</div>` : ''}</td>
        <td>${collector}</td>
        <td>${review}</td>
        <td><a href="${esc(board.discovered_from)}" target="_blank" rel="noopener noreferrer">Open page</a></td>
        <td style="display:flex;gap:4px;flex-wrap:wrap;">${actions}</td>
      </tr>`;
    }).join('');
    tbody.querySelectorAll('.board-review-btn').forEach(button => {
      button.addEventListener('click', () => reviewDiscoveredBoard(
        Number(button.dataset.boardId), button.dataset.status
      ));
    });
    tbody.querySelectorAll('.board-verify-btn').forEach(button => {
      button.addEventListener('click', () => verifyDiscoveredBoard(Number(button.dataset.boardId), button));
    });
    tbody.querySelectorAll('.board-activate-btn').forEach(button => {
      button.addEventListener('click', () => activateDiscoveredBoard(Number(button.dataset.boardId), button));
    });
    tbody.querySelectorAll('.board-disable-btn').forEach(button => {
      button.addEventListener('click', () => deactivateDiscoveredBoard(Number(button.dataset.boardId), button));
    });
  }

  async function importLastRoundDirectory(button) {
    const status = $('lastRoundDirectoryStatus');
    if (!button) return;
    button.disabled = true;
    if (status) status.textContent = 'Importing the local CC BY 4.0 directory snapshot…';
    try {
      const response = await authClient.request('/discovery/directories/last-round/import', { method: 'POST' });
      if (!response.ok) throw new Error(`Directory import failed (HTTP ${response.status}).`);
      const result = await response.json();
      if (status) status.textContent = `Snapshot rows: ${Number(result.companies_in_snapshot || 0).toLocaleString()}. New board records: ${Number(result.boards_added || 0).toLocaleString()}. None are verified or activated. Attribution: LastRound AI (CC BY 4.0).`;
      await loadDiscoveredBoards();
      await loadDirectoryCoverageSummary();
    } catch (error) {
      if (status) status.textContent = error.message || 'Directory import failed.';
    } finally {
      button.disabled = false;
    }
  }

  async function loadGlobalDiscoveryCompanies() {
    if (!state.isAdmin) return;
    try {
      const response = await authClient.request('/discovery/companies?limit=500', { cache: 'no-store' });
      if (!response.ok) throw new Error(`Could not load employers (HTTP ${response.status}).`);
      const data = await response.json();
      state.discoveredCompanies = data.companies || [];
      renderGlobalDiscoveryCandidates();
    } catch (error) {
      const target = $('globalCandidateStatus');
      if (target) target.textContent = error.message || 'Employer list unavailable.';
    }
  }

  async function loadGlobalDiscoveryCandidates() {
    if (!state.isAdmin) return;
    const tbody = $('globalCandidatesTableBody');
    if (tbody && !state.globalCandidates.length) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--text-muted);padding:var(--space-10);">Loading unmatched ATS candidates…</td></tr>';
    }
    try {
      const response = await authClient.request('/discovery/global-candidates?limit=500', { cache: 'no-store' });
      if (!response.ok) throw new Error(`Could not load global candidates (HTTP ${response.status}).`);
      const data = await response.json();
      state.globalCandidates = data.candidates || [];
      renderGlobalDiscoveryCandidates();
    } catch (error) {
      if (tbody) tbody.innerHTML = `<tr><td colspan="7" style="color:var(--status-error);padding:var(--space-10);">${esc(error.message || 'Candidate registry unavailable.')}</td></tr>`;
    }
  }

  async function loadCompanyWatchManifest() {
    if (!state.isAdmin) return;
    const status = $('companyWatchManifestStatus');
    const tbody = $('companyWatchManualReviewBody');
    try {
      const response = await authClient.request('/discovery/company-watch/manifest', { cache: 'no-store' });
      if (!response.ok) throw new Error('Could not load Company Watch manifest (HTTP ' + response.status + ').');
      const data = await response.json();
      if (!data.imported) {
        if (status) status.textContent = 'The pinned 100-company manifest has not been imported into this environment.';
        if (tbody) tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--text-muted);padding:var(--space-8);">No manifest rows imported yet.</td></tr>';
        return;
      }
      const manifest = data.manifest || {};
      const counts = data.classification_counts || {};
      if (status) status.textContent = 'Manifest ' + String(manifest.manifest_sha256 || '').slice(0, 12) + '… · ' +
        Number(manifest.rows_total || 0) + ' rows · ' + Number(counts.candidate_staged || 0) +
        ' ATS candidates staged · ' + Number(counts.manual_review || 0) +
        ' held for manual review. Import never verifies, activates, polls or notifies.';
      const rows = data.manual_review_rows || [];
      if (tbody) tbody.innerHTML = rows.length ? rows.map(row =>
        '<tr><td>' + esc(row.row_number) + '</td><td>' + esc(row.company_name) + '</td><td>' +
        esc(row.country || '—') + '</td><td>' + (row.scan_enabled ? 'Enabled in manifest' : 'Disabled in manifest') +
        '<div style="font-size:11px;color:var(--text-muted);">' + esc(row.scan_mode || '—') + ' · ' +
        esc(row.board_type || '—') + '</div></td><td>' + esc(row.verification_status || 'Not supplied') +
        '<div style="font-size:11px;color:var(--text-muted);">' + esc(row.verification_source || '') +
        '</div></td><td>' + esc(row.review_reason || 'Manual review required') +
        '</td><td><a href="' + esc(row.careers_url) +
        '" target="_blank" rel="noopener noreferrer">Open careers URL</a></td></tr>'
      ).join('') : '<tr><td colspan="7" style="text-align:center;color:var(--text-muted);padding:var(--space-8);">No manual-review rows.</td></tr>';
    } catch (error) {
      if (status) status.textContent = error.message || 'Company Watch manifest status unavailable.';
      if (tbody) tbody.innerHTML = '<tr><td colspan="7" style="color:var(--status-error);padding:var(--space-8);">Manifest review rows unavailable.</td></tr>';
    }
  }

  async function importCompanyWatchManifest(button) {
    const status = $('companyWatchManifestStatus');
    if (!button) return;
    button.disabled = true;
    try {
      if (status) status.textContent = 'Validating the pinned manifest. No database changes yet…';
      const previewResponse = await authClient.request('/discovery/company-watch/import', {
        method: 'POST', body: { dry_run: true },
      });
      const preview = await previewResponse.json().catch(() => ({}));
      if (!previewResponse.ok) throw new Error(preview.detail || 'Manifest validation failed (HTTP ' + previewResponse.status + ').');
      const counts = preview.classification_counts || {};
      const message = 'Validated ' + Number(preview.rows_total || 0) + ' manifest rows. ' +
        Number(counts.candidate_staged || 0) + ' ATS candidates will enter the existing review queue; ' +
        Number(counts.manual_review || 0) + ' records will be retained for manual review. No employers, links, verification, activation, polling, schedule changes or notifications will be created. Import now?';
      if (!window.confirm(message)) {
        if (status) status.textContent = 'Manifest validated. Import cancelled; no database changes were made.';
        return;
      }
      const response = await authClient.request('/discovery/company-watch/import', { method: 'POST', body: {} });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.detail || 'Manifest import failed (HTTP ' + response.status + ').');
      if (status) status.textContent = 'Imported ' + Number(result.rows_total || 0) + ' manifest rows: ' +
        Number(result.candidate_inserted || 0) + ' new candidates, ' +
        Number(result.manual_review_rows || 0) + ' manual-review rows. No employer records, links, verification, activation, schedules or notifications were created.';
      await Promise.all([loadCompanyWatchManifest(), loadGlobalDiscoveryCandidates()]);
    } catch (error) {
      if (status) status.textContent = error.message || 'Company Watch manifest import failed.';
    } finally {
      button.disabled = false;
    }
  }

  function renderGlobalDiscoveryCandidates() {
    const tbody = $('globalCandidatesTableBody');
    if (!tbody) return;
    const candidates = state.globalCandidates || [];
    if (!candidates.length) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--text-muted);padding:var(--space-10);">No unmatched ATS candidates yet. Add a captured public ATS URL above or wait for a discovery source.</td></tr>';
      return;
    }
    const companies = state.discoveredCompanies || [];
    tbody.innerHTML = candidates.map(candidate => {
      const linked = candidate.review_status === 'linked';
      const rejected = candidate.review_status === 'rejected';
      const options = companies.map(company =>
        `<option value="${esc(company.id)}">${esc(company.company_name)} (${esc(company.domain)})</option>`
      ).join('');
      const association = linked
        ? `<span style="color:var(--status-success);">Linked to ${esc(candidate.company_name || `company ${candidate.linked_company_id}`)}</span>`
        : rejected ? '<span style="color:var(--text-muted);">Rejected</span>'
          : companies.length
            ? `<select class="number-field-input global-candidate-company" data-candidate-id="${esc(candidate.id)}"><option value="">Choose existing employer…</option>${options}</select>`
            : '<span style="color:var(--text-muted);">Add an employer using the form below before linking.</span>';
      const linkedBoardStatus = candidate.board_review_status || 'unknown';
      const actions = linked
        ? `<span style="color:var(--text-muted);">Board status: ${esc(linkedBoardStatus)}</span>`
        : rejected ? ''
          : `${companies.length ? `<button type="button" class="btn-pill btn-pill-primary global-candidate-link" data-candidate-id="${esc(candidate.id)}">Link employer</button>` : ''}<button type="button" class="btn-pill btn-pill-secondary global-candidate-reject" data-candidate-id="${esc(candidate.id)}">Reject</button>`;
      const manifestContext = candidate.manifest_company_name
        ? '<div style="font-size:11px;color:var(--text-primary);margin-top:3px;">Manifest company: ' +
          esc(candidate.manifest_company_name) + ' · ' + esc(candidate.manifest_country || 'Country not supplied') +
          ' · row ' + esc(candidate.manifest_row_number) + '</div><div style="font-size:11px;color:var(--text-muted);">Identity evidence: ' +
          esc(candidate.manifest_verification_status || 'Not supplied') + ' · ' +
          esc(candidate.manifest_review_reason || 'Review required') + '</div>'
        : '';
      return `<tr>
        <td>${esc(candidate.provider)}</td>
        <td><a href="${esc(candidate.board_url)}" target="_blank" rel="noopener noreferrer">${esc(candidate.board_key)}</a><div style="font-size:11px;color:var(--text-muted);">${esc(candidate.candidate_host)}</div>${manifestContext}</td>
        <td>${esc(candidate.discovery_method)}<div style="font-size:11px;color:var(--text-muted);">${esc(candidate.source_reference)}</div></td>
        <td>${esc(candidate.source_captured_at || 'Not captured')}</td>
        <td>${esc(candidate.confidence)} · ${esc(candidate.review_status)}</td>
        <td>${association}</td>
        <td style="display:flex;gap:4px;flex-wrap:wrap;">${actions}</td>
      </tr>`;
    }).join('');
    tbody.querySelectorAll('.global-candidate-link').forEach(button => {
      button.addEventListener('click', () => {
        const id = Number(button.dataset.candidateId);
        const select = tbody.querySelector(`.global-candidate-company[data-candidate-id="${id}"]`);
        const companyId = Number(select?.value || 0);
        if (!companyId) {
          const status = $('globalCandidateStatus');
          if (status) status.textContent = 'Choose an existing employer before linking this candidate.';
          return;
        }
        void linkGlobalDiscoveryCandidate(id, companyId, button);
      });
    });
    tbody.querySelectorAll('.global-candidate-reject').forEach(button => {
      button.addEventListener('click', () => void rejectGlobalDiscoveryCandidate(Number(button.dataset.candidateId), button));
    });
  }

  async function importGlobalDiscoveryCandidate(event) {
    event.preventDefault();
    const button = $('importGlobalCandidateBtn');
    const status = $('globalCandidateStatus');
    const boardUrl = $('globalCandidateUrl')?.value.trim();
    const method = $('globalCandidateMethod')?.value;
    const sourceReference = $('globalCandidateReference')?.value.trim();
    const capturedInput = $('globalCandidateCapturedAt')?.value;
    if (!boardUrl || !sourceReference) {
      if (status) status.textContent = 'Enter a public ATS URL and its discovery reference.';
      return;
    }
    if (button) button.disabled = true;
    if (status) status.textContent = 'Validating and staging the ATS candidate. No employer will be created.';
    try {
      const capturedAt = capturedInput ? new Date(capturedInput).toISOString() : null;
      const response = await authClient.request('/discovery/global-candidates/import', {
        method: 'POST',
        body: { candidates: [{ board_url: boardUrl, discovery_method: method, source_reference: sourceReference, source_captured_at: capturedAt }] },
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || `Candidate import failed (HTTP ${response.status}).`);
      if (status) status.textContent = `Staged ${data.inserted || 0} new candidate(s), refreshed ${data.updated || 0}, preserved ${data.preserved_terminal || 0} linked/rejected, skipped ${data.skipped || 0}. No employer was created, verified or activated.`;
      if ($('globalCandidateUrl')) $('globalCandidateUrl').value = '';
      if ($('globalCandidateReference')) $('globalCandidateReference').value = '';
      if ($('globalCandidateCapturedAt')) $('globalCandidateCapturedAt').value = '';
      await loadGlobalDiscoveryCandidates();
    } catch (error) {
      if (status) status.textContent = error.message || 'Could not stage ATS candidate.';
    } finally {
      if (button) button.disabled = false;
    }
  }

  async function linkGlobalDiscoveryCandidate(candidateId, companyId, button) {
    if (button) button.disabled = true;
    const status = $('globalCandidateStatus');
    if (status) status.textContent = `Linking candidate ${candidateId} to the selected existing employer…`;
    try {
      const response = await authClient.request(`/discovery/global-candidates/${encodeURIComponent(candidateId)}/link`, {
        method: 'POST', body: { company_id: companyId },
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || `Candidate link failed (HTTP ${response.status}).`);
      if (status) status.textContent = `Linked to ${data.company_name}. Board remains ${data.board_review_status}; verified=${data.verified}; activated=${data.activated}.`;
      await Promise.all([loadGlobalDiscoveryCandidates(), loadDiscoveredBoards(), loadDirectoryCoverageSummary()]);
    } catch (error) {
      if (status) status.textContent = error.message || 'Could not link ATS candidate.';
    } finally {
      if (button) button.disabled = false;
    }
  }

  async function rejectGlobalDiscoveryCandidate(candidateId, button) {
    if (!window.confirm('Reject this unmatched ATS candidate? Re-discovery will not revive a rejected candidate.')) return;
    if (button) button.disabled = true;
    const status = $('globalCandidateStatus');
    try {
      const response = await authClient.request(`/discovery/global-candidates/${encodeURIComponent(candidateId)}/review`, {
        method: 'POST', body: { status: 'rejected' },
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || `Candidate rejection failed (HTTP ${response.status}).`);
      if (status) status.textContent = `Candidate ${candidateId} rejected. Future imports will preserve this decision.`;
      await loadGlobalDiscoveryCandidates();
    } catch (error) {
      if (status) status.textContent = error.message || 'Could not reject ATS candidate.';
    } finally {
      if (button) button.disabled = false;
    }
  }

  async function loadDiscoveredBoards() {
    if (!state.isAdmin) return;
    const tbody = $('discoveredBoardsTableBody');
    if (tbody && !state.discoveredBoards?.length) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--text-muted);padding:var(--space-12);">Loading discovered boards…</td></tr>';
    }
    try {
      const response = await authClient.request('/discovery/boards?limit=1000', { cache: 'no-store' });
      if (!response.ok) throw new Error(`Could not load boards (HTTP ${response.status}).`);
      const data = await response.json();
      state.discoveredBoards = data.boards || [];
      renderDiscoveredBoards();
    } catch (error) {
      if (tbody) tbody.innerHTML = `<tr><td colspan="7" style="color:var(--status-error);padding:var(--space-12);">${esc(error.message || 'Board registry unavailable.')}</td></tr>`;
    }
  }

  async function discoverCompanyBoards(event) {
    event.preventDefault();
    const button = $('discoverCompanyBtn');
    const status = $('boardDiscoveryStatus');
    const companyName = $('discoveryCompanyName')?.value.trim();
    const websiteUrl = $('discoveryWebsiteUrl')?.value.trim();
    const careersUrl = $('discoveryCareersUrl')?.value.trim();
    const country = $('discoveryCountry')?.value.trim();
    if (!companyName || !websiteUrl) return;
    if (button) button.disabled = true;
    if (status) status.textContent = 'Scanning public company and careers pages…';
    try {
      const response = await authClient.request('/discovery/companies/scan', {
        method: 'POST',
        body: { company_name: companyName, website_url: websiteUrl, careers_url: careersUrl || null, country: country || null },
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || `Discovery failed (HTTP ${response.status}).`);
      const found = Number(data.boards_discovered || 0);
      if (status) status.textContent = `${data.company_name}: checked ${data.pages_checked} public page(s), found ${found} board candidate(s). No source was enabled.`;
      if ($('discoveryCompanyName')) $('discoveryCompanyName').value = '';
      if ($('discoveryWebsiteUrl')) $('discoveryWebsiteUrl').value = '';
      if ($('discoveryCareersUrl')) $('discoveryCareersUrl').value = '';
      await Promise.all([loadDiscoveredBoards(), loadGlobalDiscoveryCompanies()]);
    } catch (error) {
      if (status) status.textContent = error.message || 'Company discovery failed.';
      showToast(error.message || 'Company discovery failed.', 'error', 7000);
    } finally {
      if (button) button.disabled = false;
    }
  }

  async function verifyDiscoveredBoard(boardId, button) {
    if (button) button.disabled = true;
    if ($('boardDiscoveryStatus')) $('boardDiscoveryStatus').textContent = `Checking public ATS endpoint for board ${boardId}…`;
    try {
      const response = await authClient.request(`/discovery/boards/${encodeURIComponent(boardId)}/verify`, { method: 'POST' });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || `Board verification failed (HTTP ${response.status}).`);
      if ($('boardDiscoveryStatus')) $('boardDiscoveryStatus').textContent = `${data.provider}: endpoint verified, ${data.jobs_observed} public listing(s) visible. Scheduler is still disabled.`;
      await loadDiscoveredBoards();
    } catch (error) {
      if ($('boardDiscoveryStatus')) $('boardDiscoveryStatus').textContent = error.message || 'Board verification failed.';
      showToast(error.message || 'Board verification failed.', 'error', 7000);
    } finally {
      if (button) button.disabled = false;
    }
  }

  async function deactivateDiscoveredBoard(boardId, button) {
    if (!window.confirm('Disable this employer board? Other boards using the same ATS will continue running.')) return;
    if (button) button.disabled = true;
    const status = $('boardDiscoveryStatus');
    if (status) status.textContent = `Disabling board ${boardId}…`;
    try {
      const response = await authClient.request(`/discovery/boards/${encodeURIComponent(boardId)}/deactivate`, { method: 'POST' });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || `Board disable failed (HTTP ${response.status}).`);
      if (status) status.textContent = `${data.source}: board disabled; ${data.remaining_boards} board(s) remain in this collector. Changes take effect on the next poll.`;
      await Promise.all([loadDiscoveredBoards(), loadSourceStatusTelemetry()]);
    } catch (error) {
      if (status) status.textContent = error.message || 'Board disable failed.';
      showToast(error.message || 'Board disable failed.', 'error', 7000);
    } finally {
      if (button) button.disabled = false;
    }
  }

  async function activateDiscoveredBoard(boardId, button) {
    if (button) button.disabled = true;
    if ($('boardDiscoveryStatus')) $('boardDiscoveryStatus').textContent = `Activating verified board ${boardId}…`;
    try {
      const response = await authClient.request(`/discovery/boards/${encodeURIComponent(boardId)}/activate`, { method: 'POST' });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || `Activation failed (HTTP ${response.status}).`);
      if ($('boardDiscoveryStatus')) $('boardDiscoveryStatus').textContent = `${data.provider}: source enabled at ${data.poll_interval_seconds}s. First poll is silent baseline inventory.`;
      await Promise.all([loadDiscoveredBoards(), loadSourceStatusTelemetry()]);
    } catch (error) {
      if ($('boardDiscoveryStatus')) $('boardDiscoveryStatus').textContent = error.message || 'Board activation failed.';
      showToast(error.message || 'Board activation failed.', 'error', 7000);
    } finally {
      if (button) button.disabled = false;
    }
  }

  async function reviewDiscoveredBoard(boardId, reviewStatus) {
    try {
      const response = await authClient.request(`/discovery/boards/${encodeURIComponent(boardId)}/review`, {
        method: 'POST', body: { status: reviewStatus },
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || `Review failed (HTTP ${response.status}).`);
      if ($('boardDiscoveryStatus')) $('boardDiscoveryStatus').textContent = `Board ${boardId} marked ${reviewStatus}. This does not enable polling.`;
      await loadDiscoveredBoards();
    } catch (error) {
      showToast(error.message || 'Could not update board review status.', 'error', 7000);
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
      ...Object.entries(sourceLabels).map(([value, label]) => ({ value, label })),
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
          state.feedPage = 1;
          loadJobsFeed();
        }, 250);
      });
    }

    if (searchClear) {
      searchClear.addEventListener('click', () => {
        if (searchInp) searchInp.value = '';
        searchClear.style.display = 'none';
        state.filters.search = '';
        state.feedPage = 1;
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
        state.feedPage = 1;
        loadJobsFeed();
      });
    }

    const remoteBtn = $('toggleRemote');
    if (remoteBtn) {
      remoteBtn.addEventListener('click', () => {
        state.filters.remoteOnly = !state.filters.remoteOnly;
        remoteBtn.classList.toggle('active', state.filters.remoteOnly);
        remoteBtn.setAttribute('aria-pressed', String(state.filters.remoteOnly));
        state.feedPage = 1;
        loadJobsFeed();
      });
    }

    // Refresh buttons
    if ($('refreshFeedBtn')) $('refreshFeedBtn').addEventListener('click', () => loadJobsFeed());
    $('refreshSourcesBtn')?.addEventListener('click', () => {
      void loadSourceStatusTelemetry();
      loadOpenSourceTools();
    });
    $('configureSourcesBtn')?.addEventListener('click', () => revealSourcePanel('preferencesSection', 'sourceSettings'));
    $('sourceSettingsBoardLink')?.addEventListener('click', event => {
      event.preventDefault();
      revealSourcePanel('sourcesSection', 'sourceBoardTools');
    });
    for (const [id, load] of Object.entries(sourceToolLoaders)) {
      $(id)?.addEventListener('toggle', event => {
        if (event.currentTarget.open && state.activeSection === 'sourcesSection') void load();
      });
    }
    if ($('importLastRoundDirectoryBtn')) $('importLastRoundDirectoryBtn').addEventListener('click', (event) => importLastRoundDirectory(event.currentTarget));
    if ($('importCompanyWatchManifestBtn')) $('importCompanyWatchManifestBtn').addEventListener('click', (event) => importCompanyWatchManifest(event.currentTarget));
    const hirebaseSourceToggle = document.querySelector('#cfgSourcesWrap input[data-source="hirebase"]');
    if (hirebaseSourceToggle) hirebaseSourceToggle.addEventListener('change', () => {
      if (hirebaseSourceToggle.checked && !window.confirm(
        'Enable the optional Hirebase daily sampler in this environment? It may spend up to 12 job credits per day and 400 per billing period. Every query is estimated first. The source remains disabled until you save configuration.'
      )) {
        hirebaseSourceToggle.checked = false;
      }
    });
    document.querySelectorAll('.hirebase-estimate-btn').forEach(button => {
      button.addEventListener('click', () => estimateHirebase(button.dataset.provider, button));
    });
    if ($('boardDiscoveryForm')) $('boardDiscoveryForm').addEventListener('submit', discoverCompanyBoards);
    if ($('globalCandidateForm')) $('globalCandidateForm').addEventListener('submit', importGlobalDiscoveryCandidate);

    // Server-side job feed pagination.
    if ($('previousJobsPageBtn')) $('previousJobsPageBtn').addEventListener('click', () => {
      if (state.pagination?.has_previous) {
        state.feedPage = Math.max(1, state.feedPage - 1);
        loadJobsFeed();
      }
    });
    if ($('nextJobsPageBtn')) $('nextJobsPageBtn').addEventListener('click', () => {
      if (state.pagination?.has_next) {
        state.feedPage += 1;
        loadJobsFeed();
      }
    });

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
          showJobInspector(state.jobs.find(job => job.id === row.dataset.jobId));
        }
      });
    }

    // Applied exports
    if ($('exportAppliedJsonBtn')) $('exportAppliedJsonBtn').addEventListener('click', () => exportAppliedData('json'));
    if ($('exportAppliedCsvBtn')) $('exportAppliedCsvBtn').addEventListener('click', () => exportAppliedData('csv'));

    // Preferences save button
    if ($('savePreferencesBtn')) $('savePreferencesBtn').addEventListener('click', savePreferences);
    if ($('parseResumeBtn')) $('parseResumeBtn').addEventListener('click', parseResumeForSuggestions);
    if ($('createTelegramLinkBtn')) $('createTelegramLinkBtn').addEventListener('click', createTelegramLink);
    if ($('telegramNotificationsEnabled')) $('telegramNotificationsEnabled').addEventListener('change', updateTelegramNotificationSetting);
    if ($('refreshTelegramStatusBtn')) $('refreshTelegramStatusBtn').addEventListener('click', loadTelegramStatus);
    if ($('disconnectTelegramBtn')) $('disconnectTelegramBtn').addEventListener('click', disconnectTelegram);
    if ($('connectGoogleAlertsGmailBtn')) $('connectGoogleAlertsGmailBtn').addEventListener('click', connectGoogleAlertsGmail);
    if ($('googleAlertsGmailDataUseConsent')) $('googleAlertsGmailDataUseConsent').addEventListener('change', () => {
      const button = $('connectGoogleAlertsGmailBtn');
      if (button) button.disabled = !$('googleAlertsGmailDataUseConsent').checked;
    });
    if ($('refreshGoogleAlertsGmailBtn')) $('refreshGoogleAlertsGmailBtn').addEventListener('click', loadGoogleAlertsGmailStatus);
    if ($('disconnectGoogleAlertsGmailBtn')) $('disconnectGoogleAlertsGmailBtn').addEventListener('click', disconnectGoogleAlertsGmail);
    if ($('pauseGoogleAlertsBackfillBtn')) $('pauseGoogleAlertsBackfillBtn').addEventListener('click', () => updateGoogleAlertsGmailBackfill('pause'));
    if ($('resumeGoogleAlertsBackfillBtn')) $('resumeGoogleAlertsBackfillBtn').addEventListener('click', () => updateGoogleAlertsGmailBackfill('resume'));
    if ($('retryGoogleAlertsBackfillBtn')) $('retryGoogleAlertsBackfillBtn').addEventListener('click', () => updateGoogleAlertsGmailBackfill('retry'));


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
        state.feedPage = 1;
        loadJobsFeed();
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
        state.feedPage = 1;
        loadJobsFeed();
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
        { value: '0', label: 'Any posting date' },
      ],
      value: String(state.filters.maxAge),
      onChange: (val) => {
        state.filters.maxAge = Number(val);
        state.feedPage = 1;
        loadJobsFeed();
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
        state.feedPage = 1;
        loadJobsFeed();
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

  function splitUserTags(value) {
    return String(value || '').split(/[\n,;]+/)
      .map(item => item.trim()).filter(Boolean)
      .filter((item, index, all) => all.findIndex(other => other.toLowerCase() === item.toLowerCase()) === index);
  }

  function safeExternalJobUrl(value) {
    try {
      const url = new URL(String(value || ''), window.location.origin);
      return ['http:', 'https:'].includes(url.protocol) ? url.href : '';
    } catch (_error) {
      return '';
    }
  }



  function showUnavailablePanel() {
    setAuthPanel('authUnavailablePanel');
  }

  async function initializeWorkspace(user) {
    if (workspaceInitialized) return;
    workspaceInitialized = true;
    state.currentUser = user;
    state.isAdmin = user?.role === 'admin';
    document.body.classList.add('auth-ready');
    document.body.classList.remove('user-ready');
    const userWorkspace = $('userWorkspace');
    if (userWorkspace) userWorkspace.hidden = true;
    if ($('accountEmail')) $('accountEmail').textContent = user?.email || '—';
    if ($('accountRole')) $('accountRole').textContent = state.isAdmin ? 'Administrator' : 'Member';
    document.querySelectorAll(
      '.admin-only-setting, .admin-only-navigation, .admin-only-section'
    ).forEach(el => { el.hidden = !state.isAdmin; });
    if ($('preferencesSubtitle')) $('preferencesSubtitle').textContent = state.isAdmin
      ? 'Candidate profile and global matching, source, and notification settings.'
      : 'Your personal target roles, locations, skills, and matching criteria. Changes affect only your feed.';
    const saveButton = $('savePreferencesBtn');
    if (saveButton) saveButton.textContent = state.isAdmin ? 'Save Preferences to V2' : 'Save My Preferences';

    try {
      await loadAppliedJobs();
    } catch (error) {
      state.appliedJobs = [];
      updateAppliedCountBadge();
      showToast(error.message || 'Application tracking is temporarily unavailable.', 'error', 7000);
    }
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
    await loadTelegramStatus();
    if (state.isAdmin) {
      const gmailResult = new URLSearchParams(window.location.search).get('gmail_connect');
      if (gmailResult === 'connected') showToast('Personal Gmail connected. Initial sync will start automatically.', 'success');
      else if (gmailResult === 'failed') showToast('Personal Gmail connection failed. Check the owner account, callback configuration and server logs.', 'error', 7000);
      else if (gmailResult === 'cancelled') showToast('Personal Gmail connection was cancelled.', 'info');
      await loadGoogleAlertsGmailStatus();
    }
    if (state.isAdmin || state.config?.onboarding_complete) await loadJobsFeed();
    else { state.jobs = []; renderFeed(); }
    await loadSourceStatusTelemetry();

    const refreshFeedIfVisible = () => {
      if (document.visibilityState !== 'visible') return;
      if (state.isAdmin || (state.config && state.config.onboarding_complete)) {
        void loadJobsFeed();
      }
    };
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible') refreshFeedIfVisible();
    });
    setInterval(refreshFeedIfVisible, 60000);
    setInterval(() => {
      if (document.visibilityState !== 'visible') return;
      void loadSourceStatusTelemetry();
      if (state.isAdmin) void loadGoogleAlertsGmailStatus();
    }, 30000);
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

    if (result.access === 'admin' || result.access === 'user') await initializeWorkspace(result.user);
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
    const googleButton = $('googleSignInBtn');
    const googleSignup = $('googleSignupWrap');
    if (googleButton && googleSignup) {
      authClient.request('/auth/google/status', { cache: 'no-store' })
        .then(response => response.ok ? response.json() : { enabled: false })
        .then(status => {
          googleSignup.hidden = !status.enabled;
          googleButton.hidden = !status.enabled;
        })
        .catch(() => {
          googleSignup.hidden = true;
          googleButton.hidden = true;
        });
    }
    const googleAuthResult = new URLSearchParams(window.location.search).get('google_auth');
    if (googleAuthResult === 'failed' && $('authStatusMsg')) {
      $('authStatusMsg').textContent = 'Google sign-in could not be completed. Please try again.';
    } else if (googleAuthResult === 'cancelled' && $('authStatusMsg')) {
      $('authStatusMsg').textContent = 'Google sign-in was cancelled.';
    }

    const passwordInput = $('authPassword');
    const passwordToggle = $('authPasswordToggle');
    if (passwordInput && passwordToggle) {
      passwordToggle.addEventListener('click', () => {
        const reveal = passwordInput.type === 'password';
        passwordInput.type = reveal ? 'text' : 'password';
        passwordToggle.textContent = reveal ? 'Hide' : 'Show';
        passwordToggle.setAttribute('aria-pressed', String(reveal));
      });
    }

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
