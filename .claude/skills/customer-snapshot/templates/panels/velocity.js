/**
 * Feature Velocity Panel — Dashboard V2
 *
 * Three visualization sections:
 *   1. Velocity Grid — sparkline cards per product area with momentum badges
 *   2. Momentum Indicators — acceleration/deceleration summary bar
 *   3. Trend Detail — multi-series line chart for top product areas
 *
 * Data shape: analytics.velocity from FeatureVelocityTransform
 *   { available, areas[], months[], kpis[], narrative }
 *
 * Registers with PanelRegistry. No ES module syntax.
 */
(function() {
  'use strict';

  // --- CSS (auto-scoped by shell via #panel-velocity prefix) ---
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
.time-period {\
  font-family: "JetBrains Mono", monospace;\
  font-size: 11px;\
  font-weight: 400;\
  color: var(--text-tertiary);\
  margin-top: -8px;\
  margin-bottom: 12px;\
}\
.velocity-grid {\
  display: grid;\
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));\
  gap: 16px;\
  margin-bottom: 32px;\
}\
.velocity-card {\
  background: var(--bg-elevated);\
  border: 1px solid var(--border-subtle);\
  border-radius: 6px;\
  padding: 16px;\
}\
.velocity-card-header {\
  display: flex;\
  justify-content: space-between;\
  align-items: center;\
  margin-bottom: 8px;\
}\
.velocity-card-name {\
  font-family: "Outfit", system-ui, sans-serif;\
  font-size: 14px;\
  font-weight: 600;\
  color: var(--text-primary);\
}\
.velocity-card-meta {\
  font-family: "JetBrains Mono", monospace;\
  font-size: 11px;\
  color: var(--text-tertiary);\
}\
.momentum-badge {\
  display: inline-block;\
  padding: 2px 8px;\
  border-radius: 4px;\
  font-family: "JetBrains Mono", monospace;\
  font-size: 11px;\
  font-weight: 600;\
  text-transform: uppercase;\
  letter-spacing: 1px;\
}\
.momentum-accelerating {\
  background: var(--green-dim);\
  color: var(--green);\
  border: 1px solid var(--green-border);\
}\
.momentum-stable {\
  background: var(--blue-dim);\
  color: var(--blue);\
  border: 1px solid var(--blue-border);\
}\
.momentum-decelerating {\
  background: var(--red-dim);\
  color: var(--red);\
  border: 1px solid var(--red-border);\
}\
.momentum-summary {\
  display: flex;\
  gap: 24px;\
  align-items: center;\
  margin-bottom: 16px;\
}\
.momentum-count {\
  font-family: "Outfit", system-ui, sans-serif;\
  font-size: 14px;\
  font-weight: 600;\
}\
.momentum-bar-wrap {\
  height: 24px;\
  border-radius: 4px;\
  overflow: hidden;\
  display: flex;\
  width: 100%;\
}\
.momentum-bar-seg {\
  display: flex;\
  align-items: center;\
  justify-content: center;\
  font-family: "JetBrains Mono", monospace;\
  font-size: 11px;\
  font-weight: 600;\
  color: #fff;\
  transition: width 0.3s;\
}\
@media (max-width: 700px) {\
  .stats-strip {\
    grid-template-columns: repeat(2, 1fr);\
  }\
  .two-col {\
    grid-template-columns: 1fr;\
  }\
  .velocity-grid {\
    grid-template-columns: 1fr;\
  }\
}\
';

  // --- HELPERS ---

  function isDark() {
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  }

  /**
   * Map transform momentum values to display labels and CSS classes.
   * Transform uses: "up", "flat", "down"
   */
  function momentumLabel(momentum) {
    if (momentum === 'up') return 'Accelerating';
    if (momentum === 'down') return 'Decelerating';
    return 'Stable';
  }

  function momentumClass(momentum) {
    if (momentum === 'up') return 'momentum-accelerating';
    if (momentum === 'down') return 'momentum-decelerating';
    return 'momentum-stable';
  }

  function momentumColor(momentum) {
    if (momentum === 'up') return 'var(--green)';
    if (momentum === 'down') return 'var(--red)';
    return 'var(--blue)';
  }

  /**
   * Format large numbers compactly.
   */
  function fmtNum(n) {
    if (n == null) return '0';
    if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
    if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
    return String(n);
  }

  // --- SQL COPY BUTTON ---

  var SQL_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"></ellipse><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path></svg>';

  function sqlCopyBtn(queryKey) {
    return '<span class="sql-copy-btn" data-query-key="' + queryKey + '" title="Copy SQL query to clipboard" aria-label="Copy SQL query">' + SQL_ICON + '</span>';
  }

  // --- REGISTRATION ---
  PanelRegistry.register({
    id: 'velocity',
    group: 'product-intel',
    label: 'Feature Velocity',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>',
    dataKey: 'analytics.velocity',

    render: function(container, data, config) {
      var charts = [];
      var cssInjected = document.querySelector('style[data-panel="velocity"]');

      // Inject CSS once
      if (!cssInjected && typeof PanelRegistry.injectCSS === 'function') {
        PanelRegistry.injectCSS('velocity', PANEL_CSS);
      }

      // Empty state
      if (!data || !data.available) {
        container.innerHTML = '<div class="placeholder-panel">' +
          '<div class="placeholder-icon">' +
          '<svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="var(--text-tertiary)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">' +
          '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg></div>' +
          '<div class="placeholder-title">Feature Velocity</div>' +
          '<div class="placeholder-desc">No product area velocity data available. Ensure the customer has usage event data in BigQuery.</div>' +
          '</div>';
        return { charts: [] };
      }

      var areas = data.areas || [];
      var months = data.months || [];
      var kpis = data.kpis || [];

      // Sort areas by total_events descending (transform already does this, but ensure)
      areas.sort(function(a, b) { return (b.total_events || 0) - (a.total_events || 0); });

      // --- KPI Stats Strip ---
      var kpiHtml = '<div class="stats-strip">';
      kpis.forEach(function(kpi) {
        kpiHtml += '<div class="stat-card">' +
          '<div class="stat-value" style="color:var(--text-primary)">' + kpi.value + '</div>' +
          '<div class="stat-label">' + kpi.label + '</div>' +
          '</div>';
      });
      kpiHtml += '</div>';

      // --- Period indicator ---
      var periodHtml = '';
      if (data.period && data.period.start) {
        periodHtml = '<div class="time-period">' + data.period.start + ' to ' + data.period.end + '</div>';
      }

      // --- Build Velocity Grid section ---
      var gridHtml = '<div class="full-width">' +
        '<div class="section-label">VELOCITY GRID</div>' +
        '<div class="velocity-grid">';

      areas.forEach(function(area, idx) {
        var mClass = momentumClass(area.momentum);
        var mLabel = momentumLabel(area.momentum);
        var pctStr = area.momentum_pct != null
          ? (area.momentum_pct > 0 ? '+' : '') + area.momentum_pct + '%'
          : '';

        gridHtml += '<div class="velocity-card">' +
          '<div class="velocity-card-header">' +
          '<span class="velocity-card-name">' + area.area + '</span>' +
          '<span class="momentum-badge ' + mClass + '">' + mLabel + '</span>' +
          '</div>' +
          '<div class="velocity-card-meta">' +
          fmtNum(area.total_events) + ' events &middot; ' +
          (area.avg_recent_users || 0) + ' users/mo' +
          (pctStr ? ' &middot; ' + pctStr + ' vs prior 3mo' : '') +
          '</div>' +
          '<div id="velocity-spark-' + idx + '" style="width:100%;height:40px;margin-top:8px;"></div>' +
          '</div>';
      });

      gridHtml += '</div></div>';

      // --- Momentum Indicators section ---
      var accelCount = 0;
      var stableCount = 0;
      var decelCount = 0;
      areas.forEach(function(a) {
        if (a.momentum === 'up') accelCount++;
        else if (a.momentum === 'down') decelCount++;
        else stableCount++;
      });
      var total = areas.length || 1;

      var momentumHtml = '<div class="full-width">' +
        '<div class="section-label">MOMENTUM INDICATORS</div>' +
        '<div class="panel-card">' +
        '<div class="momentum-summary">' +
        '<span class="momentum-count" style="color:var(--green);">' + accelCount + ' Accelerating</span>' +
        '<span class="momentum-count" style="color:var(--blue);">' + stableCount + ' Stable</span>' +
        '<span class="momentum-count" style="color:var(--red);">' + decelCount + ' Decelerating</span>' +
        '</div>' +
        '<div class="momentum-bar-wrap">';

      if (accelCount > 0) {
        momentumHtml += '<div class="momentum-bar-seg" style="width:' +
          Math.round(accelCount / total * 100) + '%;background:var(--green);">' +
          accelCount + '</div>';
      }
      if (stableCount > 0) {
        momentumHtml += '<div class="momentum-bar-seg" style="width:' +
          Math.round(stableCount / total * 100) + '%;background:var(--blue);">' +
          stableCount + '</div>';
      }
      if (decelCount > 0) {
        momentumHtml += '<div class="momentum-bar-seg" style="width:' +
          Math.round(decelCount / total * 100) + '%;background:var(--red);">' +
          decelCount + '</div>';
      }

      momentumHtml += '</div></div></div>';

      // --- Trend Detail section ---
      var trendHtml = '<div class="full-width">' +
        '<div class="section-label">TREND DETAIL</div>' +
        '<div class="panel-card">' +
        '<div id="velocity-trend-chart" style="width:100%;height:320px;"></div>' +
        '</div></div>';

      // Assemble full HTML
      container.innerHTML = kpiHtml + periodHtml + gridHtml + momentumHtml + trendHtml;

      // --- Render sparkline charts ---
      areas.forEach(function(area, idx) {
        var sparkEl = container.querySelector('#velocity-spark-' + idx);
        if (!sparkEl) return;

        var sparkChart = ChartHelpers.createChart(sparkEl);
        var lineColor = momentumColor(area.momentum);

        sparkChart.setOption({
          grid: { left: 0, right: 0, top: 2, bottom: 2 },
          xAxis: {
            type: 'category',
            data: area.months || months,
            show: false
          },
          yAxis: {
            type: 'value',
            show: false
          },
          tooltip: {
            trigger: 'axis',
            formatter: function(params) {
              var i = params[0].dataIndex;
              var m = (area.months || months)[i] || '';
              var ev = (area.events || [])[i] || 0;
              var us = (area.users || [])[i] || 0;
              return m + '<br/>Events: ' + ev.toLocaleString() + '<br/>Users: ' + us;
            }
          },
          series: [{
            type: 'line',
            data: area.events || [],
            smooth: true,
            symbol: 'none',
            lineStyle: { width: 1.5, color: lineColor },
            areaStyle: { opacity: 0.1, color: lineColor },
            itemStyle: { color: lineColor }
          }]
        });
        charts.push(sparkChart);
      });

      // --- Render trend detail chart (top 8 areas) ---
      var trendEl = container.querySelector('#velocity-trend-chart');
      if (trendEl && areas.length > 0) {
        var trendChart = ChartHelpers.createChart(trendEl);
        var topAreas = areas.slice(0, 8);

        // ECharts theme palette colors
        var palette = [
          'var(--accent)', 'var(--blue)', 'var(--green)', 'var(--amber)',
          'var(--red)', 'var(--orange)', '#9333ea', '#06b6d4'
        ];
        // Resolve CSS vars for ECharts (which needs actual color values)
        var rootStyle = getComputedStyle(document.documentElement);
        var resolvedPalette = palette.map(function(c) {
          if (c.indexOf('var(') === 0) {
            var varName = c.replace('var(', '').replace(')', '');
            return rootStyle.getPropertyValue(varName).trim() || c;
          }
          return c;
        });

        var series = topAreas.map(function(area, i) {
          return {
            name: area.area,
            type: 'line',
            data: area.events || [],
            smooth: true,
            symbol: 'circle',
            symbolSize: 4,
            lineStyle: { width: 2 },
            areaStyle: { opacity: 0.05 },
            itemStyle: { color: resolvedPalette[i] || resolvedPalette[0] }
          };
        });

        var trendOption = {
          tooltip: {
            trigger: 'axis',
            formatter: function(params) {
              var html = '<strong>' + params[0].axisValue + '</strong>';
              params.forEach(function(p) {
                if (p.value > 0) {
                  html += '<br/>' + p.marker + ' ' + p.seriesName + ': ' + p.value.toLocaleString();
                }
              });
              return html;
            }
          },
          legend: {
            data: topAreas.map(function(a) { return a.area; }),
            top: 0,
            textStyle: {
              fontSize: 11,
              fontFamily: 'JetBrains Mono, monospace'
            }
          },
          grid: { left: 48, right: 16, top: 40, bottom: 48 },
          xAxis: {
            type: 'category',
            data: months,
            axisLabel: {
              fontSize: 11,
              interval: months.length > 12 ? 1 : 0
            },
            axisLine: { lineStyle: { color: isDark() ? '#2a3040' : '#d4d2ce' } },
            axisTick: { show: false }
          },
          yAxis: {
            type: 'value',
            name: 'Events',
            nameTextStyle: { fontSize: 11 },
            axisLabel: {
              fontSize: 11,
              formatter: function(v) { return fmtNum(v); }
            },
            splitLine: { lineStyle: { type: 'dashed' } }
          },
          series: series
        };

        // Add dataZoom for 12+ months
        if (months.length >= 12) {
          trendOption.dataZoom = [
            { type: 'inside' },
            { type: 'slider', height: 20, bottom: 0 }
          ];
        }

        trendChart.setOption(trendOption);
        charts.push(trendChart);
      }

      return { charts: charts };
    },

    getHeadlineStats: function(data) {
      if (!data || !data.available) return [];

      var areas = data.areas || [];
      var accelCount = 0;
      var decelCount = 0;
      areas.forEach(function(a) {
        if (a.momentum === 'up') accelCount++;
        else if (a.momentum === 'down') decelCount++;
      });

      return [
        { label: 'Accelerating', value: String(accelCount), color: 'var(--green)' },
        { label: 'Decelerating', value: String(decelCount), color: decelCount > 0 ? 'var(--red)' : 'var(--green)' }
      ];
    },

    getAttentionItems: function(data) {
      if (!data || !data.available) return [];

      var items = [];
      var areas = data.areas || [];

      // Calculate median total_events
      var sorted = areas.map(function(a) { return a.total_events || 0; }).sort(function(a, b) { return a - b; });
      var median = 0;
      if (sorted.length > 0) {
        var mid = Math.floor(sorted.length / 2);
        median = sorted.length % 2 === 0
          ? (sorted[mid - 1] + sorted[mid]) / 2
          : sorted[mid];
      }

      // Flag high-usage areas that are decelerating
      areas.forEach(function(a) {
        if (a.momentum === 'down' && (a.total_events || 0) > median && median > 0) {
          items.push({
            severity: 'medium',
            text: a.area + ' is decelerating (was high-usage)',
            action: { panel: 'velocity' }
          });
        }
      });

      return items;
    }
  });

})();
