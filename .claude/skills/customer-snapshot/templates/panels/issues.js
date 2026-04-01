/**
 * Issues Panel — Dashboard V2
 *
 * The most complex panel extraction from v1 intelligence-dashboard.html.
 * Consolidates ~600 lines across 12+ v1 functions: classifyIssue, getFiltered,
 * buildFilters, filterByBucket, render, renderThemeChart, renderThemes,
 * renderHealthBuckets, renderAttentionCallouts, renderVelocityChart,
 * renderCadenceMetrics, and addAsanaBadgesToJiraIssues.
 *
 * Features:
 *   - Health bucket classification (triage / active / stale / resolved)
 *   - Multi-dimension filter system (status, type, theme, search, bucket)
 *   - CSS horizontal bar theme chart (bugs vs feature requests)
 *   - Collapsible theme sections with issue tables
 *   - Attention callouts with click-to-filter
 *   - Velocity chart (opened vs resolved by month)
 *   - Response cadence metrics
 *   - Asana badge cross-linking from INTELLIGENCE_DATA.actions
 *
 * No ECharts dependency — pure DOM rendering with CSS charts.
 * No ES module syntax (file:// CORS constraint).
 */
(function() {
  'use strict';

  // ── Constants (self-contained, copied from v1) ──

  var RESOLVED_STATUSES = ['Done', 'Closed', 'Resolved', 'Merged'];
  var ACTIVE_STATUSES = ['In Progress', 'In Review', 'In Development', 'Selected for Development'];
  var WAITING_STATUSES = ['Open', 'Backlog', 'To Do', 'Waiting', 'Future'];
  var TRIAGE_STATUSES = ['Triage', "Won't Fix", 'Archived'];
  var STALE_DAYS = 30;
  var VERY_STALE_DAYS = 60;

  var STATUS_CATEGORIES = {
    resolved: { statuses: RESOLVED_STATUSES, color: 'var(--green)', label: 'Resolved' },
    active: { statuses: ACTIVE_STATUSES, color: 'var(--blue)', label: 'Active' },
    waiting: { statuses: WAITING_STATUSES, color: 'var(--amber)', label: 'Waiting' },
    triage: { statuses: TRIAGE_STATUSES, color: 'var(--gray)', label: 'Triage' }
  };

  var STATUS_COLORS = {
    'Active': 'var(--blue)', 'In Progress': 'var(--blue)', 'In Review': 'var(--blue)',
    'In Development': 'var(--blue)', 'Selected for Development': 'var(--blue)',
    'Backlog': 'var(--amber)', 'Open': 'var(--amber)', 'To Do': 'var(--amber)',
    'Waiting': 'var(--amber)', 'Future': 'var(--amber)',
    'Triage': 'var(--orange)',
    'Done': 'var(--green)', 'Closed': 'var(--green)', 'Resolved': 'var(--green)', 'Merged': 'var(--green)',
    'Archive': 'var(--gray)', 'Archived': 'var(--gray)', "Won't Fix": 'var(--gray)'
  };

  var PRIO_ORDER = ['P0', 'P1', 'P2', 'P3'];

  // Component/parent normalization maps for theming
  // Maps variant component and parent names to canonical theme names
  var COMPONENT_NORMALIZE = {
    'Weave Python SDK': 'SDK & Client Libraries',
    'Python SDK': 'SDK & Client Libraries',
    'wandb-sdk': 'SDK & Client Libraries',
    'wandb SDK': 'SDK & Client Libraries',
    'Client': 'SDK & Client Libraries',
    'Sweeps': 'Sweeps',
    'Sweep': 'Sweeps',
    'Launch': 'Launch',
    'W&B Launch': 'Launch',
    'Artifacts': 'Artifacts',
    'Artifact': 'Artifacts',
    'Model Registry': 'Model Registry',
    'Reports': 'Reports',
    'Report': 'Reports',
    'Weave': 'Weave',
    'Weave Tracing': 'Weave',
    'UI': 'UI & Dashboard',
    'Dashboard': 'UI & Dashboard',
    'App': 'UI & Dashboard',
    'Frontend': 'UI & Dashboard',
    'Auth': 'Auth & Permissions',
    'Authentication': 'Auth & Permissions',
    'Permissions': 'Auth & Permissions',
    'SSO': 'Auth & Permissions',
    'API': 'API & Integrations',
    'Public API': 'API & Integrations',
    'Integrations': 'API & Integrations',
    'Infrastructure': 'Infrastructure',
    'Infra': 'Infrastructure',
    'Backend': 'Infrastructure',
    'Server': 'Infrastructure'
  };

  var PARENT_NORMALIZE = {
    'SDK Improvements': 'SDK & Client Libraries',
    'Weave SDK Improvements': 'SDK & Client Libraries',
    'Sweep Improvements': 'Sweeps',
    'Launch Improvements': 'Launch',
    'Artifact Improvements': 'Artifacts',
    'UI Improvements': 'UI & Dashboard',
    'Auth Improvements': 'Auth & Permissions',
    'API Improvements': 'API & Integrations'
  };

  // ── Filter state (module-scoped within IIFE) ──

  var _filterState = { status: 'all', type: 'all', theme: 'all', search: '', bucket: null };
  var _issues = [];
  var _container = null;
  var _config = null;
  var _debounceTimer = null;

  // ── Helpers ──

  function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
              .replace(/"/g, '&quot;').replace(/'/g, '&#039;');
  }

  function parseDate(s) {
    if (!s) return null;
    return new Date(s);
  }

  function getNow() {
    var gen = (typeof INTELLIGENCE_DATA !== 'undefined' && INTELLIGENCE_DATA.generated)
      ? INTELLIGENCE_DATA.generated : new Date().toISOString().split('T')[0];
    return new Date(gen + 'T00:00:00');
  }

  function daysAgo(dateStr) {
    var d = parseDate(dateStr);
    if (!d) return Infinity;
    var now = getNow();
    return Math.floor((now - d) / (1000 * 60 * 60 * 24));
  }

  function monthKey(dateStr) {
    var d = parseDate(dateStr);
    if (!d) return null;
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0');
  }

  function monthLabel(key) {
    var parts = key.split('-');
    var months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    return months[parseInt(parts[1]) - 1] + ' ' + parts[0].slice(2);
  }

  function statusColor(s) {
    return STATUS_COLORS[s] || 'var(--gray)';
  }

  function getStatusCategory(status) {
    for (var cat in STATUS_CATEGORIES) {
      if (STATUS_CATEGORIES[cat].statuses.indexOf(status) !== -1) {
        return cat;
      }
    }
    return 'waiting'; // default for unknown statuses
  }

  function classifyIssue(issue) {
    if (RESOLVED_STATUSES.indexOf(issue.status) !== -1) return 'resolved';
    if (issue.status === 'Triage') return 'triage';
    var engDays = daysAgo(issue.comments ? issue.comments.last_eng_comment_date : null);
    if (engDays <= STALE_DAYS && engDays !== Infinity) return 'active';
    return 'stale';
  }

  function statusBadge(status) {
    var sc = statusColor(status);
    return '<span class="status-badge" style="background:color-mix(in srgb,' + sc + ' 12%,transparent);color:' + sc + '">' + escapeHtml(status) + '</span>';
  }

  function priorityBadge(priority) {
    var p = (priority || 'P3').toUpperCase();
    var cls = 'p3';
    if (p === 'P0' || p === 'P1') cls = 'p0p1';
    else if (p === 'P2') cls = 'p2';
    return '<span class="priority-badge ' + cls + '">' + escapeHtml(p) + '</span>';
  }

  function ageBadge(dateStr) {
    var days = daysAgo(dateStr);
    if (days === Infinity) return '<span class="age-badge gray">--</span>';
    var cls = 'green';
    if (days >= 90) cls = 'red';
    else if (days >= 30) cls = 'amber';
    return '<span class="age-badge ' + cls + '">' + days + 'd</span>';
  }

  function countBy(arr, fn) {
    var m = {};
    for (var i = 0; i < arr.length; i++) {
      var k = fn(arr[i]);
      m[k] = (m[k] || 0) + 1;
    }
    return m;
  }

  // ── Filter logic ──

  function getFiltered() {
    var now = getNow();
    return _issues.filter(function(i) {
      // Bucket filter takes precedence
      if (_filterState.bucket) {
        if (_filterState.bucket === 'never_commented') {
          if (!(!i.comments || i.comments.comment_count === 0) || RESOLVED_STATUSES.indexOf(i.status) !== -1) return false;
        } else if (_filterState.bucket === 'no_eng_60d') {
          if (RESOLVED_STATUSES.indexOf(i.status) !== -1) return false;
          var ed = daysAgo(i.comments ? i.comments.last_eng_comment_date : null);
          if (!(ed > VERY_STALE_DAYS || (!i.comments || i.comments.comment_count === 0))) return false;
        } else if (_filterState.bucket === 'unassigned') {
          if (RESOLVED_STATUSES.indexOf(i.status) !== -1 || i.assignee) return false;
        } else if (_filterState.bucket === 'recent') {
          if (daysAgo(i.created) > 14) return false;
        } else if (_filterState.bucket === 'triage' || _filterState.bucket === 'active' ||
                   _filterState.bucket === 'stale' || _filterState.bucket === 'resolved') {
          if (classifyIssue(i) !== _filterState.bucket) return false;
        }
      }

      // Status filter
      if (_filterState.status !== 'all') {
        var cat = getStatusCategory(i.status);
        if (cat !== _filterState.status) return false;
      } else {
        // By default hide resolved unless explicitly selected
        if (RESOLVED_STATUSES.indexOf(i.status) !== -1 && !_filterState.bucket) return false;
      }

      // Type filter
      if (_filterState.type !== 'all') {
        if (_filterState.type === 'Bug' && i.type !== 'Bug') return false;
        if (_filterState.type === 'Feature Request' && i.type !== 'Feature Request') return false;
      }

      // Theme filter
      if (_filterState.theme !== 'all' && i.theme !== _filterState.theme) return false;

      // Search filter
      if (_filterState.search) {
        var q = _filterState.search.toLowerCase();
        var match = (i.key || '').toLowerCase().indexOf(q) !== -1 ||
                    (i.summary || '').toLowerCase().indexOf(q) !== -1 ||
                    (i.assignee || '').toLowerCase().indexOf(q) !== -1;
        if (!match) return false;
      }

      return true;
    });
  }

  // ── CSS ──

  var PANEL_CSS = '\
.section-label {\
  font-family: var(--font-mono);\
  font-size: 11px;\
  font-weight: 600;\
  text-transform: uppercase;\
  letter-spacing: 1.5px;\
  color: var(--text-tertiary);\
  margin-bottom: 16px;\
}\
.filter-bar {\
  display: flex;\
  flex-wrap: wrap;\
  gap: 8px;\
  margin-bottom: 24px;\
  align-items: center;\
}\
.filter-pill {\
  font-family: "JetBrains Mono", monospace;\
  font-size: 11px;\
  font-weight: 600;\
  padding: 6px 14px;\
  border-radius: 20px;\
  background: var(--bg-surface);\
  border: 1px solid var(--border-subtle);\
  color: var(--text-secondary);\
  cursor: pointer;\
  transition: all 0.15s;\
  white-space: nowrap;\
}\
.filter-pill:hover {\
  border-color: var(--border);\
}\
.filter-pill.active {\
  background: var(--accent-dim);\
  border-color: var(--accent-border);\
  color: var(--accent);\
}\
.filter-select {\
  font-family: "JetBrains Mono", monospace;\
  font-size: 11px;\
  font-weight: 400;\
  background: var(--bg-surface);\
  border: 1px solid var(--border-subtle);\
  border-radius: 6px;\
  padding: 6px 12px;\
  color: var(--text-secondary);\
  appearance: none;\
  -webkit-appearance: none;\
  background-image: url("data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' width=\'12\' height=\'12\' viewBox=\'0 0 12 12\'%3E%3Cpath d=\'M3 5l3 3 3-3\' fill=\'none\' stroke=\'%236b7280\' stroke-width=\'1.5\'/%3E%3C/svg%3E");\
  background-repeat: no-repeat;\
  background-position: right 8px center;\
  padding-right: 28px;\
}\
.filter-search {\
  font-family: "Outfit", system-ui, sans-serif;\
  font-size: 14px;\
  font-weight: 400;\
  background: var(--bg-surface);\
  border: 1px solid var(--border-subtle);\
  border-radius: 6px;\
  padding: 8px 12px;\
  color: var(--text-primary);\
  flex: 1;\
  min-width: 200px;\
}\
.filter-search:focus {\
  outline: none;\
  border-color: var(--accent-border);\
}\
.filter-search::placeholder {\
  color: var(--text-tertiary);\
}\
.filter-active-badge {\
  font-family: "JetBrains Mono", monospace;\
  font-size: 11px;\
  font-weight: 600;\
  color: var(--accent);\
  background: var(--accent-dim);\
  border: 1px solid var(--accent-border);\
  padding: 2px 8px;\
  border-radius: 10px;\
  cursor: pointer;\
  white-space: nowrap;\
}\
.filter-active-badge:hover {\
  opacity: 0.8;\
}\
.filter-sep {\
  width: 1px;\
  height: 20px;\
  background: var(--border-subtle);\
  flex-shrink: 0;\
}\
.health-bar {\
  display: flex;\
  height: 8px;\
  border-radius: 4px;\
  overflow: hidden;\
  margin-bottom: 12px;\
}\
.health-segment {\
  height: 100%;\
  transition: width 0.3s;\
}\
.health-legend {\
  display: flex;\
  gap: 16px;\
  margin-bottom: 24px;\
  flex-wrap: wrap;\
}\
.health-legend-item {\
  display: flex;\
  align-items: center;\
  gap: 6px;\
  font-family: "JetBrains Mono", monospace;\
  font-size: 11px;\
  font-weight: 400;\
  color: var(--text-secondary);\
  cursor: pointer;\
}\
.health-legend-item:hover {\
  color: var(--text-primary);\
}\
.health-dot {\
  width: 8px;\
  height: 8px;\
  border-radius: 50%;\
  flex-shrink: 0;\
}\
.attention-callouts {\
  display: flex;\
  flex-wrap: wrap;\
  gap: 12px;\
  margin-bottom: 24px;\
}\
.attention-callout {\
  background: var(--bg-elevated);\
  border-left: 3px solid var(--text-tertiary);\
  padding: 12px 16px;\
  border-radius: 0 6px 6px 0;\
  cursor: pointer;\
  transition: background 0.15s;\
  flex: 1;\
  min-width: 160px;\
}\
.attention-callout:hover {\
  background: var(--bg-hover);\
}\
.attention-callout.severity-high {\
  border-left-color: var(--red);\
}\
.attention-callout.severity-medium {\
  border-left-color: var(--amber);\
}\
.attention-callout.severity-low {\
  border-left-color: var(--orange);\
}\
.attention-callout.severity-info {\
  border-left-color: var(--blue);\
}\
.attention-callout.callout-active {\
  border: 1px solid var(--accent-border);\
  border-left: 3px solid var(--accent);\
  background: var(--accent-dim);\
}\
.callout-count {\
  font-family: "Outfit", system-ui, sans-serif;\
  font-size: 28px;\
  font-weight: 600;\
  display: block;\
  line-height: 1.1;\
}\
.callout-text {\
  font-family: "Outfit", system-ui, sans-serif;\
  font-size: 14px;\
  font-weight: 400;\
  color: var(--text-secondary);\
  display: block;\
  margin-top: 4px;\
}\
.callout-action {\
  font-family: "JetBrains Mono", monospace;\
  font-size: 11px;\
  font-weight: 400;\
  color: var(--accent);\
  opacity: 0;\
  transition: opacity 0.15s;\
  display: block;\
  margin-top: 6px;\
}\
.attention-callout:hover .callout-action {\
  opacity: 1;\
}\
.two-col-grid {\
  display: grid;\
  grid-template-columns: 1fr 1fr;\
  gap: 24px;\
  margin-bottom: 24px;\
}\
.analytics-card {\
  background: var(--bg-elevated);\
  border: 1px solid var(--border-subtle);\
  border-radius: 6px;\
  padding: 20px;\
}\
.velocity-chart {\
  margin-bottom: 16px;\
}\
.velocity-bar-row {\
  display: flex;\
  gap: 8px;\
  align-items: center;\
  margin-bottom: 4px;\
}\
.velocity-label {\
  font-family: "JetBrains Mono", monospace;\
  font-size: 11px;\
  font-weight: 400;\
  color: var(--text-tertiary);\
  width: 60px;\
  text-align: right;\
  flex-shrink: 0;\
}\
.velocity-bars {\
  flex: 1;\
  display: flex;\
  gap: 3px;\
}\
.velocity-bar {\
  height: 16px;\
  border-radius: 3px;\
  min-width: 2px;\
  transition: width 0.3s;\
}\
.velocity-opened {\
  background: var(--red-dim);\
  border: 1px solid var(--red-border);\
}\
.velocity-resolved {\
  background: var(--green-dim);\
  border: 1px solid var(--green-border);\
}\
.velocity-legend {\
  display: flex;\
  gap: 16px;\
  margin-top: 8px;\
}\
.velocity-legend .legend-item {\
  display: flex;\
  align-items: center;\
  gap: 6px;\
  font-family: "JetBrains Mono", monospace;\
  font-size: 11px;\
  font-weight: 400;\
  color: var(--text-tertiary);\
}\
.velocity-legend .legend-dot {\
  width: 8px;\
  height: 8px;\
  border-radius: 50%;\
  flex-shrink: 0;\
}\
.velocity-summary {\
  font-family: "JetBrains Mono", monospace;\
  font-size: 10px;\
  color: var(--text-tertiary);\
  margin-top: 6px;\
}\
.cadence-metrics {\
  display: flex;\
  gap: 48px;\
  flex-wrap: wrap;\
}\
.cadence-stat {\
  display: flex;\
  flex-direction: column;\
}\
.cadence-value {\
  font-family: "Outfit", system-ui, sans-serif;\
  font-size: 28px;\
  font-weight: 600;\
  line-height: 1.1;\
}\
.cadence-label {\
  font-family: "JetBrains Mono", monospace;\
  font-size: 11px;\
  font-weight: 600;\
  text-transform: uppercase;\
  letter-spacing: 1.5px;\
  color: var(--text-tertiary);\
  margin-top: 6px;\
}\
.cadence-context {\
  font-family: "JetBrains Mono", monospace;\
  font-size: 11px;\
  font-weight: 400;\
  color: var(--text-tertiary);\
  margin-top: 4px;\
}\
.theme-chart {\
  margin-bottom: 32px;\
}\
.theme-bar-row {\
  display: flex;\
  align-items: center;\
  gap: 12px;\
  margin-bottom: 6px;\
}\
.theme-bar-label {\
  font-family: "JetBrains Mono", monospace;\
  font-size: 11px;\
  font-weight: 400;\
  color: var(--text-secondary);\
  width: 180px;\
  text-align: right;\
  flex-shrink: 0;\
  overflow: hidden;\
  text-overflow: ellipsis;\
  white-space: nowrap;\
}\
.theme-bar-track {\
  flex: 1;\
  height: 20px;\
  background: var(--bg-surface);\
  border-radius: 3px;\
  overflow: hidden;\
  display: flex;\
}\
.theme-bar-fill {\
  height: 100%;\
  border-radius: 3px;\
  transition: width 0.3s;\
}\
.theme-bar-count {\
  font-family: "JetBrains Mono", monospace;\
  font-size: 11px;\
  font-weight: 600;\
  color: var(--text-tertiary);\
  width: 40px;\
  flex-shrink: 0;\
}\
.stacked-bar-legend {\
  display: flex;\
  gap: 16px;\
  margin-top: 8px;\
}\
.stacked-bar-legend .legend-item {\
  display: flex;\
  align-items: center;\
  gap: 6px;\
  font-family: "JetBrains Mono", monospace;\
  font-size: 11px;\
  font-weight: 400;\
  color: var(--text-tertiary);\
}\
.stacked-bar-legend .legend-dot {\
  width: 8px;\
  height: 8px;\
  border-radius: 50%;\
  flex-shrink: 0;\
}\
.theme-section {\
  margin-bottom: 16px;\
}\
.theme-header {\
  display: flex;\
  justify-content: space-between;\
  align-items: center;\
  padding: 10px 16px;\
  background: var(--bg-elevated);\
  border: 1px solid var(--border-subtle);\
  border-radius: 6px;\
  cursor: pointer;\
  transition: background 0.15s;\
}\
.theme-header:hover {\
  background: var(--bg-hover);\
}\
.theme-header-left {\
  display: flex;\
  align-items: center;\
  gap: 12px;\
}\
.theme-name {\
  font-family: "Outfit", system-ui, sans-serif;\
  font-size: 14px;\
  font-weight: 600;\
}\
.theme-count {\
  font-family: "JetBrains Mono", monospace;\
  font-size: 11px;\
  font-weight: 600;\
  color: var(--text-tertiary);\
}\
.theme-badges {\
  display: flex;\
  gap: 6px;\
  align-items: center;\
}\
.mini-badge {\
  font-family: "JetBrains Mono", monospace;\
  font-size: 10px;\
  font-weight: 600;\
  padding: 1px 6px;\
  border-radius: 8px;\
}\
.mini-badge.p0, .mini-badge.p1 {\
  color: var(--red);\
  background: var(--red-dim);\
}\
.mini-badge.p2 {\
  color: var(--amber);\
  background: var(--amber-dim);\
}\
.mini-badge.p3 {\
  color: var(--text-tertiary);\
  background: var(--bg-surface);\
}\
.theme-arrow {\
  display: inline-block;\
  width: 16px;\
  transition: transform 0.2s;\
  color: var(--text-tertiary);\
  font-size: 12px;\
}\
.theme-section.collapsed .theme-arrow {\
  transform: rotate(-90deg);\
}\
.theme-body {\
  display: grid;\
  grid-template-rows: 1fr;\
  transition: grid-template-rows 0.25s ease;\
}\
.theme-section.collapsed .theme-body {\
  grid-template-rows: 0fr;\
}\
.theme-body-inner {\
  overflow: hidden;\
}\
.issue-table {\
  width: 100%;\
  border-collapse: collapse;\
  margin-top: 4px;\
}\
.issue-table th {\
  font-family: "JetBrains Mono", monospace;\
  font-size: 11px;\
  font-weight: 600;\
  text-transform: uppercase;\
  letter-spacing: 1.5px;\
  color: var(--text-tertiary);\
  text-align: left;\
  padding: 8px 12px;\
  border-bottom: 1px solid var(--border);\
}\
.issue-table td {\
  font-family: "Outfit", system-ui, sans-serif;\
  font-size: 14px;\
  font-weight: 400;\
  padding: 10px 12px;\
  border-bottom: 1px solid var(--border-subtle);\
  vertical-align: middle;\
}\
.issue-table tr:hover {\
  background: var(--bg-hover);\
  transition: background 0.15s;\
}\
.issue-table tr:last-child td {\
  border-bottom: none;\
}\
.issue-key {\
  font-family: "JetBrains Mono", monospace;\
  font-size: 11px;\
  font-weight: 400;\
  color: var(--accent);\
  text-decoration: none;\
  white-space: nowrap;\
}\
.issue-key:hover {\
  text-decoration: underline;\
}\
.issue-summary {\
  font-family: "Outfit", system-ui, sans-serif;\
  font-size: 14px;\
  font-weight: 400;\
  max-width: 300px;\
  overflow: hidden;\
  text-overflow: ellipsis;\
  white-space: nowrap;\
  display: inline-block;\
}\
.status-badge {\
  display: inline-block;\
  padding: 2px 8px;\
  border-radius: 10px;\
  font-family: "JetBrains Mono", monospace;\
  font-size: 11px;\
  font-weight: 400;\
  white-space: nowrap;\
}\
.priority-badge {\
  display: inline-block;\
  padding: 2px 8px;\
  border-radius: 10px;\
  font-family: "JetBrains Mono", monospace;\
  font-size: 11px;\
  font-weight: 400;\
}\
.priority-badge.p0p1 {\
  color: var(--red);\
  background: var(--red-dim);\
  border: 1px solid var(--red-border);\
}\
.priority-badge.p2 {\
  color: var(--amber);\
  background: var(--amber-dim);\
  border: 1px solid var(--amber-border);\
}\
.priority-badge.p3 {\
  color: var(--text-tertiary);\
  background: var(--bg-surface);\
  border: 1px solid var(--border-subtle);\
}\
.age-badge {\
  display: inline-block;\
  padding: 2px 8px;\
  border-radius: 10px;\
  font-family: "JetBrains Mono", monospace;\
  font-size: 11px;\
  font-weight: 400;\
}\
.age-badge.green {\
  color: var(--green);\
  background: var(--green-dim);\
  border: 1px solid var(--green-border);\
}\
.age-badge.amber {\
  color: var(--amber);\
  background: var(--amber-dim);\
  border: 1px solid var(--amber-border);\
}\
.age-badge.red {\
  color: var(--red);\
  background: var(--red-dim);\
  border: 1px solid var(--red-border);\
}\
.age-badge.gray {\
  color: var(--text-tertiary);\
  background: var(--bg-surface);\
  border: 1px solid var(--border-subtle);\
}\
.type-badge {\
  display: inline-block;\
  padding: 2px 8px;\
  border-radius: 10px;\
  font-family: "JetBrains Mono", monospace;\
  font-size: 11px;\
  font-weight: 400;\
}\
.type-badge.bug {\
  color: var(--red);\
  background: var(--red-dim);\
}\
.type-badge.feature {\
  color: var(--blue);\
  background: var(--blue-dim);\
}\
.assignee {\
  font-family: "Outfit", system-ui, sans-serif;\
  font-size: 13px;\
  font-weight: 400;\
  color: var(--text-secondary);\
}\
.assignee.unassigned {\
  color: var(--text-tertiary);\
}\
.activity-cell {\
  font-family: "JetBrains Mono", monospace;\
  font-size: 11px;\
  font-weight: 400;\
}\
.activity-cell.recent {\
  color: var(--green);\
}\
.activity-cell.aging {\
  color: var(--amber);\
}\
.activity-cell.stale {\
  color: var(--red);\
}\
.activity-cell.never {\
  color: var(--text-tertiary);\
}\
.asana-badge {\
  display: inline-block;\
  font-family: "JetBrains Mono", monospace;\
  font-size: 11px;\
  font-weight: 600;\
  color: var(--accent);\
  background: var(--accent-dim);\
  border: 1px solid var(--accent-border);\
  padding: 2px 8px;\
  border-radius: 10px;\
  text-decoration: none;\
  margin-left: 6px;\
}\
.asana-badge:hover {\
  opacity: 0.8;\
}\
.fe-badge {\
  display: inline-block;\
  font-family: "JetBrains Mono", monospace;\
  font-size: 11px;\
  font-weight: 600;\
  color: var(--accent);\
  background: var(--accent-dim);\
  padding: 2px 6px;\
  border-radius: 10px;\
  margin-left: 4px;\
}\
.themes-toolbar {\
  display: flex;\
  justify-content: flex-end;\
  padding: 10px 0 0;\
}\
.expand-collapse-btn {\
  font-family: "JetBrains Mono", monospace;\
  font-size: 10px;\
  font-weight: 600;\
  padding: 3px 10px;\
  border-radius: 20px;\
  background: var(--bg-surface);\
  border: 1px solid var(--border-subtle);\
  color: var(--text-secondary);\
  cursor: pointer;\
}\
.expand-collapse-btn:hover {\
  border-color: var(--border);\
}\
.empty-state {\
  color: var(--text-tertiary);\
  font-family: "Outfit", system-ui, sans-serif;\
  font-size: 14px;\
  padding: 24px 0;\
  text-align: center;\
}\
@media (max-width: 700px) {\
  .two-col-grid {\
    grid-template-columns: 1fr;\
  }\
  .theme-bar-label {\
    width: 100px;\
  }\
  .cadence-metrics {\
    gap: 24px;\
  }\
}\
';

  // ── Sub-renderers ──

  function renderHealthSummary(el, issues) {
    var buckets = { triage: 0, active: 0, stale: 0, resolved: 0 };
    for (var i = 0; i < issues.length; i++) {
      buckets[classifyIssue(issues[i])]++;
    }
    var total = issues.length;
    if (total === 0) {
      el.innerHTML = '';
      return;
    }

    var colors = { triage: 'var(--orange)', active: 'var(--green)', stale: 'var(--red)', resolved: 'var(--gray)' };
    var labels = { triage: 'Needs Triage', active: 'Active', stale: 'No eng update ' + STALE_DAYS + 'd+', resolved: 'Resolved' };
    var order = ['triage', 'active', 'stale', 'resolved'];

    var barHtml = '<div class="health-bar">';
    for (var j = 0; j < order.length; j++) {
      var key = order[j];
      var pct = (buckets[key] / total) * 100;
      if (pct > 0) {
        barHtml += '<div class="health-segment" style="width:' + Math.max(pct, 2) + '%;background:' + colors[key] + '"></div>';
      }
    }
    barHtml += '</div>';

    var legendHtml = '<div class="health-legend">';
    for (var k = 0; k < order.length; k++) {
      var bk = order[k];
      legendHtml += '<div class="health-legend-item" data-health-bucket="' + bk + '">' +
        '<span class="health-dot" style="background:' + colors[bk] + '"></span>' +
        '<span>' + labels[bk] + ' (' + buckets[bk] + ')</span>' +
        '</div>';
    }
    legendHtml += '</div>';

    el.innerHTML = '<div class="section-label">Issue Health</div>' + barHtml + legendHtml;

    // Click on legend items to filter by bucket
    el.querySelectorAll('[data-health-bucket]').forEach(function(item) {
      item.addEventListener('click', function() {
        var bucket = item.getAttribute('data-health-bucket');
        _filterState.bucket = bucket;
        _filterState.status = 'all';
        reRender();
      });
    });
  }

  function renderAttentionCallouts(el, issues) {
    var nonResolved = issues.filter(function(i) {
      return RESOLVED_STATUSES.indexOf(i.status) === -1;
    });

    var neverCommented = nonResolved.filter(function(i) {
      return !i.comments || i.comments.comment_count === 0;
    });
    var noEng60d = nonResolved.filter(function(i) {
      if (!i.comments || i.comments.comment_count === 0) return true;
      return daysAgo(i.comments.last_eng_comment_date) > VERY_STALE_DAYS;
    });
    var unassigned = nonResolved.filter(function(i) {
      return !i.assignee;
    });
    var recentlyOpened = issues.filter(function(i) {
      return daysAgo(i.created) <= 14;
    });

    var callouts = [];
    if (neverCommented.length > 0) {
      callouts.push({
        count: neverCommented.length,
        text: 'ticket' + (neverCommented.length !== 1 ? 's have' : ' has') + ' never been commented on',
        severity: 'high',
        bucket: 'never_commented'
      });
    }
    if (noEng60d.length > 0) {
      callouts.push({
        count: noEng60d.length,
        text: 'ticket' + (noEng60d.length !== 1 ? 's have' : ' has') + ' had no eng activity in ' + VERY_STALE_DAYS + '+ days',
        severity: 'medium',
        bucket: 'no_eng_60d'
      });
    }
    if (unassigned.length > 0) {
      callouts.push({
        count: unassigned.length,
        text: 'open ticket' + (unassigned.length !== 1 ? 's are' : ' is') + ' unassigned',
        severity: 'low',
        bucket: 'unassigned'
      });
    }
    if (recentlyOpened.length > 0) {
      callouts.push({
        count: recentlyOpened.length,
        text: 'ticket' + (recentlyOpened.length !== 1 ? 's' : '') + ' opened in the last 14 days',
        severity: 'info',
        bucket: 'recent'
      });
    }

    if (callouts.length === 0) {
      el.innerHTML = '<div style="color:var(--text-tertiary);font-size:13px;padding:8px 0">No issues requiring immediate attention.</div>';
      return;
    }

    el.innerHTML = '<div class="section-label">Attention</div><div class="attention-callouts">' +
      callouts.map(function(c) {
        var activeClass = _filterState.bucket === c.bucket ? ' callout-active' : '';
        return '<div class="attention-callout severity-' + c.severity + activeClass + '" data-callout-bucket="' + c.bucket + '">' +
          '<span class="callout-count">' + c.count + '</span>' +
          '<span class="callout-text">' + c.text + '</span>' +
          '<span class="callout-action">View tickets &#8594;</span>' +
          '</div>';
      }).join('') + '</div>';

    // Bind click handlers
    el.querySelectorAll('[data-callout-bucket]').forEach(function(card) {
      card.addEventListener('click', function() {
        var bucket = card.getAttribute('data-callout-bucket');
        if (_filterState.bucket === bucket) {
          // Toggle off
          _filterState.bucket = null;
          _filterState.status = 'all';
        } else {
          _filterState.bucket = bucket;
          _filterState.status = 'all';
        }
        reRender();
      });
    });
  }

  function renderVelocityChart(el, issues) {
    var monthsOpened = {};
    var monthsResolved = {};

    for (var i = 0; i < issues.length; i++) {
      var issue = issues[i];
      var mk = monthKey(issue.created);
      if (mk) monthsOpened[mk] = (monthsOpened[mk] || 0) + 1;
      if (RESOLVED_STATUSES.indexOf(issue.status) !== -1) {
        var rk = monthKey(issue.updated);
        if (rk) monthsResolved[rk] = (monthsResolved[rk] || 0) + 1;
      }
    }

    // Last 6 months
    var allMonths = {};
    var k;
    for (k in monthsOpened) allMonths[k] = true;
    for (k in monthsResolved) allMonths[k] = true;
    var sorted = Object.keys(allMonths).sort().slice(-6);

    if (sorted.length === 0) {
      el.innerHTML = '<div class="section-label">Velocity</div>' +
        '<div style="color:var(--text-tertiary);font-size:13px">No velocity data available.</div>';
      return;
    }

    var maxVal = 1;
    for (var s = 0; s < sorted.length; s++) {
      var mo = sorted[s];
      maxVal = Math.max(maxVal, monthsOpened[mo] || 0, monthsResolved[mo] || 0);
    }

    var html = '<div class="section-label">Velocity (Opened vs Resolved)</div><div class="velocity-chart">';
    for (var v = 0; v < sorted.length; v++) {
      var m = sorted[v];
      var opened = monthsOpened[m] || 0;
      var resolved = monthsResolved[m] || 0;
      var oPct = (opened / maxVal) * 100;
      var rPct = (resolved / maxVal) * 100;
      html += '<div class="velocity-bar-row">' +
        '<span class="velocity-label">' + monthLabel(m) + '</span>' +
        '<div class="velocity-bars">' +
        '<div class="velocity-bar velocity-opened" style="width:' + Math.max(oPct, 2) + '%" title="Opened: ' + opened + '"></div>' +
        '<div class="velocity-bar velocity-resolved" style="width:' + Math.max(rPct, 2) + '%" title="Resolved: ' + resolved + '"></div>' +
        '</div>' +
        '</div>';
    }
    html += '</div>';

    html += '<div class="velocity-legend">' +
      '<span class="legend-item"><span class="legend-dot" style="background:var(--red);opacity:0.75"></span>Opened</span>' +
      '<span class="legend-item"><span class="legend-dot" style="background:var(--green);opacity:0.75"></span>Resolved</span>' +
      '</div>';

    // Net change summary
    var totalOpened = sorted.reduce(function(s, m) { return s + (monthsOpened[m] || 0); }, 0);
    var totalResolved = sorted.reduce(function(s, m) { return s + (monthsResolved[m] || 0); }, 0);
    var net = totalOpened - totalResolved;
    var trend = net > 0 ? ('+' + net + ' net (backlog growing)') :
                net < 0 ? (net + ' net (backlog shrinking)') : 'balanced';
    html += '<div class="velocity-summary">' + totalOpened + ' opened, ' + totalResolved + ' resolved &mdash; ' + trend + '</div>';

    el.innerHTML = html;
  }

  function renderCadenceMetrics(el, issues) {
    var responseTimes = [];

    for (var i = 0; i < issues.length; i++) {
      var issue = issues[i];
      if (!issue.comments || !issue.comments.first_comment_date) continue;
      var created = parseDate(issue.created);
      var first = parseDate(issue.comments.first_comment_date);
      if (created && first) {
        var days = Math.floor((first - created) / (1000 * 60 * 60 * 24));
        if (days >= 0) responseTimes.push(days);
      }
    }

    var neverCommented = issues.filter(function(i) {
      return !i.comments || i.comments.comment_count === 0;
    }).length;

    if (responseTimes.length === 0) {
      el.innerHTML = '<div class="section-label">Response Cadence</div>' +
        '<div style="color:var(--text-tertiary);font-size:13px">No comment data available.</div>';
      return;
    }

    responseTimes.sort(function(a, b) { return a - b; });
    var median = responseTimes[Math.floor(responseTimes.length / 2)];
    var avg = Math.round(responseTimes.reduce(function(s, v) { return s + v; }, 0) / responseTimes.length);
    var within7 = responseTimes.filter(function(d) { return d <= 7; }).length;
    var within7Pct = Math.round((within7 / issues.length) * 100);

    var html = '<div class="section-label">Response Cadence</div><div class="cadence-metrics">';
    html += '<div class="cadence-stat">' +
      '<div class="cadence-value" style="color:' + (median <= 7 ? 'var(--green)' : median <= 14 ? 'var(--amber)' : 'var(--red)') + '">' + median + 'd</div>' +
      '<div class="cadence-label">Median first comment</div>' +
      '<div class="cadence-context">Average: ' + avg + ' days</div>' +
      '</div>';
    html += '<div class="cadence-stat">' +
      '<div class="cadence-value" style="color:' + (within7Pct >= 70 ? 'var(--green)' : within7Pct >= 40 ? 'var(--amber)' : 'var(--red)') + '">' + within7Pct + '%</div>' +
      '<div class="cadence-label">Response within 7 days</div>' +
      '<div class="cadence-context">' + within7 + ' of ' + issues.length + ' tickets</div>' +
      '</div>';
    html += '<div class="cadence-stat">' +
      '<div class="cadence-value" style="color:' + (neverCommented === 0 ? 'var(--green)' : neverCommented <= 5 ? 'var(--amber)' : 'var(--red)') + '">' + neverCommented + '</div>' +
      '<div class="cadence-label">Zero comments</div>' +
      '<div class="cadence-context">' + Math.round((neverCommented / issues.length) * 100) + '% of all tickets</div>' +
      '</div>';
    html += '</div>';

    el.innerHTML = html;
  }

  function renderThemeChart(el, filtered) {
    var allThemes = [];
    var seenThemes = {};
    for (var t = 0; t < _issues.length; t++) {
      var th = _issues[t].theme;
      if (th && !seenThemes[th]) {
        seenThemes[th] = true;
        allThemes.push(th);
      }
    }

    var themeBugs = {};
    var themeFRs = {};
    for (var f = 0; f < filtered.length; f++) {
      var issue = filtered[f];
      if (issue.type === 'Bug') themeBugs[issue.theme] = (themeBugs[issue.theme] || 0) + 1;
      else themeFRs[issue.theme] = (themeFRs[issue.theme] || 0) + 1;
    }

    var sortedThemes = allThemes
      .map(function(name) {
        return { name: name, bugs: themeBugs[name] || 0, frs: themeFRs[name] || 0, total: (themeBugs[name] || 0) + (themeFRs[name] || 0) };
      })
      .filter(function(t) { return t.total > 0; })
      .sort(function(a, b) { return b.total - a.total; });

    if (sortedThemes.length === 0) {
      el.innerHTML = '';
      return;
    }

    var maxCount = 1;
    for (var mc = 0; mc < sortedThemes.length; mc++) {
      maxCount = Math.max(maxCount, sortedThemes[mc].total);
    }

    var html = '<div class="section-label">Issues by Theme</div><div class="theme-chart">';
    for (var r = 0; r < sortedThemes.length; r++) {
      var item = sortedThemes[r];
      var bugPct = (item.bugs / maxCount) * 100;
      var frPct = (item.frs / maxCount) * 100;
      var label = item.name.length > 22 ? item.name.slice(0, 20) + '...' : item.name;
      html += '<div class="theme-bar-row">' +
        '<span class="theme-bar-label" title="' + escapeHtml(item.name) + '">' + escapeHtml(label) + '</span>' +
        '<div class="theme-bar-track">' +
        '<div class="theme-bar-fill" style="width:' + bugPct + '%;background:var(--red)"></div>' +
        '<div class="theme-bar-fill" style="width:' + frPct + '%;background:var(--blue)"></div>' +
        '</div>' +
        '<span class="theme-bar-count">' + item.total + '</span>' +
        '</div>';
    }
    html += '</div>';

    html += '<div class="stacked-bar-legend">' +
      '<span class="legend-item"><span class="legend-dot" style="background:var(--red)"></span>Bug</span>' +
      '<span class="legend-item"><span class="legend-dot" style="background:var(--blue)"></span>Feature Request</span>' +
      '</div>';

    el.innerHTML = html;
  }

  function renderThemes(el, filtered) {
    var grouped = {};
    for (var g = 0; g < filtered.length; g++) {
      var issue = filtered[g];
      if (!grouped[issue.theme]) grouped[issue.theme] = [];
      grouped[issue.theme].push(issue);
    }
    var sortedThemes = Object.keys(grouped).sort(function(a, b) {
      return grouped[b].length - grouped[a].length;
    });

    if (sortedThemes.length === 0) {
      el.innerHTML = '<div class="empty-state">No issues match the current filters.</div>';
      return;
    }

    var html = '<div class="themes-toolbar">' +
      '<button class="expand-collapse-btn" data-expand-all>Expand All</button>' +
      '</div>';

    for (var ti = 0; ti < sortedThemes.length; ti++) {
      var theme = sortedThemes[ti];
      var themeIssues = grouped[theme];
      var prioCounts = countBy(themeIssues, function(i) { return i.priority; });
      var badges = PRIO_ORDER
        .filter(function(p) { return prioCounts[p]; })
        .map(function(p) {
          return '<span class="mini-badge ' + p.toLowerCase() + '">' + p + ':' + prioCounts[p] + '</span>';
        }).join('');

      var rows = '';
      for (var ri = 0; ri < themeIssues.length; ri++) {
        var iss = themeIssues[ri];
        var sc = statusColor(iss.status);
        var tc = iss.type === 'Bug' ? 'bug' : 'feature';
        var assigneeHtml = iss.assignee
          ? '<span class="assignee">' + escapeHtml(iss.assignee) + '</span>'
          : '<span class="assignee unassigned">&mdash;</span>';

        // Last activity column
        var feCount = (iss.comments && iss.comments.fe_update_count) || 0;
        var feBadgeHtml = feCount > 0 ? '<span class="fe-badge">SE:' + feCount + '</span>' : '';
        var activityHtml;
        if (!iss.comments || iss.comments.comment_count === 0) {
          activityHtml = '<span class="activity-cell never">No comments</span>';
        } else if (!iss.comments.last_eng_comment_date) {
          activityHtml = '<span class="activity-cell stale">SE only</span>' + feBadgeHtml;
        } else {
          var engDays = daysAgo(iss.comments.last_eng_comment_date);
          var cls = engDays > VERY_STALE_DAYS ? 'stale' : engDays > STALE_DAYS ? 'aging' : 'recent';
          activityHtml = '<span class="activity-cell ' + cls + '">' + engDays + 'd ago</span>' + feBadgeHtml;
        }

        rows += '<tr>' +
          '<td><a class="issue-key" href="' + (iss.url || '#') + '" target="_blank" rel="noopener" data-issue-key="' + escapeHtml(iss.key) + '">' + escapeHtml(iss.key) + '</a></td>' +
          '<td><span class="issue-summary" title="' + escapeHtml(iss.summary) + '">' + escapeHtml(iss.summary) + '</span></td>' +
          '<td><span class="type-badge ' + tc + '">' + (iss.type === 'Feature Request' ? 'FR' : escapeHtml(iss.type)) + '</span></td>' +
          '<td>' + priorityBadge(iss.priority) + '</td>' +
          '<td>' + statusBadge(iss.status) + '</td>' +
          '<td>' + activityHtml + '</td>' +
          '<td>' + assigneeHtml + '</td>' +
          '</tr>';
      }

      html += '<div class="theme-section collapsed">' +
        '<div class="theme-header">' +
        '<div class="theme-header-left">' +
        '<span class="theme-arrow">&#9662;</span>' +
        '<span class="theme-name">' + escapeHtml(theme) + '</span>' +
        '<span class="theme-count">' + themeIssues.length + '</span>' +
        '</div>' +
        '<div class="theme-badges">' + badges + '</div>' +
        '</div>' +
        '<div class="theme-body"><div class="theme-body-inner">' +
        '<table class="issue-table">' +
        '<thead><tr><th>Key</th><th>Summary</th><th>Type</th><th>Priority</th><th>Status</th><th>Last Activity</th><th>Assignee</th></tr></thead>' +
        '<tbody>' + rows + '</tbody>' +
        '</table>' +
        '</div></div>' +
        '</div>';
    }

    el.innerHTML = html;

    // Wire collapse/expand on headers
    el.querySelectorAll('.theme-header').forEach(function(header) {
      header.addEventListener('click', function() {
        header.parentElement.classList.toggle('collapsed');
      });
    });

    // Wire expand/collapse all button
    var expandBtn = el.querySelector('[data-expand-all]');
    if (expandBtn) {
      expandBtn.addEventListener('click', function() {
        var sections = el.querySelectorAll('.theme-section');
        var allExpanded = true;
        for (var s = 0; s < sections.length; s++) {
          if (sections[s].classList.contains('collapsed')) { allExpanded = false; break; }
        }
        for (var e = 0; e < sections.length; e++) {
          if (allExpanded) sections[e].classList.add('collapsed');
          else sections[e].classList.remove('collapsed');
        }
        expandBtn.textContent = allExpanded ? 'Expand All' : 'Collapse All';
      });
    }
  }

  function addAsanaBadges(container) {
    var actions = (typeof INTELLIGENCE_DATA !== 'undefined') ? INTELLIGENCE_DATA.actions : null;
    if (!actions || !actions.available || !actions.tasks) return;

    // Build lookup: Jira key -> Asana task URL
    var jiraToAsana = {};
    for (var i = 0; i < actions.tasks.length; i++) {
      var t = actions.tasks[i];
      if (t.linked_jira) {
        jiraToAsana[t.linked_jira] = t.url || '#';
      }
    }
    if (Object.keys(jiraToAsana).length === 0) return;

    // Find all Jira issue key links in the issue table
    container.querySelectorAll('.issue-key').forEach(function(el) {
      var key = el.getAttribute('data-issue-key') || el.textContent.trim();
      if (jiraToAsana[key]) {
        var badge = document.createElement('a');
        badge.className = 'asana-badge';
        badge.href = jiraToAsana[key];
        badge.target = '_blank';
        badge.rel = 'noopener';
        badge.textContent = 'A';
        badge.title = 'View linked Asana task';
        el.parentElement.appendChild(badge);
      }
    });
  }

  // ── Filter system ──

  function buildFilters(el) {
    var html = '<div class="filter-bar">';

    // Status pills
    var statusPills = [
      { label: 'All', value: 'all' },
      { label: 'Active', value: 'active' },
      { label: 'Waiting', value: 'waiting' },
      { label: 'Resolved', value: 'resolved' },
      { label: 'Triage', value: 'triage' }
    ];
    for (var sp = 0; sp < statusPills.length; sp++) {
      var pill = statusPills[sp];
      var active = _filterState.status === pill.value ? ' active' : '';
      html += '<button class="filter-pill' + active + '" data-filter-status="' + pill.value + '">' + pill.label + '</button>';
    }

    html += '<span class="filter-sep"></span>';

    // Type pills
    var typePills = [
      { label: 'All', value: 'all' },
      { label: 'Bugs', value: 'Bug' },
      { label: 'Features', value: 'Feature Request' }
    ];
    for (var tp = 0; tp < typePills.length; tp++) {
      var tpill = typePills[tp];
      var tActive = _filterState.type === tpill.value ? ' active' : '';
      html += '<button class="filter-pill' + tActive + '" data-filter-type="' + tpill.value + '">' + tpill.label + '</button>';
    }

    html += '<span class="filter-sep"></span>';

    // Theme dropdown
    var themes = [];
    var seenThemes = {};
    for (var ti = 0; ti < _issues.length; ti++) {
      var th = _issues[ti].theme;
      if (th && !seenThemes[th]) {
        seenThemes[th] = true;
        themes.push(th);
      }
    }
    themes.sort();

    html += '<select class="filter-select" data-filter-theme>';
    html += '<option value="all"' + (_filterState.theme === 'all' ? ' selected' : '') + '>All Themes</option>';
    for (var td = 0; td < themes.length; td++) {
      var selected = _filterState.theme === themes[td] ? ' selected' : '';
      html += '<option value="' + escapeHtml(themes[td]) + '"' + selected + '>' + escapeHtml(themes[td]) + '</option>';
    }
    html += '</select>';

    html += '<span class="filter-sep"></span>';

    // Search input
    html += '<input type="text" class="filter-search" placeholder="Search issues..." value="' + escapeHtml(_filterState.search) + '" data-filter-search>';

    // Active filter badge
    var activeCount = 0;
    if (_filterState.status !== 'all') activeCount++;
    if (_filterState.type !== 'all') activeCount++;
    if (_filterState.theme !== 'all') activeCount++;
    if (_filterState.search) activeCount++;
    if (_filterState.bucket) activeCount++;
    if (activeCount > 0) {
      html += '<span class="filter-active-badge" data-filter-clear>&#x2715; Clear ' + activeCount + ' filter' + (activeCount !== 1 ? 's' : '') + '</span>';
    }

    html += '</div>';
    el.innerHTML = html;

    // Wire status pills
    el.querySelectorAll('[data-filter-status]').forEach(function(btn) {
      btn.addEventListener('click', function() {
        _filterState.status = btn.getAttribute('data-filter-status');
        _filterState.bucket = null;
        reRender();
      });
    });

    // Wire type pills
    el.querySelectorAll('[data-filter-type]').forEach(function(btn) {
      btn.addEventListener('click', function() {
        _filterState.type = btn.getAttribute('data-filter-type');
        reRender();
      });
    });

    // Wire theme dropdown
    var themeSelect = el.querySelector('[data-filter-theme]');
    if (themeSelect) {
      themeSelect.addEventListener('change', function() {
        _filterState.theme = themeSelect.value;
        reRender();
      });
    }

    // Wire search input with 300ms debounce
    var searchInput = el.querySelector('[data-filter-search]');
    if (searchInput) {
      searchInput.addEventListener('input', function() {
        if (_debounceTimer) clearTimeout(_debounceTimer);
        _debounceTimer = setTimeout(function() {
          _filterState.search = searchInput.value;
          reRender();
        }, 300);
      });
    }

    // Wire clear badge
    var clearBadge = el.querySelector('[data-filter-clear]');
    if (clearBadge) {
      clearBadge.addEventListener('click', function() {
        _filterState = { status: 'all', type: 'all', theme: 'all', search: '', bucket: null };
        reRender();
      });
    }
  }

  function reRender() {
    if (!_container || !_issues) return;
    var filtered = getFiltered();

    // Re-render filters (to update active state)
    var filterEl = _container.querySelector('[data-issues-filters]');
    if (filterEl) buildFilters(filterEl);

    // Re-render attention callouts (to show active state)
    var attentionEl = _container.querySelector('[data-issues-attention]');
    if (attentionEl) renderAttentionCallouts(attentionEl, _issues);

    // Re-render theme chart and themes
    var themeChartEl = _container.querySelector('[data-issues-theme-chart]');
    if (themeChartEl) renderThemeChart(themeChartEl, filtered);

    var themesEl = _container.querySelector('[data-issues-themes]');
    if (themesEl) {
      renderThemes(themesEl, filtered);
      addAsanaBadges(themesEl);
    }
  }

  // ── Registration ──

  PanelRegistry.register({
    id: 'issues',
    group: 'intelligence',
    label: 'Issues',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>',
    badgeKey: 'issues.length',
    dataKey: 'issues',

    render: function(container, data, config) {
      // data is INTELLIGENCE_DATA.issues array
      if (!data || !Array.isArray(data) || data.length === 0) {
        container.innerHTML = '<div class="empty-state">' +
          '<div class="section-label">Jira Issues</div>' +
          '<div>No Jira issues found for this customer.</div>' +
          '</div>';
        return { charts: [] };
      }

      // Store references for re-rendering
      _issues = data;
      _container = container;
      _config = config;
      _filterState = { status: 'all', type: 'all', theme: 'all', search: '', bucket: null };

      // Inject CSS
      if (typeof PanelRegistry.injectCSS === 'function') {
        PanelRegistry.injectCSS('issues', PANEL_CSS);
      }

      // Build DOM structure
      container.innerHTML = '' +
        '<div data-issues-health></div>' +
        '<div data-issues-attention></div>' +
        '<div class="two-col-grid">' +
        '  <div class="analytics-card" data-issues-velocity></div>' +
        '  <div class="analytics-card" data-issues-cadence></div>' +
        '</div>' +
        '<div data-issues-filters></div>' +
        '<div data-issues-theme-chart></div>' +
        '<div data-issues-themes></div>';

      // Render analysis section (not affected by filters)
      renderHealthSummary(container.querySelector('[data-issues-health]'), data);
      renderAttentionCallouts(container.querySelector('[data-issues-attention]'), data);
      renderVelocityChart(container.querySelector('[data-issues-velocity]'), data);
      renderCadenceMetrics(container.querySelector('[data-issues-cadence]'), data);

      // Render filter bar
      buildFilters(container.querySelector('[data-issues-filters]'));

      // Render filtered content
      var filtered = getFiltered();
      renderThemeChart(container.querySelector('[data-issues-theme-chart]'), filtered);
      renderThemes(container.querySelector('[data-issues-themes]'), filtered);

      // Add Asana badges after DOM is built
      addAsanaBadges(container);

      // All charts are CSS-based, not ECharts
      return { charts: [] };
    },

    getHeadlineStats: function(data) {
      if (!data || !Array.isArray(data) || data.length === 0) return [];
      var active = data.filter(function(i) {
        return RESOLVED_STATUSES.indexOf(i.status) === -1;
      });
      var bugs = active.filter(function(i) { return i.type === 'Bug'; });
      var p0p1 = active.filter(function(i) { return i.priority === 'P0' || i.priority === 'P1'; });
      return [
        { label: 'Open Issues', value: String(active.length), color: 'var(--text-primary)' },
        { label: 'Bugs', value: String(bugs.length), color: bugs.length > 0 ? 'var(--red)' : 'var(--text-tertiary)' },
        { label: 'P0/P1', value: String(p0p1.length), color: p0p1.length > 0 ? 'var(--red)' : 'var(--text-tertiary)' }
      ];
    },

    getAttentionItems: function(data) {
      if (!data || !Array.isArray(data) || data.length === 0) return [];
      var items = [];
      var nonResolved = data.filter(function(i) {
        return RESOLVED_STATUSES.indexOf(i.status) === -1;
      });

      // P0/P1 open issues
      var p0p1 = nonResolved.filter(function(i) { return i.priority === 'P0' || i.priority === 'P1'; });
      if (p0p1.length > 0) {
        items.push({ severity: 'high', text: p0p1.length + ' P0/P1 issues open', action: { panel: 'issues', filter: 'p0p1' } });
      }

      // Issues with no eng comment in 60+ days
      var noEng60 = nonResolved.filter(function(i) {
        var engDays = daysAgo(i.comments ? i.comments.last_eng_comment_date : null);
        return engDays > VERY_STALE_DAYS;
      });
      if (noEng60.length > 0) {
        items.push({ severity: 'high', text: noEng60.length + ' issues with no eng activity in 60+ days', action: { panel: 'issues', filter: 'stale60' } });
      }

      // Issues with no FE-UPDATE in 30+ days
      var noUpdate = nonResolved.filter(function(i) {
        if (!i.comments || !i.comments.fe_update_count || i.comments.fe_update_count === 0) return true;
        return false;
      });
      if (noUpdate.length > 0) {
        items.push({ severity: 'low', text: noUpdate.length + ' issues with no FE-UPDATE', action: { panel: 'issues', filter: 'no-update' } });
      }

      // Unassigned non-resolved
      var unassigned = nonResolved.filter(function(i) { return !i.assignee; });
      if (unassigned.length > 0) {
        items.push({ severity: 'medium', text: unassigned.length + ' unassigned issues', action: { panel: 'issues', filter: 'unassigned' } });
      }

      return items;
    }
  });

})();
