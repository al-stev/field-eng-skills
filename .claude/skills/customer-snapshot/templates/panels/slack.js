/**
 * Slack Panel — Dashboard V2
 *
 * Slack sentiment panel extracted from v1 intelligence-dashboard.html renderSentimentPanel().
 * Renders sentiment score display, channel summary, hot threads with Slack links,
 * and internal-only risk signals and recommended actions.
 *
 * No ECharts dependency — pure DOM rendering.
 */
(function() {
  'use strict';

  // ── Constants (self-contained, copied from v1) ──

  var SENTIMENT_LABELS = {
    'positive': 'Positive',
    'neutral': 'Neutral',
    'cautiously-negative': 'Cautiously Negative',
    'negative': 'Negative',
    'critical': 'Critical'
  };

  var SENTIMENT_COLOURS = {
    'positive': 'var(--green)',
    'neutral': 'var(--text-secondary)',
    'cautiously-negative': 'var(--amber)',
    'negative': 'var(--orange)',
    'critical': 'var(--red)'
  };

  // ── Panel CSS ──

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
.sentiment-header {\
  display: flex;\
  align-items: center;\
  gap: 12px;\
  margin-bottom: 16px;\
}\
.sentiment-score-display {\
  font-family: var(--font-body);\
  font-size: 28px;\
  font-weight: 600;\
  line-height: 1.1;\
}\
.sentiment-numeric {\
  font-family: var(--font-mono);\
  font-size: 11px;\
  font-weight: 400;\
  color: var(--text-tertiary);\
}\
.sentiment-summary {\
  font-family: var(--font-body);\
  font-size: 14px;\
  font-weight: 400;\
  color: var(--text-secondary);\
  margin-bottom: 16px;\
  line-height: 1.55;\
}\
.sentiment-channels {\
  font-family: var(--font-mono);\
  font-size: 11px;\
  font-weight: 400;\
  color: var(--text-tertiary);\
  margin-bottom: 24px;\
}\
.hot-threads-list {\
  display: flex;\
  flex-direction: column;\
  gap: 12px;\
}\
.hot-thread {\
  background: var(--bg-elevated);\
  border: 1px solid var(--border-subtle);\
  border-radius: 6px;\
  padding: 16px;\
}\
.hot-thread-channel {\
  font-family: var(--font-mono);\
  font-size: 11px;\
  font-weight: 600;\
  color: var(--accent);\
}\
.hot-thread-summary {\
  font-family: var(--font-body);\
  font-size: 14px;\
  font-weight: 400;\
  color: var(--text-primary);\
  display: block;\
  margin-top: 4px;\
  line-height: 1.55;\
}\
.hot-thread-meta {\
  display: flex;\
  gap: 12px;\
  margin-top: 8px;\
  align-items: center;\
}\
.hot-thread-stat {\
  font-family: var(--font-mono);\
  font-size: 11px;\
  font-weight: 400;\
  color: var(--text-tertiary);\
}\
.hot-thread-sentiment {\
  font-family: var(--font-mono);\
  font-size: 11px;\
  font-weight: 600;\
  text-transform: uppercase;\
}\
.hot-thread-link {\
  font-family: var(--font-mono);\
  font-size: 11px;\
  font-weight: 400;\
  color: var(--blue);\
  text-decoration: none;\
  margin-left: auto;\
}\
.hot-thread-link:hover {\
  text-decoration: underline;\
}\
.sentiment-unavailable {\
  font-family: var(--font-body);\
  font-size: 14px;\
  font-weight: 400;\
  color: var(--text-secondary);\
  padding: 24px;\
}\
.internal-section {\
  margin-top: 24px;\
  border-top: 1px solid var(--border-subtle);\
  padding-top: 24px;\
}\
.internal-section-label {\
  font-family: var(--font-mono);\
  font-size: 11px;\
  font-weight: 600;\
  text-transform: uppercase;\
  letter-spacing: 1.5px;\
  color: var(--text-tertiary);\
  margin-bottom: 8px;\
}\
.internal-text {\
  font-family: var(--font-body);\
  font-size: 14px;\
  font-weight: 400;\
  color: var(--text-secondary);\
  line-height: 1.55;\
  margin-bottom: 16px;\
}\
.risk-list,\
.action-list {\
  list-style: none;\
  padding: 0;\
  margin: 0 0 16px 0;\
}\
.risk-list li,\
.action-list li {\
  font-family: var(--font-body);\
  font-size: 14px;\
  font-weight: 400;\
  color: var(--text-secondary);\
  padding: 4px 0;\
  line-height: 1.55;\
}\
.risk-list li::before {\
  content: "\\26A0\\FE0F ";\
}\
.action-list li::before {\
  content: "\\25B6 ";\
  color: var(--accent);\
}\
';

  // ── Icon SVG (Slack-style icon from shell.html) ──

  var ICON_SVG = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 10c-.8 0-1.5-.7-1.5-1.5v-5c0-.8.7-1.5 1.5-1.5s1.5.7 1.5 1.5v5c0 .8-.7 1.5-1.5 1.5z"></path><path d="M20.5 10H19v-1.5c0-.8.7-1.5 1.5-1.5s1.5.7 1.5 1.5-.7 1.5-1.5 1.5z"></path><path d="M9.5 14c.8 0 1.5.7 1.5 1.5v5c0 .8-.7 1.5-1.5 1.5S8 21.3 8 20.5v-5c0-.8.7-1.5 1.5-1.5z"></path><path d="M3.5 14H5v1.5c0 .8-.7 1.5-1.5 1.5S2 16.3 2 15.5 2.7 14 3.5 14z"></path><path d="M14 14.5c0-.8.7-1.5 1.5-1.5h5c.8 0 1.5.7 1.5 1.5s-.7 1.5-1.5 1.5h-5c-.8 0-1.5-.7-1.5-1.5z"></path><path d="M14 20.5c0 .8-.7 1.5-1.5 1.5S11 21.3 11 20.5V19h1.5c.8 0 1.5.7 1.5 1.5z"></path><path d="M10 9.5C10 10.3 9.3 11 8.5 11h-5C2.7 11 2 10.3 2 9.5S2.7 8 3.5 8h5c.8 0 1.5.7 1.5 1.5z"></path><path d="M10 3.5C10 2.7 10.7 2 11.5 2S13 2.7 13 3.5V5h-1.5c-.8 0-1.5-.7-1.5-1.5z"></path><rect x="7" y="7" width="10" height="10" rx="0.5"></rect></svg>';

  // ── Helpers ──

  function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  // ── Registration ──

  PanelRegistry.register({
    id: 'slack',
    group: 'activity',
    label: 'Slack',
    icon: ICON_SVG,
    badgeKey: 'sentiment.hot_threads.length',
    dataKey: 'sentiment',

    render: function(container, data, config) {
      // Inject scoped CSS on first render
      if (!document.querySelector('style[data-panel="slack"]')) {
        PanelRegistry.injectCSS('slack', PANEL_CSS);
      }

      // Graceful degradation: null = not configured, available=false = unavailable
      if (!data || !data.available) {
        var msg = data === null
          ? 'Not configured &mdash; add Slack channels to templates/customers.yaml'
          : 'Slack data unavailable for this period';
        container.innerHTML =
          '<div class="section-label">Channel Sentiment</div>' +
          '<div class="sentiment-unavailable">' + msg + '</div>';
        return { charts: [] };
      }

      var scoreLabel = SENTIMENT_LABELS[data.overall && data.overall.score] || (data.overall && data.overall.score) || 'Unknown';
      var scoreColor = SENTIMENT_COLOURS[data.overall && data.overall.score] || 'var(--text-secondary)';
      var numericDisplay = data.overall && data.overall.numeric !== undefined
        ? data.overall.numeric.toFixed(1) : '';

      var html = '<div class="section-label">Channel Sentiment</div>' +
        '<div class="sentiment-header">' +
          '<span class="sentiment-score-display" style="color:' + scoreColor + '">' + escapeHtml(scoreLabel) + '</span>' +
          '<span class="sentiment-numeric">' + numericDisplay + '</span>' +
        '</div>';

      // Summary text
      if (data.overall && data.overall.summary) {
        html += '<div class="sentiment-summary">' + escapeHtml(data.overall.summary) + '</div>';
      }

      // Channels analyzed + period
      var channels = (data.channels_analyzed || []).join(', ');
      var period = data.period
        ? data.period.start + ' to ' + data.period.end
        : '';
      if (channels || period) {
        html += '<div class="sentiment-channels">' +
          escapeHtml(channels) +
          (channels && period ? ' &middot; ' : '') +
          escapeHtml(period) +
        '</div>';
      }

      // Hot threads (up to 5)
      if (data.hot_threads && data.hot_threads.length > 0) {
        var threads = data.hot_threads.slice(0, 5);
        html += '<div class="section-label" style="margin-top:8px">Hot Threads</div>';
        html += '<div class="hot-threads-list">';

        for (var i = 0; i < threads.length; i++) {
          var t = threads[i];
          var sentColor = SENTIMENT_COLOURS[t.sentiment] || 'var(--text-tertiary)';
          var sentLabel = (t.sentiment || 'negative').replace(/-/g, ' ');
          var link = t.url
            ? '<a class="hot-thread-link" href="' + escapeHtml(t.url) + '" target="_blank" rel="noopener">View in Slack</a>'
            : '';

          html += '<div class="hot-thread">' +
            '<span class="hot-thread-channel">' + escapeHtml(t.channel) + '</span>' +
            '<span class="hot-thread-summary">' + escapeHtml(t.summary) + '</span>' +
            '<div class="hot-thread-meta">' +
              '<span class="hot-thread-stat">' + (t.message_count || 0) + ' msgs</span>' +
              '<span class="hot-thread-stat">' + (t.participants || 0) + ' people</span>' +
              '<span class="hot-thread-sentiment" style="color:' + sentColor + '">' + escapeHtml(sentLabel) + '</span>' +
              link +
            '</div>' +
          '</div>';
        }

        html += '</div>';
      }

      // Internal-only section (risk signals + recommended actions)
      if (config && config.audience === 'internal' && data.internal) {
        html += '<div class="internal-section">';

        if (data.internal.raw_analysis) {
          html += '<div class="internal-section-label">Internal Analysis</div>';
          html += '<div class="internal-text">' + escapeHtml(data.internal.raw_analysis) + '</div>';
        }

        if (data.internal.risk_signals && data.internal.risk_signals.length > 0) {
          html += '<div class="internal-section-label">Risk Signals</div>';
          html += '<ul class="risk-list">';
          for (var r = 0; r < data.internal.risk_signals.length; r++) {
            html += '<li>' + escapeHtml(data.internal.risk_signals[r]) + '</li>';
          }
          html += '</ul>';
        }

        if (data.internal.recommended_actions && data.internal.recommended_actions.length > 0) {
          html += '<div class="internal-section-label">Recommended Actions</div>';
          html += '<ul class="action-list">';
          for (var a = 0; a < data.internal.recommended_actions.length; a++) {
            html += '<li>' + escapeHtml(data.internal.recommended_actions[a]) + '</li>';
          }
          html += '</ul>';
        }

        html += '</div>';
      }

      container.innerHTML = html;
      return { charts: [] };
    },

    getHeadlineStats: function(data) {
      if (!data || !data.available) return [];
      var scoreColor = SENTIMENT_COLOURS[data.overall && data.overall.score] || 'var(--text-secondary)';
      return [
        { label: 'Sentiment', value: SENTIMENT_LABELS[data.overall && data.overall.score] || 'Unknown', color: scoreColor },
        { label: 'Hot Threads', value: String(data.hot_threads ? data.hot_threads.length : 0), color: (data.hot_threads && data.hot_threads.length > 0) ? 'var(--orange)' : 'var(--text-tertiary)' }
      ];
    },

    getAttentionItems: function(data) {
      if (!data || !data.available) return [];
      var items = [];
      var score = data.overall && data.overall.score;

      // Flag negative or critical sentiment
      if (score === 'negative' || score === 'critical') {
        var label = SENTIMENT_LABELS[score] || score;
        items.push({ severity: 'high', text: 'Slack sentiment is ' + label, action: { panel: 'slack' } });
      }

      // Flag many hot threads
      if (data.hot_threads && data.hot_threads.length > 2) {
        items.push({ severity: 'medium', text: data.hot_threads.length + ' hot threads in Slack', action: { panel: 'slack' } });
      }

      // Flag risk signals
      if (data.internal && data.internal.risk_signals && data.internal.risk_signals.length > 0) {
        items.push({ severity: 'high', text: data.internal.risk_signals.length + ' risk signals detected', action: { panel: 'slack' } });
      }

      return items;
    }
  });

})();
