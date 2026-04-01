/**
 * Overview Panel — Dashboard V2
 *
 * Aggregator panel: iterates all registered panels via PanelRegistry.getAll(),
 * calls getHeadlineStats() and getAttentionItems() on each, and renders a
 * unified executive view. Shows changes-since-last-generation diff when
 * INTELLIGENCE_DATA._diff exists, and agent-generated narrative insights
 * when INTELLIGENCE_DATA._insights exists.
 *
 * This is the landing page SEs see first.
 *
 * No ECharts dependency — pure DOM rendering.
 * No ES module syntax (file:// CORS constraint).
 */
(function() {
  'use strict';

  // ── Helpers ──

  function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  /**
   * Walk dot-separated path through nested objects.
   * Handle `.length` suffix by returning array length.
   * Return undefined if path doesn't resolve.
   */
  function resolveKey(obj, dotPath) {
    if (!obj || !dotPath) return undefined;
    var parts = dotPath.split('.');
    var current = obj;
    for (var i = 0; i < parts.length; i++) {
      if (current === null || current === undefined) return undefined;
      if (parts[i] === 'length' && Array.isArray(current)) return current.length;
      current = current[parts[i]];
    }
    return current;
  }

  // ── Panel CSS ──

  var PANEL_CSS = '\
.overview-header {\
  margin-bottom: 32px;\
}\
.overview-title {\
  font-family: var(--font-display);\
  font-size: 24px;\
  font-weight: 400;\
  color: var(--text-primary);\
  margin-bottom: 8px;\
}\
.overview-subtitle {\
  font-family: var(--font-body);\
  font-size: 14px;\
  font-weight: 400;\
  color: var(--text-secondary);\
}\
.section-label {\
  font-family: var(--font-mono);\
  font-size: 11px;\
  font-weight: 600;\
  text-transform: uppercase;\
  letter-spacing: 1.5px;\
  color: var(--text-tertiary);\
  margin-bottom: 16px;\
}\
.stats-strip {\
  display: grid;\
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));\
  gap: 16px;\
  margin-bottom: 32px;\
}\
.stat-card {\
  background: var(--bg-elevated);\
  border: 1px solid var(--border-subtle);\
  border-radius: 6px;\
  padding: 20px;\
  cursor: pointer;\
  transition: border-color 0.15s, background 0.15s;\
}\
.stat-card:hover {\
  border-color: var(--accent-border);\
  background: var(--bg-hover);\
}\
.stat-value {\
  font-family: var(--font-body);\
  font-size: 28px;\
  font-weight: 600;\
  line-height: 1.1;\
}\
.stat-label {\
  font-family: var(--font-mono);\
  font-size: 11px;\
  font-weight: 600;\
  text-transform: uppercase;\
  letter-spacing: 1.5px;\
  color: var(--text-tertiary);\
  margin-top: 4px;\
}\
.stat-source {\
  font-family: var(--font-mono);\
  font-size: 11px;\
  font-weight: 400;\
  color: var(--text-tertiary);\
  opacity: 0.6;\
  margin-top: 2px;\
}\
.attention-section {\
  margin-bottom: 32px;\
}\
.attention-list {\
  display: flex;\
  flex-direction: column;\
  gap: 8px;\
}\
.attention-row {\
  display: flex;\
  align-items: center;\
  gap: 16px;\
  padding: 12px 16px;\
  background: var(--bg-elevated);\
  border-left: 3px solid var(--text-tertiary);\
  border-radius: 0 6px 6px 0;\
  cursor: pointer;\
  transition: background 0.15s;\
}\
.attention-row:hover {\
  background: var(--bg-hover);\
}\
.attention-row.high {\
  border-left-color: var(--red);\
}\
.attention-row.medium {\
  border-left-color: var(--orange);\
}\
.attention-row.low {\
  border-left-color: var(--amber);\
}\
.attention-row.info {\
  border-left-color: var(--blue);\
}\
.attention-severity {\
  font-family: var(--font-mono);\
  font-size: 11px;\
  font-weight: 600;\
  text-transform: uppercase;\
  width: 60px;\
  flex-shrink: 0;\
}\
.attention-text {\
  font-family: var(--font-body);\
  font-size: 14px;\
  font-weight: 400;\
  color: var(--text-secondary);\
  flex: 1;\
}\
.attention-action {\
  font-family: var(--font-mono);\
  font-size: 11px;\
  font-weight: 400;\
  color: var(--accent);\
  opacity: 0;\
  transition: opacity 0.15s;\
}\
.attention-row:hover .attention-action {\
  opacity: 1;\
}\
.diff-section {\
  margin-bottom: 32px;\
  background: var(--bg-elevated);\
  border: 1px solid var(--border-subtle);\
  border-radius: 6px;\
  padding: 24px;\
}\
.diff-header {\
  display: flex;\
  justify-content: space-between;\
  align-items: center;\
  margin-bottom: 16px;\
}\
.diff-title {\
  font-family: var(--font-mono);\
  font-size: 11px;\
  font-weight: 600;\
  text-transform: uppercase;\
  color: var(--text-tertiary);\
}\
.diff-date {\
  font-family: var(--font-mono);\
  font-size: 11px;\
  font-weight: 400;\
  color: var(--text-tertiary);\
}\
.diff-grid {\
  display: grid;\
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));\
  gap: 16px;\
}\
.diff-item {\
  display: flex;\
  flex-direction: column;\
}\
.diff-item-label {\
  font-family: var(--font-mono);\
  font-size: 11px;\
  font-weight: 600;\
  text-transform: uppercase;\
  color: var(--text-tertiary);\
}\
.diff-item-value {\
  font-family: var(--font-body);\
  font-size: 14px;\
  font-weight: 600;\
  color: var(--text-primary);\
  margin-top: 4px;\
}\
.diff-item-value.positive {\
  color: var(--green);\
}\
.diff-item-value.negative {\
  color: var(--red);\
}\
.diff-item-value.neutral {\
  color: var(--text-secondary);\
}\
.narrative-section {\
  margin-bottom: 32px;\
}\
.narrative-text {\
  font-family: var(--font-body);\
  font-size: 14px;\
  font-weight: 400;\
  color: var(--text-secondary);\
  line-height: 1.55;\
}\
.empty-overview {\
  text-align: center;\
  padding: 48px 24px;\
}\
.empty-overview-title {\
  font-family: var(--font-display);\
  font-size: 24px;\
  font-weight: 400;\
  color: var(--text-primary);\
  margin-bottom: 8px;\
}\
.empty-overview-desc {\
  font-family: var(--font-body);\
  font-size: 14px;\
  font-weight: 400;\
  color: var(--text-secondary);\
  max-width: 400px;\
  margin: 0 auto;\
}\
';

  // ── Icon SVG (grid icon — 4 squares) ──

  var ICON_SVG = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"></rect><rect x="14" y="3" width="7" height="7" rx="1"></rect><rect x="3" y="14" width="7" height="7" rx="1"></rect><rect x="14" y="14" width="7" height="7" rx="1"></rect></svg>';

  // ── Severity ordering ──

  var SEVERITY_ORDER = { 'high': 0, 'medium': 1, 'low': 2, 'info': 3 };
  var SEVERITY_COLORS = {
    'high': 'var(--red)',
    'medium': 'var(--orange)',
    'low': 'var(--amber)',
    'info': 'var(--blue)'
  };

  // ── Registration ──

  PanelRegistry.register({
    id: 'overview',
    group: 'intelligence',
    label: 'Overview',
    icon: ICON_SVG,
    dataKey: null,
    always_show: true,

    render: function(container, data, config) {
      // Inject scoped CSS on first render
      if (!document.querySelector('style[data-panel="overview"]')) {
        PanelRegistry.injectCSS('overview', PANEL_CSS);
      }

      var customerName = (typeof INTELLIGENCE_DATA !== 'undefined' && INTELLIGENCE_DATA.customer) || 'Customer';

      // ── 1. Aggregate stats from all panels ──
      var allStats = [];
      var allAttention = [];
      var panels = PanelRegistry.getAll();

      for (var p = 0; p < panels.length; p++) {
        var panel = panels[p];
        if (panel.id === 'overview') continue;

        try {
          var panelData = panel.dataKey ? resolveKey(INTELLIGENCE_DATA, panel.dataKey) : null;
          if (!panelData) continue;

          // Collect headline stats
          var stats = panel.getHeadlineStats(panelData);
          if (stats && stats.length > 0) {
            for (var s = 0; s < stats.length; s++) {
              allStats.push({
                label: stats[s].label,
                value: stats[s].value,
                color: stats[s].color || 'var(--text-primary)',
                source: panel.label
              });
            }
          }

          // Collect attention items
          var items = panel.getAttentionItems(panelData);
          if (items && items.length > 0) {
            for (var a = 0; a < items.length; a++) {
              allAttention.push(items[a]);
            }
          }
        } catch (e) {
          console.warn('[Overview] Error aggregating panel ' + panel.id + ':', e);
        }
      }

      // Sort attention items by severity
      allAttention.sort(function(a, b) {
        var sa = SEVERITY_ORDER[a.severity] !== undefined ? SEVERITY_ORDER[a.severity] : 99;
        var sb = SEVERITY_ORDER[b.severity] !== undefined ? SEVERITY_ORDER[b.severity] : 99;
        return sa - sb;
      });

      // ── Check if we have any data at all ──
      if (allStats.length === 0 && allAttention.length === 0) {
        container.innerHTML =
          '<div class="empty-overview">' +
            '<div class="empty-overview-title">No Intelligence Data</div>' +
            '<div class="empty-overview-desc">Run /customer-snapshot to generate this dashboard with the latest data from Jira, Slack, BigQuery, and Asana.</div>' +
          '</div>';
        return { charts: [] };
      }

      var html = '';

      // ── 2. Header ──
      html += '<div class="overview-header">' +
        '<div class="overview-title">' + escapeHtml(customerName) + '</div>' +
        '<div class="overview-subtitle">Executive Overview</div>' +
      '</div>';

      // ── 3. Aggregated stats strip ──
      // Map panel labels to panel IDs for click navigation
      var sourceToPanelId = {};
      for (var mp = 0; mp < panels.length; mp++) {
        sourceToPanelId[panels[mp].label] = panels[mp].id;
      }

      if (allStats.length > 0) {
        html += '<div class="section-label">Key Metrics</div>';
        html += '<div class="stats-strip">';
        for (var si = 0; si < allStats.length; si++) {
          var stat = allStats[si];
          var targetPanelId = sourceToPanelId[stat.source] || '';
          html += '<div class="stat-card" data-source-panel="' + escapeHtml(targetPanelId) + '">' +
            '<div class="stat-value" style="color:' + stat.color + '">' + escapeHtml(stat.value) + '</div>' +
            '<div class="stat-label">' + escapeHtml(stat.label) + '</div>' +
            '<div class="stat-source">' + escapeHtml(stat.source) + '</div>' +
          '</div>';
        }
        html += '</div>';
      }

      // ── 4. Attention items ──
      if (allAttention.length > 0) {
        html += '<div class="attention-section">';
        html += '<div class="section-label">Attention Required (' + allAttention.length + ')</div>';
        html += '<div class="attention-list">';

        for (var ai = 0; ai < allAttention.length; ai++) {
          var item = allAttention[ai];
          var sevClass = item.severity || 'info';
          var sevColor = SEVERITY_COLORS[sevClass] || 'var(--text-tertiary)';
          var targetPanel = (item.action && item.action.panel) || '';

          html += '<div class="attention-row ' + sevClass + '" data-target-panel="' + escapeHtml(targetPanel) + '"' +
            (item.action && item.action.filter ? ' data-target-filter="' + escapeHtml(item.action.filter) + '"' : '') + '>' +
            '<span class="attention-severity" style="color:' + sevColor + '">' + escapeHtml(sevClass) + '</span>' +
            '<span class="attention-text">' + escapeHtml(item.text) + '</span>' +
            '<span class="attention-action">View &rarr;</span>' +
          '</div>';
        }

        html += '</div>';
        html += '</div>';
      }

      // ── 5. Changes since last generation (diff) ──
      var diff = typeof INTELLIGENCE_DATA !== 'undefined' ? INTELLIGENCE_DATA._diff : null;
      if (diff && diff.previous_date) {
        html += '<div class="diff-section">';
        html += '<div class="diff-header">' +
          '<span class="diff-title">Changes Since Last Generation</span>' +
          '<span class="diff-date">' + escapeHtml(diff.previous_date) + '</span>' +
        '</div>';

        html += '<div class="diff-grid">';

        // New issues
        var newIssueCount = diff.new_issues ? diff.new_issues.length : 0;
        html += '<div class="diff-item">' +
          '<span class="diff-item-label">New Issues</span>' +
          '<span class="diff-item-value' + (newIssueCount > 0 ? ' negative' : ' neutral') + '">' +
          (newIssueCount > 0 ? '+' + newIssueCount : '0') + '</span>' +
        '</div>';

        // Resolved issues
        var resolvedCount = diff.resolved_issues ? diff.resolved_issues.length : 0;
        html += '<div class="diff-item">' +
          '<span class="diff-item-label">Resolved Issues</span>' +
          '<span class="diff-item-value' + (resolvedCount > 0 ? ' positive' : ' neutral') + '">' +
          (resolvedCount > 0 ? '+' + resolvedCount : '0') + '</span>' +
        '</div>';

        // New tickets
        if (diff.new_tickets !== undefined && diff.new_tickets !== null) {
          var ticketCls = diff.new_tickets > 0 ? 'negative' : diff.new_tickets < 0 ? 'positive' : 'neutral';
          var ticketPrefix = diff.new_tickets > 0 ? '+' : '';
          html += '<div class="diff-item">' +
            '<span class="diff-item-label">Ticket Change</span>' +
            '<span class="diff-item-value ' + ticketCls + '">' + ticketPrefix + diff.new_tickets + '</span>' +
          '</div>';
        }

        // Seat change
        if (diff.seat_change !== undefined && diff.seat_change !== null) {
          var seatCls = diff.seat_change > 0 ? 'positive' : diff.seat_change < 0 ? 'negative' : 'neutral';
          var seatPrefix = diff.seat_change > 0 ? '+' : '';
          html += '<div class="diff-item">' +
            '<span class="diff-item-label">Seat Change</span>' +
            '<span class="diff-item-value ' + seatCls + '">' + seatPrefix + diff.seat_change + '</span>' +
          '</div>';
        }

        // Sentiment change
        if (diff.sentiment_change) {
          html += '<div class="diff-item">' +
            '<span class="diff-item-label">Sentiment</span>' +
            '<span class="diff-item-value neutral">' + escapeHtml(diff.sentiment_change) + '</span>' +
          '</div>';
        }

        html += '</div>';
        html += '</div>';
      }

      // ── 6. Narrative insights ──
      var insights = typeof INTELLIGENCE_DATA !== 'undefined' ? INTELLIGENCE_DATA._insights : null;
      if (insights && insights.length > 0) {
        html += '<div class="narrative-section">';
        html += '<div class="section-label">Narrative Insights</div>';
        for (var ni = 0; ni < insights.length; ni++) {
          html += '<p class="narrative-text">' + escapeHtml(insights[ni]) + '</p>';
        }
        html += '</div>';
      }

      container.innerHTML = html;

      // ── Wire stat card click handlers ──
      var cards = container.querySelectorAll('.stat-card[data-source-panel]');
      for (var ci = 0; ci < cards.length; ci++) {
        cards[ci].addEventListener('click', function() {
          var panelId = this.getAttribute('data-source-panel');
          if (panelId && typeof navigateTo === 'function') {
            navigateTo(panelId, true);
          }
        });
      }

      // ── Wire attention row click handlers ──
      var rows = container.querySelectorAll('.attention-row[data-target-panel]');
      for (var ri = 0; ri < rows.length; ri++) {
        rows[ri].addEventListener('click', function() {
          var targetId = this.getAttribute('data-target-panel');
          var filter = this.getAttribute('data-target-filter');
          if (targetId && typeof navigateTo === 'function') {
            navigateTo(targetId, true);
            if (filter) {
              window.dispatchEvent(new CustomEvent('panel-filter', {
                detail: { panel: targetId, filter: filter }
              }));
            }
          }
        });
      }

      return { charts: [] };
    },

    getHeadlineStats: function(data) {
      // Overview doesn't contribute stats to itself
      return [];
    },

    getAttentionItems: function(data) {
      // Overview doesn't contribute attention items
      return [];
    }
  });

})();
