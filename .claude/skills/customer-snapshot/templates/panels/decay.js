/**
 * Engagement Decay Panel — Dashboard V2
 *
 * Three visualizations:
 *   1. Cold Detection table with inline sparklines
 *   2. Engagement Trend line chart with danger zones
 *   3. Decay Distribution histogram
 *
 * Registers with PanelRegistry. No ES module syntax.
 */
(function() {
  'use strict';

  // --- Dark mode detection ---
  function isDark() {
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  }

  // --- CSS (auto-scoped by shell via #panel-decay prefix) ---
  var PANEL_CSS = '\
.stats-strip {\
  display: grid;\
  grid-template-columns: repeat(4, 1fr);\
  gap: 16px;\
  margin-bottom: 32px;\
}\
.stat-card {\
  background: var(--bg-elevated);\
  border: 1px solid var(--border-subtle);\
  border-radius: 6px;\
  padding: 20px;\
}\
.stat-value {\
  font-family: "Outfit", system-ui, sans-serif;\
  font-size: 28px;\
  font-weight: 600;\
  line-height: 1.1;\
}\
.stat-label {\
  font-family: "JetBrains Mono", monospace;\
  font-size: 11px;\
  font-weight: 600;\
  text-transform: uppercase;\
  letter-spacing: 1.5px;\
  color: var(--text-tertiary);\
  margin-top: 6px;\
}\
.stat-sub {\
  font-family: "JetBrains Mono", monospace;\
  font-size: 11px;\
  font-weight: 400;\
  color: var(--text-tertiary);\
  margin-top: 4px;\
}\
.section-label {\
  font-family: "JetBrains Mono", monospace;\
  font-size: 11px;\
  font-weight: 600;\
  text-transform: uppercase;\
  letter-spacing: 1.5px;\
  color: var(--text-tertiary);\
  margin-bottom: 16px;\
}\
.two-col {\
  display: grid;\
  grid-template-columns: 1fr 1fr;\
  gap: 24px;\
  margin-bottom: 32px;\
}\
.panel-card {\
  background: var(--bg-elevated);\
  border: 1px solid var(--border-subtle);\
  border-radius: 6px;\
  padding: 24px;\
}\
.full-width {\
  margin-bottom: 32px;\
}\
.decay-table {\
  width: 100%;\
  border-collapse: collapse;\
}\
.decay-table th {\
  font-family: "JetBrains Mono", monospace;\
  font-size: 11px;\
  font-weight: 600;\
  text-transform: uppercase;\
  letter-spacing: 1.5px;\
  color: var(--text-tertiary);\
  text-align: left;\
  padding: 8px 12px;\
  border-bottom: 1px solid var(--border-subtle);\
}\
.decay-table td {\
  padding: 8px 12px;\
  border-bottom: 1px solid var(--border-subtle);\
  font-family: "Outfit", system-ui, sans-serif;\
  font-size: 14px;\
}\
.decay-table tr:hover {\
  background: var(--bg-hover);\
}\
.decay-table tr:last-child td {\
  border-bottom: none;\
}\
.status-badge {\
  display: inline-block;\
  padding: 2px 8px;\
  border-radius: 4px;\
  font-family: "JetBrains Mono", monospace;\
  font-size: 11px;\
  font-weight: 600;\
  text-transform: uppercase;\
  letter-spacing: 1px;\
}\
.status-cold {\
  background: var(--red-dim);\
  color: var(--red);\
  border: 1px solid var(--red-border);\
}\
.status-cooling {\
  background: var(--amber-dim);\
  color: var(--amber);\
  border: 1px solid var(--amber-border);\
}\
.status-active {\
  background: var(--green-dim);\
  color: var(--green);\
  border: 1px solid var(--green-border);\
}\
.champion-badge {\
  display: inline-block;\
  margin-left: 6px;\
  padding: 1px 6px;\
  border-radius: 3px;\
  background: var(--accent-dim);\
  color: var(--accent);\
  font-family: "JetBrains Mono", monospace;\
  font-size: 10px;\
  font-weight: 600;\
  letter-spacing: 1px;\
}\
.decay-expand-toggle {\
  cursor: pointer;\
  font-family: "JetBrains Mono", monospace;\
  font-size: 11px;\
  font-weight: 600;\
  color: var(--text-secondary);\
  margin-top: 12px;\
  display: inline-block;\
  user-select: none;\
}\
.decay-expand-toggle:hover {\
  color: var(--accent);\
}\
@media (max-width: 700px) {\
  .stats-strip {\
    grid-template-columns: repeat(2, 1fr);\
  }\
  .two-col {\
    grid-template-columns: 1fr;\
  }\
}\
';

  // --- HELPERS ---

  /**
   * Format a number with commas.
   */
  function fmt(n) {
    if (n === null || n === undefined) return '--';
    return Number(n).toLocaleString();
  }

  /**
   * Format a decay percentage with color.
   */
  function decayColor(pct) {
    if (pct >= 80) return 'var(--red)';
    if (pct >= 50) return 'var(--amber)';
    return 'var(--green)';
  }

  /**
   * Escape HTML entities.
   */
  function esc(str) {
    if (!str) return '';
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  // --- REGISTRATION ---
  PanelRegistry.register({
    id: 'decay',
    group: 'user-intel',
    label: 'Engagement Decay',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 18 13.5 8.5 8.5 13.5 1 6"></polyline><polyline points="17 18 23 18 23 12"></polyline></svg>',
    dataKey: 'analytics.decay',

    render: function(container, data, config) {
      var charts = [];

      // CSS injection guard
      if (!document.querySelector('style[data-panel="decay"]')) {
        if (typeof PanelRegistry.injectCSS === 'function') {
          PanelRegistry.injectCSS('decay', PANEL_CSS);
        }
      }

      // Empty state
      if (!data || !data.available) {
        container.innerHTML =
          '<div class="placeholder-panel">' +
            '<div class="placeholder-icon">' +
              '<svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="var(--text-tertiary)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">' +
                '<polyline points="23 18 13.5 8.5 8.5 13.5 1 6"></polyline>' +
                '<polyline points="17 18 23 18 23 12"></polyline>' +
              '</svg>' +
            '</div>' +
            '<div class="placeholder-title">Engagement Decay</div>' +
            '<div class="placeholder-desc">No engagement decay data available. This requires daily engagement score history in BigQuery.</div>' +
          '</div>';
        return { charts: [] };
      }

      // --- KPI Stats Strip ---
      var kpis = data.kpis || [];
      var kpiHtml = '<div class="stats-strip">';
      for (var k = 0; k < kpis.length; k++) {
        kpiHtml += '<div class="stat-card">' +
          '<div class="stat-value" style="color:var(--text-primary)">' + esc(kpis[k].value) + '</div>' +
          '<div class="stat-label">' + esc(kpis[k].label) + '</div>' +
        '</div>';
      }
      kpiHtml += '</div>';

      // --- Cold Detection Table ---
      var coldUsers = (data.cold_users || []).slice().sort(function(a, b) {
        return (b.decay_pct || 0) - (a.decay_pct || 0);
      });
      var showLimit = 20;
      var hasMore = coldUsers.length > showLimit;

      var tableHtml = '<div class="full-width">' +
        '<div class="section-label">Cold Detection</div>' +
        '<div class="panel-card">' +
          '<table class="decay-table">' +
            '<thead><tr>' +
              '<th>User</th>' +
              '<th>Status</th>' +
              '<th>Last Active</th>' +
              '<th style="text-align:right">Days Inactive</th>' +
              '<th style="text-align:right">Decay %</th>' +
              '<th>Sparkline</th>' +
            '</tr></thead>' +
            '<tbody>';

      for (var i = 0; i < coldUsers.length; i++) {
        var user = coldUsers[i];
        var hiddenClass = (i >= showLimit && hasMore) ? ' style="display:none" data-decay-extra="true"' : '';
        var statusClass = 'status-' + (user.status || 'active');
        var statusLabel = (user.status || 'active').toUpperCase();
        var champHtml = user.is_champion ? '<span class="champion-badge">CHAMPION</span>' : '';
        var displayName = esc(user.display_name || user.username || 'Unknown');
        var lastActive = user.last_active ? user.last_active.slice(0, 10) : '--';

        tableHtml += '<tr' + hiddenClass + '>' +
          '<td>' + displayName + champHtml + '</td>' +
          '<td><span class="status-badge ' + statusClass + '">' + statusLabel + '</span></td>' +
          '<td style="font-family:JetBrains Mono,monospace;font-size:11px;color:var(--text-tertiary)">' + lastActive + '</td>' +
          '<td style="text-align:right;font-family:JetBrains Mono,monospace;font-size:11px">' + (user.days_inactive != null ? user.days_inactive : '--') + '</td>' +
          '<td style="text-align:right;font-family:JetBrains Mono,monospace;font-size:11px;color:' + decayColor(user.decay_pct || 0) + '">' + (user.decay_pct != null ? Math.round(user.decay_pct) + '%' : '--') + '</td>' +
          '<td><div id="decay-spark-' + i + '" style="width:120px;height:32px;display:inline-block;"></div></td>' +
        '</tr>';
      }

      tableHtml += '</tbody></table>';

      if (hasMore) {
        tableHtml += '<div class="decay-expand-toggle" id="decay-expand-btn">Show all ' + coldUsers.length + ' users</div>';
      }

      tableHtml += '</div></div>';

      // --- Chart containers ---
      var chartsHtml =
        '<div class="two-col">' +
          '<div>' +
            '<div class="section-label">Engagement Trend</div>' +
            '<div class="panel-card">' +
              '<div id="decay-trend-chart" style="width:100%;height:320px;"></div>' +
            '</div>' +
          '</div>' +
          '<div>' +
            '<div class="section-label">Decay Distribution</div>' +
            '<div class="panel-card">' +
              '<div id="decay-dist-chart" style="width:100%;height:320px;"></div>' +
            '</div>' +
          '</div>' +
        '</div>';

      container.innerHTML = kpiHtml + tableHtml + chartsHtml;

      // --- Expand toggle handler ---
      if (hasMore) {
        var expandBtn = container.querySelector('#decay-expand-btn');
        if (expandBtn) {
          var expanded = false;
          expandBtn.addEventListener('click', function() {
            expanded = !expanded;
            var extraRows = container.querySelectorAll('[data-decay-extra]');
            for (var r = 0; r < extraRows.length; r++) {
              extraRows[r].style.display = expanded ? '' : 'none';
            }
            expandBtn.textContent = expanded ? 'Show first 20 users' : 'Show all ' + coldUsers.length + ' users';
          });
        }
      }

      // --- Sparkline rendering ---
      var sparkColor = isDark() ? '#60a5fa' : '#3b82f6';
      for (var s = 0; s < coldUsers.length; s++) {
        (function(idx) {
          setTimeout(function() {
            var sparkEl = container.querySelector('#decay-spark-' + idx);
            if (!sparkEl) return;
            var sparkChart = ChartHelpers.createChart(sparkEl);
            var sparkData = coldUsers[idx].sparkline || [];
            sparkChart.setOption({
              grid: { left: 0, right: 0, top: 2, bottom: 2 },
              xAxis: { type: 'category', show: false, data: sparkData.map(function(_, i) { return i; }) },
              yAxis: { type: 'value', show: false },
              tooltip: { show: false },
              series: [{
                type: 'line',
                data: sparkData,
                smooth: true,
                symbol: 'none',
                lineStyle: { width: 1.5, color: sparkColor },
                areaStyle: { opacity: 0.1, color: sparkColor }
              }]
            });
            charts.push(sparkChart);
          }, 3 * idx);
        })(s);
      }

      // --- Engagement Trend chart ---
      setTimeout(function() {
        var trendEl = container.querySelector('#decay-trend-chart');
        if (!trendEl) return;
        var trendChart = ChartHelpers.createChart(trendEl);
        var trendData = data.engagement_trend || [];
        var dates = trendData.map(function(d) { return d.date; });
        var scores = trendData.map(function(d) { return d.score; });

        var trendOption = {
          tooltip: {
            trigger: 'axis',
            formatter: function(params) {
              var p = params[0];
              return '<strong>' + p.axisValue + '</strong><br/>Engagement Score: ' + (p.value != null ? p.value.toFixed(1) : '--');
            }
          },
          grid: { left: 48, right: 16, top: 16, bottom: trendData.length > 12 ? 48 : 24 },
          xAxis: {
            type: 'category',
            data: dates,
            axisLabel: {
              color: isDark() ? '#5c6370' : '#8c8c8c',
              fontSize: 11,
              fontFamily: 'JetBrains Mono, monospace'
            },
            axisLine: { lineStyle: { color: isDark() ? '#1e2430' : '#e0ded9' } },
            axisTick: { show: false }
          },
          yAxis: {
            type: 'value',
            name: 'Score',
            nameTextStyle: { color: isDark() ? '#5c6370' : '#8c8c8c', fontSize: 11 },
            axisLabel: {
              color: isDark() ? '#5c6370' : '#8c8c8c',
              fontSize: 11
            },
            splitLine: { lineStyle: { color: isDark() ? '#1e2430' : '#e0ded9', type: 'dashed' } }
          },
          series: [{
            type: 'line',
            data: scores,
            smooth: true,
            symbol: 'circle',
            symbolSize: 4,
            lineStyle: { width: 2 },
            areaStyle: {
              opacity: 0.15,
              color: {
                type: 'linear',
                x: 0, y: 0, x2: 0, y2: 1,
                colorStops: [
                  { offset: 0, color: isDark() ? '#60a5fa' : '#3b82f6' },
                  { offset: 1, color: 'transparent' }
                ]
              }
            },
            markArea: {
              silent: true,
              itemStyle: {
                color: isDark() ? 'rgba(248,113,113,0.08)' : 'rgba(248,113,113,0.06)'
              },
              data: [[
                { yAxis: 0 },
                { yAxis: 20 }
              ]]
            }
          }]
        };

        // Add dataZoom for 12+ points
        if (trendData.length > 12) {
          trendOption.dataZoom = [
            { type: 'inside' },
            { type: 'slider', height: 20, bottom: 0 }
          ];
        }

        trendChart.setOption(trendOption);
        charts.push(trendChart);
      }, 10);

      // --- Decay Distribution chart ---
      setTimeout(function() {
        var distEl = container.querySelector('#decay-dist-chart');
        if (!distEl) return;
        var distChart = ChartHelpers.createChart(distEl);
        var distData = data.decay_distribution || [];
        var buckets = distData.map(function(d) { return d.bucket; });
        var counts = distData.map(function(d) { return d.count; });

        // Color gradient by bucket position: green -> amber -> red
        var barColors = distData.map(function(d, i) {
          var ratio = distData.length > 1 ? i / (distData.length - 1) : 0;
          if (ratio <= 0.3) return isDark() ? '#4ade80' : '#22c55e';
          if (ratio <= 0.6) return isDark() ? '#fbbf24' : '#d97706';
          return isDark() ? '#f87171' : '#ef4444';
        });

        distChart.setOption({
          tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            formatter: function(params) {
              var p = params[0];
              return '<strong>' + p.axisValue + '</strong><br/>Users: ' + p.value;
            }
          },
          grid: { left: 48, right: 16, top: 16, bottom: 32 },
          xAxis: {
            type: 'category',
            data: buckets,
            axisLabel: {
              color: isDark() ? '#5c6370' : '#8c8c8c',
              fontSize: 11,
              fontFamily: 'JetBrains Mono, monospace',
              rotate: buckets.length > 6 ? 30 : 0
            },
            axisLine: { lineStyle: { color: isDark() ? '#1e2430' : '#e0ded9' } },
            axisTick: { show: false }
          },
          yAxis: {
            type: 'value',
            name: 'Users',
            nameTextStyle: { color: isDark() ? '#5c6370' : '#8c8c8c', fontSize: 11 },
            axisLabel: {
              color: isDark() ? '#5c6370' : '#8c8c8c',
              fontSize: 11
            },
            splitLine: { lineStyle: { color: isDark() ? '#1e2430' : '#e0ded9', type: 'dashed' } }
          },
          series: [{
            type: 'bar',
            data: counts.map(function(val, i) {
              return {
                value: val,
                itemStyle: { color: barColors[i], borderRadius: [3, 3, 0, 0] }
              };
            }),
            barMaxWidth: 40
          }]
        });
        charts.push(distChart);
      }, 20);

      return { charts: charts };
    },

    getHeadlineStats: function(data) {
      if (!data || !data.available) return [];
      var coldCount = data.cold_users_count || 0;
      var championRisk = 0;
      var coldUsers = data.cold_users || [];
      for (var i = 0; i < coldUsers.length; i++) {
        if (coldUsers[i].is_champion && coldUsers[i].status === 'cold') {
          championRisk++;
        }
      }
      return [
        { label: 'Cold Users', value: String(coldCount), color: coldCount > 0 ? 'var(--red)' : 'var(--green)' },
        { label: 'Champion Risk', value: String(championRisk), color: championRisk > 0 ? 'var(--red)' : 'var(--green)' }
      ];
    },

    getAttentionItems: function(data) {
      if (!data || !data.available) return [];
      var items = [];
      var coldCount = data.cold_users_count || 0;

      if (coldCount >= 5) {
        items.push({
          severity: 'high',
          text: coldCount + ' users showing engagement decay',
          action: { panel: 'decay' }
        });
      } else if (coldCount > 0) {
        items.push({
          severity: 'medium',
          text: coldCount + ' user(s) going cold',
          action: { panel: 'decay' }
        });
      }

      // Champion-specific alerts
      var coldUsers = data.cold_users || [];
      for (var i = 0; i < coldUsers.length; i++) {
        var user = coldUsers[i];
        if (user.is_champion && user.status === 'cold') {
          items.push({
            severity: 'high',
            text: (user.display_name || user.username || 'Unknown') + ' (champion) has gone cold',
            action: { panel: 'decay' }
          });
        }
      }

      return items;
    }
  });
})();
