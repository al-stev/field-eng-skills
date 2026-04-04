/**
 * Cohort Analysis Panel — Dashboard V2
 *
 * Three visualization sections:
 *   1. KPI stats strip (up to 4 cards)
 *   2. Retention Heatmap (cohort x period matrix with red-amber-green gradient)
 *   3. Retention Curve (line with area fill) + User Lifecycle (stacked area, conditional)
 *
 * Data source: INTELLIGENCE_DATA.analytics.cohort
 * Registers with PanelRegistry. No ES module syntax.
 */
(function() {
  'use strict';

  function isDark() {
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  }

  // --- CSS (auto-scoped by shell via #panel-cohort prefix) ---
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
.time-period {\
  font-family: "JetBrains Mono", monospace;\
  font-size: 11px;\
  font-weight: 400;\
  color: var(--text-tertiary);\
  margin-top: -8px;\
  margin-bottom: 12px;\
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
@media (max-width: 700px) {\
  .stats-strip {\
    grid-template-columns: repeat(2, 1fr);\
  }\
  .two-col {\
    grid-template-columns: 1fr;\
  }\
}\
';

  // --- Helpers ---

  function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function buildStatsStrip(kpis) {
    var html = '<div class="stats-strip">';
    for (var i = 0; i < kpis.length && i < 4; i++) {
      html += '<div class="stat-card">' +
        '<div class="stat-value" style="color:var(--text-primary)">' + escapeHtml(kpis[i].value) + '</div>' +
        '<div class="stat-label">' + escapeHtml(kpis[i].label) + '</div>' +
        '</div>';
    }
    html += '</div>';
    return html;
  }

  function renderEmptyState(container) {
    container.innerHTML = '<div class="placeholder-panel">' +
      '<div class="placeholder-icon">' +
      '<svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">' +
      '<rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>' +
      '<line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line>' +
      '<line x1="3" y1="10" x2="21" y2="10"></line></svg></div>' +
      '<div class="placeholder-title">Cohort Analysis</div>' +
      '<div class="placeholder-desc">No retention cohort data available. This requires at least 2 months of user activity data in BigQuery.</div>' +
      '</div>';
  }

  /**
   * Build heatmap data array from cohort_matrix.
   * Input: [{ cohort: "2025-06", size: 12, periods: [100, 75.5, null, ...] }, ...]
   * Output: [[cohortIdx, periodIdx, retentionPct], ...] for ECharts heatmap series
   */
  function buildHeatmapData(matrix) {
    var data = [];
    for (var ci = 0; ci < matrix.length; ci++) {
      var row = matrix[ci];
      var periods = row.periods || [];
      for (var pi = 0; pi < periods.length; pi++) {
        if (periods[pi] !== null && periods[pi] !== undefined) {
          data.push([pi, ci, Math.round(periods[pi] * 10) / 10]);
        }
      }
    }
    return data;
  }

  // --- Registration ---

  PanelRegistry.register({
    id: 'cohort',
    group: 'user-intel',
    label: 'Cohort Analysis',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>',
    dataKey: 'analytics.cohort',

    render: function(container, data, config) {
      var charts = [];

      // CSS injection guard
      if (!document.querySelector('style[data-panel="cohort"]')) {
        PanelRegistry.injectCSS('cohort', PANEL_CSS);
      }

      // Empty state
      if (!data || !data.available) {
        renderEmptyState(container);
        return { charts: [] };
      }

      var html = '';

      // --- KPI Stats Strip ---
      var kpis = data.kpis || [];
      html += buildStatsStrip(kpis);

      // --- Time Period ---
      if (data.period) {
        html += '<div class="time-period">' + escapeHtml(data.period.start || '') + ' to ' + escapeHtml(data.period.end || '') + '</div>';
      }

      // --- Normalize data shapes ---
      // Transform outputs cohort_matrix as {cohort_labels, cohort_sizes, period_labels, matrix}
      // where matrix entries are [cohortIdx, periodIdx, retentionPct].
      // Normalize to array of {cohort, size, periods: [...]} for rendering.
      var rawCM = data.cohort_matrix || {};
      var matrix = [];
      if (Array.isArray(rawCM)) {
        // Already in expected array format
        matrix = rawCM;
      } else if (rawCM.cohort_labels && rawCM.matrix) {
        var cmLabels = rawCM.cohort_labels || [];
        var cmSizes = rawCM.cohort_sizes || {};
        var cmPeriodLabels = rawCM.period_labels || [];
        var maxPeriodIdx = 0;
        for (var mi = 0; mi < rawCM.matrix.length; mi++) {
          if (rawCM.matrix[mi][1] > maxPeriodIdx) maxPeriodIdx = rawCM.matrix[mi][1];
        }
        // Build row-based structure
        for (var li = 0; li < cmLabels.length; li++) {
          var periods = [];
          for (var pi = 0; pi <= maxPeriodIdx; pi++) { periods.push(null); }
          matrix.push({
            cohort: cmLabels[li],
            size: cmSizes[cmLabels[li]] || cmSizes[li] || null,
            periods: periods
          });
        }
        // Fill in retention values
        for (var ei = 0; ei < rawCM.matrix.length; ei++) {
          var entry = rawCM.matrix[ei];
          var cIdx = entry[0], pIdx = entry[1], retPct = entry[2];
          if (matrix[cIdx]) {
            matrix[cIdx].periods[pIdx] = retPct;
          }
        }
      }

      // Normalize retention_curve: {periods, values} -> [{period, retention_pct}]
      var rawRC = data.retention_curve || [];
      var rc = [];
      if (Array.isArray(rawRC)) {
        rc = rawRC;
      } else if (rawRC.periods && rawRC.values) {
        for (var ri = 0; ri < rawRC.periods.length; ri++) {
          rc.push({ period: ri, period_label: rawRC.periods[ri], retention_pct: rawRC.values[ri] });
        }
      }

      // Normalize lifecycle: {months, new_users, retained, resurrected, churned} -> [{month, new, retained, resurrected, churned}]
      var rawLC = data.lifecycle;
      var lc = null;
      if (rawLC && Array.isArray(rawLC) && rawLC.length > 0) {
        lc = rawLC;
      } else if (rawLC && rawLC.months && rawLC.months.length > 0) {
        lc = [];
        for (var lci = 0; lci < rawLC.months.length; lci++) {
          lc.push({
            month: rawLC.months[lci],
            'new': rawLC.new_users ? rawLC.new_users[lci] : 0,
            new_users: rawLC.new_users ? rawLC.new_users[lci] : 0,
            retained: rawLC.retained ? rawLC.retained[lci] : 0,
            resurrected: rawLC.resurrected ? rawLC.resurrected[lci] : 0,
            churned: rawLC.churned ? rawLC.churned[lci] : 0
          });
        }
      }

      // --- RETENTION HEATMAP section ---
      html += '<div class="section-label">RETENTION HEATMAP</div>';
      html += '<div class="full-width"><div class="panel-card">';
      if (matrix.length > 0) {
        var heatmapHeight = Math.max(400, matrix.length * 32 + 120);
        html += '<div id="cohort-heatmap" style="width:100%;height:' + heatmapHeight + 'px;"></div>';
      } else {
        html += '<div style="text-align:center;padding:32px;color:var(--text-tertiary);font-size:14px;">No cohort matrix data available</div>';
      }
      html += '</div></div>';

      // --- Two-col: Retention Curve + User Lifecycle ---
      var hasLifecycle = lc && Array.isArray(lc) && lc.length > 0;

      if (rc.length > 0 || hasLifecycle) {
        html += '<div class="two-col">';

        // Left: Retention Curve
        html += '<div>';
        html += '<div class="section-label">RETENTION CURVE</div>';
        html += '<div class="panel-card">';
        if (rc.length > 0) {
          html += '<div id="cohort-curve" style="width:100%;height:320px;"></div>';
        } else {
          html += '<div style="text-align:center;padding:32px;color:var(--text-tertiary);font-size:14px;">No retention curve data</div>';
        }
        html += '</div></div>';

        // Right: User Lifecycle
        html += '<div>';
        html += '<div class="section-label">USER LIFECYCLE</div>';
        html += '<div class="panel-card">';
        if (hasLifecycle) {
          html += '<div id="cohort-lifecycle" style="width:100%;height:320px;"></div>';
        } else {
          html += '<div style="text-align:center;padding:32px;color:var(--text-tertiary);font-size:14px;">Lifecycle data not available for this account</div>';
        }
        html += '</div></div>';

        html += '</div>';
      }

      // Inject DOM
      container.innerHTML = html;

      // --- Render ECharts: Retention Heatmap ---
      if (matrix.length > 0) {
        var heatmapEl = container.querySelector('#cohort-heatmap');
        if (heatmapEl) {
          var heatmapChart = ChartHelpers.createChart(heatmapEl);

          // Build axis labels
          var cohortLabels = matrix.map(function(row) {
            return row.cohort + (row.size != null ? '  (n=' + row.size + ')' : '');
          });

          // Determine max period count
          var maxPeriods = 0;
          for (var mi = 0; mi < matrix.length; mi++) {
            var pLen = (matrix[mi].periods || []).length;
            if (pLen > maxPeriods) maxPeriods = pLen;
          }
          var periodLabels = [];
          for (var pi = 0; pi < maxPeriods; pi++) {
            periodLabels.push('M+' + pi);
          }

          var heatmapData = buildHeatmapData(matrix);

          heatmapChart.setOption({
            tooltip: {
              position: 'top',
              formatter: function(p) {
                var cohortName = cohortLabels[p.value[1]] || '';
                return 'Cohort: ' + cohortName + '<br/>Period: M+' + p.value[0] + '<br/>Retention: ' + p.value[2] + '%';
              }
            },
            grid: { left: 140, right: 60, top: 40, bottom: 60 },
            xAxis: {
              type: 'category',
              data: periodLabels,
              position: 'top',
              axisLabel: ChartHelpers.axisLabelConfig(),
              axisLine: { lineStyle: { color: ChartHelpers.getColor('border-subtle') || '#1e2430' } },
              axisTick: { show: false }
            },
            yAxis: {
              type: 'category',
              data: cohortLabels,
              axisLabel: ChartHelpers.axisLabelConfig(),
              axisLine: { lineStyle: { color: ChartHelpers.getColor('border-subtle') || '#1e2430' } },
              axisTick: { show: false }
            },
            visualMap: {
              type: 'continuous',
              min: 0,
              max: 100,
              calculable: true,
              orient: 'horizontal',
              left: 'center',
              bottom: 10,
              inRange: {
                color: ['#f87171', '#fbbf24', '#4ade80']
              },
              textStyle: {
                color: ChartHelpers.getColor('text-tertiary') || '#5c6370',
                fontSize: 11
              }
            },
            series: [{
              type: 'heatmap',
              data: heatmapData,
              label: {
                show: true,
                color: ChartHelpers.getColor('text-primary') || '#e8eaed',
                fontSize: 11,
                fontFamily: "'JetBrains Mono', monospace",
                formatter: function(p) {
                  return p.value[2] !== null ? Math.round(p.value[2]) + '%' : '';
                }
              },
              emphasis: {
                itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.5)' }
              }
            }]
          });
          charts.push(heatmapChart);
        }
      }

      // --- Render ECharts: Retention Curve ---
      if (rc.length > 0) {
        var curveEl = container.querySelector('#cohort-curve');
        if (curveEl) {
          var curveChart = ChartHelpers.createChart(curveEl);
          var curvePeriods = rc.map(function(r) { return r.period_label || (r.period != null ? 'M+' + r.period : ''); });
          var curveValues = rc.map(function(r) { return r.retention_pct; });
          var blueColor = ChartHelpers.getColor('blue') || '#60a5fa';

          var curveOpts = {
            tooltip: {
              trigger: 'axis',
              formatter: function(params) {
                var p = params[0];
                return p.name + ': ' + (p.value !== null ? p.value + '%' : 'N/A');
              }
            },
            grid: { left: 48, right: 16, top: 24, bottom: 32 },
            xAxis: {
              type: 'category',
              data: curvePeriods,
              axisLabel: ChartHelpers.axisLabelConfig(),
              axisLine: { lineStyle: { color: ChartHelpers.getColor('border-subtle') || '#1e2430' } },
              axisTick: { show: false }
            },
            yAxis: {
              type: 'value',
              min: 0,
              max: 100,
              name: 'Retention %',
              nameTextStyle: {
                color: ChartHelpers.getColor('text-tertiary') || '#5c6370',
                fontSize: 11
              },
              axisLabel: {
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 11,
                color: ChartHelpers.getColor('text-tertiary') || '#5c6370',
                formatter: '{value}%'
              },
              splitLine: ChartHelpers.gridLine()
            },
            series: [{
              type: 'line',
              data: curveValues,
              smooth: true,
              symbol: 'circle',
              symbolSize: 8,
              lineStyle: { color: blueColor, width: 2 },
              itemStyle: { color: blueColor },
              areaStyle: { color: blueColor + '22' }
            }]
          };

          // Add dataZoom for 12+ periods
          if (curvePeriods.length >= 12) {
            curveOpts.dataZoom = [
              { type: 'inside' },
              { type: 'slider', height: 20, bottom: 0 }
            ];
            curveOpts.grid.bottom = 52;
          }

          curveChart.setOption(curveOpts);
          charts.push(curveChart);
        }
      }

      // --- Render ECharts: User Lifecycle (stacked area) ---
      if (hasLifecycle) {
        var lcEl = container.querySelector('#cohort-lifecycle');
        if (lcEl) {
          var lcChart = ChartHelpers.createChart(lcEl);

          var lcMonths = lc.map(function(r) { return r.month; });
          var greenColor = ChartHelpers.getColor('green') || '#4ade80';
          var lcBlueColor = ChartHelpers.getColor('blue') || '#60a5fa';
          var amberColor = ChartHelpers.getColor('amber') || '#fbbf24';
          var redColor = ChartHelpers.getColor('red') || '#f87171';

          var lcSeries = [
            {
              name: 'New',
              type: 'line',
              stack: 'lifecycle',
              areaStyle: { color: lcBlueColor + '33' },
              lineStyle: { color: lcBlueColor, width: 2 },
              itemStyle: { color: lcBlueColor },
              symbol: 'none',
              data: lc.map(function(r) { return r['new'] || r.new_users || 0; }),
              emphasis: { focus: 'series' }
            },
            {
              name: 'Retained',
              type: 'line',
              stack: 'lifecycle',
              areaStyle: { color: greenColor + '33' },
              lineStyle: { color: greenColor, width: 2 },
              itemStyle: { color: greenColor },
              symbol: 'none',
              data: lc.map(function(r) { return r.retained || 0; }),
              emphasis: { focus: 'series' }
            },
            {
              name: 'Resurrected',
              type: 'line',
              stack: 'lifecycle',
              areaStyle: { color: amberColor + '33' },
              lineStyle: { color: amberColor, width: 2 },
              itemStyle: { color: amberColor },
              symbol: 'none',
              data: lc.map(function(r) { return r.resurrected || 0; }),
              emphasis: { focus: 'series' }
            },
            {
              name: 'Churned',
              type: 'line',
              stack: 'churned',
              areaStyle: { color: redColor + '33' },
              lineStyle: { color: redColor, width: 2 },
              itemStyle: { color: redColor },
              symbol: 'none',
              data: lc.map(function(r) { return -(r.churned || 0); }),
              emphasis: { focus: 'series' }
            }
          ];

          var lcOpts = {
            tooltip: {
              trigger: 'axis',
              formatter: function(params) {
                var html = '<strong>' + params[0].axisValue + '</strong>';
                params.forEach(function(p) {
                  var val = p.seriesName === 'Churned' ? Math.abs(p.value) : p.value;
                  html += '<br/>' + p.marker + ' ' + p.seriesName + ': ' + val + ' users';
                });
                return html;
              }
            },
            legend: {
              data: ['New', 'Retained', 'Resurrected', 'Churned'],
              bottom: 0,
              textStyle: {
                color: ChartHelpers.getColor('text-secondary') || '#8b92a0',
                fontSize: 11,
                fontFamily: "'JetBrains Mono', monospace"
              },
              itemWidth: 12,
              itemHeight: 12
            },
            grid: { left: 48, right: 16, top: 24, bottom: 40 },
            xAxis: {
              type: 'category',
              data: lcMonths,
              axisLabel: ChartHelpers.axisLabelConfig(),
              axisLine: { lineStyle: { color: ChartHelpers.getColor('border-subtle') || '#1e2430' } },
              axisTick: { show: false }
            },
            yAxis: {
              type: 'value',
              name: 'Users',
              nameTextStyle: {
                color: ChartHelpers.getColor('text-tertiary') || '#5c6370',
                fontSize: 11
              },
              axisLabel: {
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 11,
                color: ChartHelpers.getColor('text-tertiary') || '#5c6370'
              },
              splitLine: ChartHelpers.gridLine()
            },
            series: lcSeries
          };

          // Add dataZoom for 12+ months
          if (lcMonths.length >= 12) {
            lcOpts.dataZoom = [
              { type: 'inside', start: 0, end: 100 },
              {
                type: 'slider', start: 0, end: 100,
                bottom: 24, height: 16,
                textStyle: { color: ChartHelpers.getColor('text-tertiary') || '#5c6370', fontSize: 10 },
                borderColor: ChartHelpers.getColor('border-subtle') || '#1e2430',
                fillerColor: (ChartHelpers.getColor('accent') || '#d4a853') + '22',
                handleStyle: { color: ChartHelpers.getColor('accent') || '#d4a853' }
              }
            ];
            lcOpts.grid.bottom = 60;
            lcOpts.legend.bottom = 44;
          }

          lcChart.setOption(lcOpts);
          charts.push(lcChart);
        }
      }

      return { charts: charts };
    },

    getHeadlineStats: function(data) {
      if (!data || !data.available) return [];

      var stats = [];

      // Normalize retention_curve for headline stats
      var rawRC = data.retention_curve || [];
      var rc = [];
      if (Array.isArray(rawRC)) {
        rc = rawRC;
      } else if (rawRC.periods && rawRC.values) {
        for (var i = 0; i < rawRC.values.length; i++) {
          rc.push({ retention_pct: rawRC.values[i] });
        }
      }

      // First retention point (M+1 or first period)
      if (rc.length >= 1) {
        var m1 = rc[0];
        var pct = m1 ? m1.retention_pct : null;
        if (pct !== null && pct !== undefined) {
          var retColor = pct >= 70 ? 'var(--green)' : pct >= 40 ? 'var(--amber)' : 'var(--red)';
          stats.push({
            label: 'M+1 Retention',
            value: Math.round(pct) + '%',
            color: retColor
          });
        }
      }

      // Cohort count
      var rawCM = data.cohort_matrix || [];
      var cohortCount = 0;
      if (Array.isArray(rawCM)) {
        cohortCount = rawCM.length;
      } else if (rawCM.cohort_labels) {
        cohortCount = rawCM.cohort_labels.length;
      }
      if (cohortCount > 0) {
        stats.push({
          label: 'Cohorts',
          value: String(cohortCount),
          color: 'var(--text-primary)'
        });
      }

      return stats;
    },

    getAttentionItems: function(data) {
      if (!data || !data.available) return [];

      var items = [];

      // Normalize retention_curve
      var rawRC = data.retention_curve || [];
      var rc = [];
      if (Array.isArray(rawRC)) {
        rc = rawRC;
      } else if (rawRC.periods && rawRC.values) {
        for (var i = 0; i < rawRC.values.length; i++) {
          rc.push({ retention_pct: rawRC.values[i] });
        }
      }

      // Check first retention point
      if (rc.length >= 1) {
        var m1 = rc[0];
        var pct = m1 ? m1.retention_pct : null;
        if (pct !== null && pct < 40) {
          items.push({
            severity: 'high',
            text: 'Low first-month retention (' + Math.round(pct) + '%)',
            action: { panel: 'cohort' }
          });
        }
      }

      return items;
    }
  });
})();
