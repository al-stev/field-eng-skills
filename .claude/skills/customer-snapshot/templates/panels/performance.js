/**
 * Performance Panel -- Dashboard V2
 *
 * Performance index gauge, latency breakdown bar chart, error metrics,
 * and slow chart users table. Handles descoped/schema_error/unavailable
 * empty states gracefully (performance data is LOW confidence).
 *
 * Data source: INTELLIGENCE_DATA.analytics.performance
 * Transform: PerformanceTransform
 *
 * Registers with PanelRegistry. No ES module syntax.
 */
(function() {
  'use strict';

  // --- Helpers ---
  function isDark() {
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  }

  function tierColor(tier) {
    if (tier === 'good') return 'var(--green)';
    if (tier === 'fair') return 'var(--amber)';
    return 'var(--red)';
  }

  // --- CSS (auto-scoped by shell via #panel-performance prefix) ---
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
.comp-bar-row {\
  display: flex;\
  align-items: center;\
  gap: 12px;\
  margin-bottom: 10px;\
}\
.comp-bar-label {\
  font-family: "Outfit", system-ui, sans-serif;\
  font-size: 14px;\
  font-weight: 500;\
  color: var(--text-secondary);\
  min-width: 120px;\
  flex-shrink: 0;\
}\
.comp-bar-track {\
  flex: 1;\
  height: 8px;\
  background: var(--bg-surface);\
  border-radius: 4px;\
  overflow: hidden;\
}\
.comp-bar-fill {\
  height: 100%;\
  border-radius: 4px;\
  transition: width 0.3s ease;\
}\
.comp-bar-value {\
  font-family: "JetBrains Mono", monospace;\
  font-size: 11px;\
  font-weight: 600;\
  color: var(--text-tertiary);\
  min-width: 32px;\
  text-align: right;\
}\
.error-stat {\
  text-align: center;\
}\
.error-stat-value {\
  font-family: "Outfit", system-ui, sans-serif;\
  font-size: 28px;\
  font-weight: 600;\
  line-height: 1.1;\
}\
.error-stat-label {\
  font-family: "JetBrains Mono", monospace;\
  font-size: 11px;\
  font-weight: 600;\
  text-transform: uppercase;\
  letter-spacing: 1.5px;\
  color: var(--text-tertiary);\
  margin-top: 6px;\
}\
.latency-stats-row {\
  display: flex;\
  gap: 24px;\
  margin-bottom: 16px;\
}\
.latency-stat {\
  display: flex;\
  align-items: baseline;\
  gap: 6px;\
}\
.latency-stat-label {\
  font-family: "JetBrains Mono", monospace;\
  font-size: 11px;\
  font-weight: 600;\
  text-transform: uppercase;\
  letter-spacing: 1.5px;\
  color: var(--text-tertiary);\
}\
.latency-stat-value {\
  font-family: "JetBrains Mono", monospace;\
  font-size: 11px;\
  font-weight: 600;\
  color: var(--text-primary);\
}\
.slow-table {\
  width: 100%;\
  border-collapse: collapse;\
}\
.slow-table th {\
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
.slow-table td {\
  font-family: "Outfit", system-ui, sans-serif;\
  font-size: 14px;\
  font-weight: 400;\
  padding: 10px 12px;\
  border-bottom: 1px solid var(--border-subtle);\
  vertical-align: middle;\
}\
.slow-table tr:hover {\
  background: var(--bg-hover);\
  transition: background 0.15s;\
}\
.slow-table tr:last-child td {\
  border-bottom: none;\
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

  var _cssInjected = false;

  // --- REGISTRATION ---
  PanelRegistry.register({
    id: 'performance',
    group: 'product-intelligence',
    label: 'Performance',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>',
    dataKey: 'analytics.performance',

    render: function(container, data, config) {
      var charts = [];

      // Inject CSS once
      if (!_cssInjected && typeof PanelRegistry.injectCSS === 'function') {
        PanelRegistry.injectCSS('performance', PANEL_CSS);
        _cssInjected = true;
      }

      // Empty state -- multiple variants based on reason
      if (!data || !data.available) {
        var emptyTitle = 'No Performance Data';
        var emptyDesc = 'No performance data available. Application performance metrics may not be available for all deployment types.';

        if (data && data.reason === 'performance_descoped') {
          emptyTitle = 'Performance Data Descoped';
          emptyDesc = 'No performance data available. Application performance metrics may not be available for all deployment types.';
        } else if (data && data.reason === 'schema_error') {
          emptyTitle = 'Performance Schema Error';
          emptyDesc = 'Performance data schema error. The required BigQuery tables may not exist or have changed structure.';
        }

        container.innerHTML =
          '<div class="placeholder-panel">' +
            '<div class="placeholder-icon">' +
              '<svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="var(--text-tertiary)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">' +
                '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>' +
              '</svg>' +
            '</div>' +
            '<div class="placeholder-title">' + emptyTitle + '</div>' +
            '<div class="placeholder-desc">' + emptyDesc + '</div>' +
          '</div>';
        return { charts: charts };
      }

      var perfIndex = data.performance_index || {};
      var slowness = data.slowness_breakdown || [];
      var errors = data.error_metrics || {};
      var latency = data.latency_distribution || {};
      var slowUsers = data.slow_chart_users || [];
      var tier = perfIndex.tier || 'poor';

      // --- KPI stats strip ---
      var kpis = data.kpis || [];
      var statsHtml = '<div class="stats-strip">';
      for (var k = 0; k < kpis.length && k < 4; k++) {
        var statColor = 'var(--text-primary)';
        if (k === 0) {
          statColor = tierColor(tier);
        }
        statsHtml += '<div class="stat-card">' +
          '<div class="stat-value" style="color:' + statColor + '">' + (kpis[k].value || '--') + '</div>' +
          '<div class="stat-label">' + (kpis[k].label || '') + '</div>' +
        '</div>';
      }
      statsHtml += '</div>';

      // --- Build container HTML ---
      container.innerHTML = statsHtml +
        '<div class="section-label">PERFORMANCE INDEX</div>' +
        '<div class="two-col">' +
          '<div class="panel-card">' +
            '<div id="perf-gauge" style="width:100%;height:200px;"></div>' +
          '</div>' +
          '<div class="panel-card" id="perf-components"></div>' +
        '</div>' +
        '<div class="section-label">LATENCY BREAKDOWN</div>' +
        '<div class="full-width panel-card">' +
          '<div id="perf-latency-stats"></div>' +
          '<div id="perf-latency-bar" style="width:100%;height:320px;"></div>' +
        '</div>' +
        '<div class="two-col">' +
          '<div class="panel-card" id="perf-errors"></div>' +
          '<div class="panel-card" id="perf-slow-users"></div>' +
        '</div>';

      // =========================================================
      // CHART 1: Performance Index Gauge
      // =========================================================
      var gaugeEl = container.querySelector('#perf-gauge');
      if (gaugeEl) {
        var gaugeChart = ChartHelpers.createChart(gaugeEl);
        charts.push(gaugeChart);

        gaugeChart.setOption({
          series: [{
            type: 'gauge',
            min: 0,
            max: 100,
            startAngle: 200,
            endAngle: -20,
            axisLine: {
              lineStyle: {
                width: 20,
                color: [
                  [0.5, '#f87171'],
                  [0.8, '#fbbf24'],
                  [1, '#4ade80']
                ]
              }
            },
            pointer: { length: '60%', width: 4, itemStyle: { color: 'auto' } },
            axisTick: { show: false },
            splitLine: { show: false },
            axisLabel: { show: false },
            detail: {
              valueAnimation: true,
              fontSize: 36,
              fontFamily: "'Instrument Serif', Georgia, serif",
              color: ChartHelpers.getColor('text-primary'),
              offsetCenter: [0, '60%'],
              formatter: '{value}'
            },
            title: {
              offsetCenter: [0, '82%'],
              fontSize: 14,
              fontFamily: "'Outfit', sans-serif",
              color: tierColor(tier)
            },
            data: [{ value: Math.round(perfIndex.score || 0), name: tier.toUpperCase() }]
          }]
        });
      }

      // =========================================================
      // SECTION: Component Breakdown
      // =========================================================
      var compEl = container.querySelector('#perf-components');
      if (compEl) {
        var components = perfIndex.components || {};
        var compKeys = Object.keys(components);

        var compHtml = '<div class="section-label">COMPONENT BREAKDOWN</div>';
        if (compKeys.length === 0) {
          compHtml += '<div style="font-family:Outfit,system-ui,sans-serif;font-size:14px;color:var(--text-tertiary);">No component data available.</div>';
        } else {
          for (var ci = 0; ci < compKeys.length; ci++) {
            var compName = compKeys[ci];
            var compScore = components[compName];
            var barColor = compScore >= 80 ? '#4ade80' : compScore >= 50 ? '#fbbf24' : '#f87171';
            var displayName = compName.replace(/_/g, ' ').replace(/\b\w/g, function(c) { return c.toUpperCase(); });

            compHtml += '<div class="comp-bar-row">' +
              '<span class="comp-bar-label">' + displayName + '</span>' +
              '<div class="comp-bar-track">' +
                '<div class="comp-bar-fill" style="width:' + Math.min(compScore, 100) + '%;background:' + barColor + ';"></div>' +
              '</div>' +
              '<span class="comp-bar-value">' + Math.round(compScore) + '</span>' +
            '</div>';
          }
        }
        compEl.innerHTML = compHtml;
      }

      // =========================================================
      // SECTION: Latency Stats + CHART 2: Latency Breakdown Bar
      // =========================================================
      var latStatsEl = container.querySelector('#perf-latency-stats');
      if (latStatsEl && latency) {
        var p50 = latency.p50 != null ? latency.p50 : '--';
        var p95 = latency.p95 != null ? latency.p95 : '--';
        var p99 = latency.p99 != null ? latency.p99 : '--';
        var p50Display = typeof p50 === 'number' ? Math.round(p50) + 'ms' : p50;
        var p95Display = typeof p95 === 'number' ? Math.round(p95) + 'ms' : p95;
        var p99Display = typeof p99 === 'number' ? Math.round(p99) + 'ms' : p99;

        latStatsEl.innerHTML =
          '<div class="latency-stats-row">' +
            '<div class="latency-stat"><span class="latency-stat-label">P50</span><span class="latency-stat-value">' + p50Display + '</span></div>' +
            '<div class="latency-stat"><span class="latency-stat-label">P95</span><span class="latency-stat-value">' + p95Display + '</span></div>' +
            '<div class="latency-stat"><span class="latency-stat-label">P99</span><span class="latency-stat-value">' + p99Display + '</span></div>' +
          '</div>';
      }

      var barEl = container.querySelector('#perf-latency-bar');
      if (barEl && slowness.length > 0) {
        var barChart = ChartHelpers.createChart(barEl);
        charts.push(barChart);

        // Sort descending by count for display
        var sorted = slowness.slice().sort(function(a, b) { return b.count - a.count; });
        var featureNames = [];
        var counts = [];
        var maxCount = 0;
        for (var si = 0; si < sorted.length; si++) {
          featureNames.push(sorted[si].label || sorted[si].feature);
          counts.push(sorted[si].count);
          if (sorted[si].count > maxCount) maxCount = sorted[si].count;
        }

        // Reverse for horizontal bar (bottom to top)
        featureNames.reverse();
        counts.reverse();

        barChart.setOption({
          tooltip: Object.assign({}, ChartHelpers.tooltipConfig(), {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            formatter: function(params) {
              var d = params[0];
              var idx = sorted.length - 1 - d.dataIndex;
              var item = sorted[idx];
              if (!item) return d.name + ': ' + d.value;
              return '<div style="font-weight:600;margin-bottom:4px">' + (item.label || item.feature) + '</div>' +
                '<div>' + item.count + ' slow loads (' + item.pct + '% of total)</div>';
            }
          }),
          grid: { left: '30%', right: '10%', top: 20, bottom: 20 },
          xAxis: {
            type: 'value',
            axisLabel: ChartHelpers.axisLabelConfig(),
            splitLine: ChartHelpers.gridLine(),
            axisLine: { show: false },
            axisTick: { show: false }
          },
          yAxis: {
            type: 'category',
            data: featureNames,
            axisLabel: {
              fontFamily: "'Outfit', system-ui, sans-serif",
              fontSize: 12,
              color: ChartHelpers.getColor('text-secondary')
            },
            axisLine: { lineStyle: { color: ChartHelpers.getColor('border-subtle') } },
            axisTick: { show: false }
          },
          series: [{
            type: 'bar',
            data: counts.map(function(c) {
              var pct = maxCount > 0 ? c / maxCount : 0;
              var barCol = pct >= 0.7 ? '#f87171' : pct >= 0.4 ? '#fbbf24' : '#4ade80';
              return { value: c, itemStyle: { color: barCol } };
            }),
            barMaxWidth: 30,
            itemStyle: { borderRadius: [0, 3, 3, 0] }
          }]
        });
      } else if (barEl) {
        barEl.style.height = '60px';
        barEl.innerHTML = '<div style="font-family:Outfit,system-ui,sans-serif;font-size:14px;color:var(--text-tertiary);padding:16px 0;">No latency breakdown data available.</div>';
      }

      // =========================================================
      // SECTION: Error Metrics
      // =========================================================
      var errEl = container.querySelector('#perf-errors');
      if (errEl) {
        var errCount = errors.error_count_30d || 0;
        var errUsers = errors.users_facing_errors || 0;
        var errRate = errors.error_rate != null ? (errors.error_rate * 100).toFixed(1) + '%' : '--';

        var errCountColor = errCount > 50 ? 'var(--red)' : errCount > 10 ? 'var(--amber)' : 'var(--green)';

        errEl.innerHTML =
          '<div class="section-label">ERROR METRICS</div>' +
          '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;">' +
            '<div class="error-stat">' +
              '<div class="error-stat-value" style="color:' + errCountColor + '">' + errCount + '</div>' +
              '<div class="error-stat-label">Errors (30d)</div>' +
            '</div>' +
            '<div class="error-stat">' +
              '<div class="error-stat-value" style="color:var(--text-primary)">' + errUsers + '</div>' +
              '<div class="error-stat-label">Users Affected</div>' +
            '</div>' +
            '<div class="error-stat">' +
              '<div class="error-stat-value" style="color:var(--text-primary)">' + errRate + '</div>' +
              '<div class="error-stat-label">Error Rate</div>' +
            '</div>' +
          '</div>';
      }

      // =========================================================
      // SECTION: Slow Chart Users
      // =========================================================
      var slowEl = container.querySelector('#perf-slow-users');
      if (slowEl) {
        var slowHtml = '<div class="section-label">SLOW CHART USERS</div>';

        if (slowUsers.length === 0) {
          slowHtml += '<div style="font-family:Outfit,system-ui,sans-serif;font-size:14px;color:var(--text-tertiary);padding:16px 0;">No slow chart load users detected.</div>';
        } else {
          slowHtml += '<table class="slow-table"><thead><tr>' +
            '<th>User</th>' +
            '<th style="text-align:right">Slow Loads</th>' +
          '</tr></thead><tbody>';

          var maxSlowUsers = Math.min(slowUsers.length, 10);
          for (var ui = 0; ui < maxSlowUsers; ui++) {
            var u = slowUsers[ui];
            slowHtml += '<tr>' +
              '<td>' + (u.username || u.display_name || 'unknown') + '</td>' +
              '<td style="text-align:right;font-family:JetBrains Mono,monospace;font-size:11px;">' + u.slow_loads + '</td>' +
            '</tr>';
          }

          slowHtml += '</tbody></table>';
          if (slowUsers.length > 10) {
            slowHtml += '<div style="font-family:JetBrains Mono,monospace;font-size:11px;color:var(--text-tertiary);margin-top:8px;">+ ' + (slowUsers.length - 10) + ' more users</div>';
          }
        }

        slowEl.innerHTML = slowHtml;
      }

      return { charts: charts };
    },

    getHeadlineStats: function(data) {
      if (!data || !data.available) return [];
      var perfIndex = data.performance_index || {};
      var kpis = data.kpis || [];
      var stats = [];

      if (kpis.length > 0) {
        stats.push({
          label: 'Perf Index',
          value: kpis[0].value,
          color: tierColor(perfIndex.tier || 'poor')
        });
      }
      if (kpis.length > 1) {
        var errVal = kpis[1].value;
        stats.push({
          label: 'Errors (30d)',
          value: errVal,
          color: parseInt(errVal) > 10 ? 'var(--red)' : 'var(--green)'
        });
      }
      return stats;
    },

    getAttentionItems: function(data) {
      if (!data || !data.available) return [];
      var items = [];
      var perfIndex = data.performance_index || {};

      if (perfIndex.tier === 'poor') {
        items.push({
          severity: 'high',
          text: 'Poor application performance (score: ' + (perfIndex.score || 0) + ')',
          action: { panel: 'performance' }
        });
      }

      var errors = data.error_metrics || {};
      if (errors.error_count_30d > 50) {
        items.push({
          severity: 'medium',
          text: errors.error_count_30d + ' errors in last 30 days',
          action: { panel: 'performance' }
        });
      }

      return items;
    }
  });
})();
