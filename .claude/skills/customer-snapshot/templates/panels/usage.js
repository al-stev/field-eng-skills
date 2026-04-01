/**
 * Usage Panel — Dashboard V2
 *
 * Extracted from v1 intelligence-dashboard.html (lines 3337-3690).
 * Renders 4 ECharts charts (seat utilization, product radar, Weave ingestion,
 * tracked hours) plus KPI summary row and account health grid.
 *
 * All ECharts instances created via ChartHelpers.createChart() (never direct
 * echarts.init). Account health grid is DOM-based and internal-audience only.
 */
(function() {
  'use strict';

  // ── LOCAL HELPERS ──
  // These exist in v1 global scope; reproduced here for panel isolation.

  function isDark() {
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  }

  function formatNumber(n) {
    if (n === null || n === undefined) return '\u2014';
    return n.toLocaleString();
  }

  function formatTrendHTML(change) {
    if (change === null || change === undefined) return '';
    var arrow = change > 0 ? '\u2191' : change < 0 ? '\u2193' : '\u2192';
    var cls = change > 0 ? 'trend-up' : change < 0 ? 'trend-down' : 'trend-flat';
    return '<span class="' + cls + '">' + arrow + ' ' + Math.abs(change).toFixed(1) + '%</span>';
  }

  function zoneClass(pct) {
    if (pct >= 70) return 'zone-green';
    if (pct >= 40) return 'zone-amber';
    return 'zone-red';
  }

  // ── PANEL CSS ──

  var PANEL_CSS = [
    '.section-label {',
    '  font-family: "JetBrains Mono", monospace;',
    '  font-size: 11px;',
    '  font-weight: 600;',
    '  text-transform: uppercase;',
    '  letter-spacing: 1.5px;',
    '  color: var(--text-tertiary);',
    '  margin-bottom: 16px;',
    '}',
    '.usage-kpi-row {',
    '  display: flex;',
    '  gap: clamp(24px, 4vw, 48px);',
    '  flex-wrap: wrap;',
    '  margin-bottom: 24px;',
    '}',
    '.usage-kpi-item {',
    '  display: flex;',
    '  flex-direction: column;',
    '}',
    '.usage-kpi-value {',
    '  font-family: "Outfit", system-ui, sans-serif;',
    '  font-size: 14px;',
    '  font-weight: 600;',
    '  color: var(--text-primary);',
    '}',
    '.trend-up {',
    '  color: var(--green);',
    '  font-family: "JetBrains Mono", monospace;',
    '  font-size: 11px;',
    '  font-weight: 400;',
    '  margin-left: 6px;',
    '}',
    '.trend-down {',
    '  color: var(--red);',
    '  font-family: "JetBrains Mono", monospace;',
    '  font-size: 11px;',
    '  font-weight: 400;',
    '  margin-left: 6px;',
    '}',
    '.trend-flat {',
    '  color: var(--text-tertiary);',
    '  font-family: "JetBrains Mono", monospace;',
    '  font-size: 11px;',
    '  font-weight: 400;',
    '  margin-left: 6px;',
    '}',
    '.zone-green { color: var(--green); }',
    '.zone-amber { color: var(--amber); }',
    '.zone-red { color: var(--red); }',
    '.usage-chart-section {',
    '  margin-bottom: 32px;',
    '}',
    '.usage-chart-section .chart-label {',
    '  font-family: "JetBrains Mono", monospace;',
    '  font-size: 11px;',
    '  font-weight: 600;',
    '  text-transform: uppercase;',
    '  letter-spacing: 1.5px;',
    '  color: var(--text-tertiary);',
    '  margin-bottom: 12px;',
    '}',
    '.account-health-grid {',
    '  display: grid;',
    '  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));',
    '  gap: 16px;',
    '  margin-top: 24px;',
    '}',
    '.health-card {',
    '  background: var(--bg-elevated);',
    '  border: 1px solid var(--border-subtle);',
    '  border-radius: 6px;',
    '  padding: 16px;',
    '}',
    '.health-card-label {',
    '  font-family: "JetBrains Mono", monospace;',
    '  font-size: 11px;',
    '  font-weight: 600;',
    '  text-transform: uppercase;',
    '  letter-spacing: 1.5px;',
    '  color: var(--text-tertiary);',
    '}',
    '.health-card-value {',
    '  font-family: "Outfit", system-ui, sans-serif;',
    '  font-size: 14px;',
    '  font-weight: 600;',
    '  color: var(--text-primary);',
    '  margin-top: 4px;',
    '}',
    '.health-badge {',
    '  display: inline-block;',
    '  font-family: "JetBrains Mono", monospace;',
    '  font-size: 11px;',
    '  font-weight: 600;',
    '  text-transform: uppercase;',
    '  padding: 2px 8px;',
    '  border-radius: 10px;',
    '}',
    '.health-badge-green {',
    '  color: var(--green);',
    '  background: var(--green-dim);',
    '}',
    '.health-badge-amber {',
    '  color: var(--amber);',
    '  background: var(--amber-dim);',
    '}',
    '.health-badge-red {',
    '  color: var(--red);',
    '  background: var(--red-dim);',
    '}',
    '.usage-empty-state {',
    '  display: flex;',
    '  flex-direction: column;',
    '  align-items: center;',
    '  justify-content: center;',
    '  min-height: 300px;',
    '  text-align: center;',
    '}',
    '.usage-empty-icon {',
    '  width: 48px;',
    '  height: 48px;',
    '  display: flex;',
    '  align-items: center;',
    '  justify-content: center;',
    '  background: var(--bg-surface);',
    '  border: 1px solid var(--border-subtle);',
    '  border-radius: 12px;',
    '  margin-bottom: 16px;',
    '}',
    '.usage-empty-title {',
    '  font-family: "Instrument Serif", serif;',
    '  font-size: 24px;',
    '  color: var(--text-primary);',
    '  margin-bottom: 8px;',
    '}',
    '.usage-empty-desc {',
    '  font-family: "Outfit", system-ui, sans-serif;',
    '  font-size: 14px;',
    '  color: var(--text-secondary);',
    '  max-width: 400px;',
    '}',
    '.usage-two-col {',
    '  display: grid;',
    '  grid-template-columns: 1fr 1fr;',
    '  gap: 24px;',
    '}',
    '@media (max-width: 700px) {',
    '  .usage-two-col {',
    '    grid-template-columns: 1fr;',
    '  }',
    '}'
  ].join('\n');

  // ── SUB-RENDERERS ──

  /**
   * Render KPI summary row with seat utilization, Weave ingestion, and run count.
   * @param {HTMLElement} container - KPI row container
   * @param {Object} data - usage data object
   */
  function renderKPIs(container, data) {
    if (!data) return;
    var t = data.trends || {};
    var html = '';

    if (data.seat_utilization) {
      html += '<div class="usage-kpi-item">' +
        '<span class="usage-kpi-value">' +
        data.seat_utilization.active + ' / ' + data.seat_utilization.contracted + ' seats ' +
        '(<span class="' + zoneClass(data.seat_utilization.utilization_percent) + '">' +
        Math.round(data.seat_utilization.utilization_percent) + '%</span>)' +
        '</span>' +
        formatTrendHTML(t.seat_utilization_change) +
        '</div>';
    }

    if (data.weave) {
      html += '<div class="usage-kpi-item">' +
        '<span class="usage-kpi-value">' +
        data.weave.ingestion_gb.toFixed(0) + ' GB / ' + data.weave.limit_gb.toFixed(0) + ' GB ' +
        '(<span class="' + zoneClass(data.weave.utilization_percent) + '">' +
        Math.round(data.weave.utilization_percent) + '%</span>)' +
        '</span>' +
        formatTrendHTML(t.weave_ingestion_change) +
        '</div>';
    }

    if (data.tracked_hours) {
      html += '<div class="usage-kpi-item">' +
        '<span class="usage-kpi-value">' +
        formatNumber(data.tracked_hours.last_30d_run_count) + ' runs last 30d' +
        '</span>' +
        formatTrendHTML(t.run_count_change) +
        '</div>';
    }

    container.innerHTML = html;
  }

  /**
   * Render seat utilization line chart with contracted threshold.
   * @param {HTMLElement} chartEl - Chart container element
   * @param {Object} data - usage data object
   * @returns {Object|null} ECharts instance or null
   */
  function renderSeatChart(chartEl, data) {
    var seatData = data.seat_utilization;
    if (!seatData || !seatData.history || seatData.history.length === 0) return null;

    var chart = ChartHelpers.createChart(chartEl);
    var weeks = seatData.history.map(function(h) {
      var d = new Date(h.week + 'T00:00:00');
      return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
    });
    var activeValues = seatData.history.map(function(h) { return h.active; });
    var blueColor = isDark() ? '#60a5fa' : '#1565a0';
    var accentColor = isDark() ? '#d4a853' : '#b8922e';

    chart.setOption({
      tooltip: {
        trigger: 'axis',
        backgroundColor: ChartHelpers.tooltipConfig().backgroundColor,
        borderColor: ChartHelpers.tooltipConfig().borderColor,
        textStyle: ChartHelpers.tooltipConfig().textStyle,
        formatter: function(params) {
          var p = params[0];
          return '<strong>' + p.name + '</strong><br/>Active: ' + p.value + '<br/>Contracted: ' + seatData.contracted;
        }
      },
      grid: { left: 48, right: 24, top: 24, bottom: 32 },
      xAxis: {
        type: 'category',
        data: weeks,
        axisLabel: Object.assign({}, ChartHelpers.axisLabelConfig(), {
          rotate: weeks.length > 12 ? 45 : 0
        }),
        axisLine: { lineStyle: { color: ChartHelpers.getColor('border-subtle') } },
        axisTick: { lineStyle: { color: ChartHelpers.getColor('border-subtle') } }
      },
      yAxis: {
        type: 'value',
        min: 0,
        max: Math.max(seatData.contracted, Math.max.apply(null, activeValues)) + 5,
        axisLabel: ChartHelpers.axisLabelConfig(),
        splitLine: ChartHelpers.gridLine(),
        axisLine: { lineStyle: { color: ChartHelpers.getColor('border-subtle') } },
        axisTick: { lineStyle: { color: ChartHelpers.getColor('border-subtle') } }
      },
      series: [{
        name: 'Active Seats',
        type: 'line',
        data: activeValues,
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: { color: blueColor, width: 2 },
        itemStyle: { color: blueColor },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: blueColor + '33' },
            { offset: 1, color: blueColor + '05' }
          ])
        },
        markLine: {
          silent: true,
          symbol: 'none',
          lineStyle: { color: accentColor, type: 'dashed', width: 2, opacity: 0.6 },
          label: {
            formatter: 'Contracted: ' + seatData.contracted,
            fontSize: 11,
            fontFamily: "'JetBrains Mono', monospace",
            color: isDark() ? '#5c6370' : '#8c8c8c'
          },
          data: [{ yAxis: seatData.contracted }]
        }
      }]
    });

    return chart;
  }

  /**
   * Render product areas radar chart.
   * @param {HTMLElement} chartEl - Chart container element
   * @param {Object} data - usage data object
   * @returns {Object|null} ECharts instance or null
   */
  function renderRadarChart(chartEl, data) {
    var areas = data.product_areas;
    if (!areas || areas.length === 0) return null;

    // Sort by total_events descending, take top 8
    var sorted = areas.slice().sort(function(a, b) {
      return b.total_events - a.total_events;
    });
    if (sorted.length > 8) sorted = sorted.slice(0, 8);

    var chart = ChartHelpers.createChart(chartEl);
    var maxEvents = Math.max.apply(null, sorted.map(function(a) { return a.total_events; }));
    var maxUsers = Math.max.apply(null, sorted.map(function(a) { return a.unique_users; }));
    var blueColor = isDark() ? '#60a5fa' : '#1565a0';
    var greenColor = isDark() ? '#4ade80' : '#1a7a4c';

    chart.setOption({
      tooltip: {
        trigger: 'item',
        backgroundColor: ChartHelpers.tooltipConfig().backgroundColor,
        borderColor: ChartHelpers.tooltipConfig().borderColor,
        textStyle: ChartHelpers.tooltipConfig().textStyle,
        formatter: function(params) {
          var d = params.data;
          var tip = '<strong>' + d.name + '</strong><br/>';
          sorted.forEach(function(a) {
            if (d.name === 'Events') {
              tip += a.area + ': ' + a.total_events.toLocaleString() + '<br/>';
            } else {
              tip += a.area + ': ' + a.unique_users + '<br/>';
            }
          });
          return tip;
        }
      },
      legend: {
        bottom: 0,
        textStyle: {
          color: isDark() ? '#8b92a0' : '#5c5c5c',
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 11
        }
      },
      radar: {
        center: ['50%', '46%'],
        radius: '60%',
        indicator: sorted.map(function(a) {
          return { name: a.area, max: Math.round(maxEvents * 1.2) };
        }),
        shape: 'polygon',
        axisName: {
          color: isDark() ? '#5c6370' : '#8c8c8c',
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 11
        },
        splitArea: {
          areaStyle: { color: ['transparent'] }
        },
        splitLine: {
          lineStyle: { color: isDark() ? '#1e2430' : '#e0ded9' }
        },
        axisLine: {
          lineStyle: { color: isDark() ? '#2a3040' : '#d4d2ce' }
        }
      },
      series: [{
        type: 'radar',
        data: [
          {
            name: 'Events',
            value: sorted.map(function(a) { return a.total_events; }),
            lineStyle: { color: blueColor, width: 2 },
            itemStyle: { color: blueColor },
            areaStyle: { color: blueColor + '22' }
          },
          {
            name: 'Users',
            value: sorted.map(function(a) {
              return maxUsers > 0 ? (a.unique_users / maxUsers) * maxEvents : 0;
            }),
            lineStyle: { color: greenColor, width: 2 },
            itemStyle: { color: greenColor },
            areaStyle: { color: greenColor + '22' }
          }
        ]
      }]
    });

    return chart;
  }

  /**
   * Render Weave ingestion bar chart with limit threshold.
   * @param {HTMLElement} chartEl - Chart container element
   * @param {Object} data - usage data object
   * @returns {Object|null} ECharts instance or null
   */
  function renderWeaveChart(chartEl, data) {
    var weaveData = data.weave;
    if (!weaveData || !weaveData.history || weaveData.history.length === 0) return null;

    var chart = ChartHelpers.createChart(chartEl);
    var months = weaveData.history.map(function(h) {
      return ChartHelpers.formatMonth(h.month);
    });
    var values = weaveData.history.map(function(h) { return h.ingestion_gb; });
    var blueColor = isDark() ? '#60a5fa' : '#1565a0';
    var accentColor = isDark() ? '#d4a853' : '#b8922e';

    var markLineConfig = undefined;
    if (weaveData.limit_gb) {
      markLineConfig = {
        silent: true,
        symbol: 'none',
        lineStyle: { color: accentColor, type: 'dashed', width: 2, opacity: 0.6 },
        label: {
          formatter: 'Limit: ' + weaveData.limit_gb + ' GB',
          fontSize: 11,
          fontFamily: "'JetBrains Mono', monospace",
          color: isDark() ? '#5c6370' : '#8c8c8c',
          position: 'insideEndTop'
        },
        data: [{ yAxis: weaveData.limit_gb }]
      };
    }

    chart.setOption({
      tooltip: {
        trigger: 'axis',
        backgroundColor: ChartHelpers.tooltipConfig().backgroundColor,
        borderColor: ChartHelpers.tooltipConfig().borderColor,
        textStyle: ChartHelpers.tooltipConfig().textStyle,
        formatter: function(params) {
          var p = params[0];
          var tip = '<strong>' + p.name + '</strong><br/>Ingestion: ' + p.value.toFixed(1) + ' GB';
          if (weaveData.limit_gb) {
            tip += '<br/>Limit: ' + weaveData.limit_gb + ' GB';
          }
          return tip;
        }
      },
      grid: { left: 56, right: 24, top: 24, bottom: 32 },
      xAxis: {
        type: 'category',
        data: months,
        axisLabel: ChartHelpers.axisLabelConfig(),
        axisLine: { lineStyle: { color: ChartHelpers.getColor('border-subtle') } },
        axisTick: { lineStyle: { color: ChartHelpers.getColor('border-subtle') } }
      },
      yAxis: {
        type: 'value',
        axisLabel: Object.assign({}, ChartHelpers.axisLabelConfig(), {
          formatter: '{value} GB'
        }),
        splitLine: ChartHelpers.gridLine(),
        axisLine: { lineStyle: { color: ChartHelpers.getColor('border-subtle') } },
        axisTick: { lineStyle: { color: ChartHelpers.getColor('border-subtle') } }
      },
      series: [{
        name: 'Ingestion',
        type: 'bar',
        data: values,
        barWidth: '60%',
        itemStyle: {
          color: blueColor,
          borderRadius: [3, 3, 0, 0]
        },
        markLine: markLineConfig
      }]
    });

    return chart;
  }

  /**
   * Render tracked hours bar chart.
   * @param {HTMLElement} chartEl - Chart container element
   * @param {Object} data - usage data object
   * @returns {Object|null} ECharts instance or null
   */
  function renderHoursChart(chartEl, data) {
    var hoursData = data.tracked_hours;
    if (!hoursData || !hoursData.history || hoursData.history.length === 0) return null;

    var chart = ChartHelpers.createChart(chartEl);
    var weeks = hoursData.history.map(function(h) {
      var d = new Date(h.week + 'T00:00:00');
      return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
    });
    var values = hoursData.history.map(function(h) { return h.tracked_hours; });
    var blueColor = isDark() ? '#60a5fa' : '#1565a0';

    chart.setOption({
      tooltip: {
        trigger: 'axis',
        backgroundColor: ChartHelpers.tooltipConfig().backgroundColor,
        borderColor: ChartHelpers.tooltipConfig().borderColor,
        textStyle: ChartHelpers.tooltipConfig().textStyle,
        formatter: function(params) {
          var p = params[0];
          return '<strong>' + p.name + '</strong><br/>Hours: ' + Math.round(p.value) + 'h';
        }
      },
      grid: { left: 72, right: 24, top: 24, bottom: 32 },
      xAxis: {
        type: 'category',
        data: weeks,
        axisLabel: Object.assign({}, ChartHelpers.axisLabelConfig(), {
          rotate: weeks.length > 12 ? 45 : 0
        }),
        axisLine: { lineStyle: { color: ChartHelpers.getColor('border-subtle') } },
        axisTick: { lineStyle: { color: ChartHelpers.getColor('border-subtle') } }
      },
      yAxis: {
        type: 'value',
        axisLabel: Object.assign({}, ChartHelpers.axisLabelConfig(), {
          formatter: '{value}h'
        }),
        splitLine: ChartHelpers.gridLine(),
        axisLine: { lineStyle: { color: ChartHelpers.getColor('border-subtle') } },
        axisTick: { lineStyle: { color: ChartHelpers.getColor('border-subtle') } }
      },
      series: [{
        name: 'Tracked Hours',
        type: 'bar',
        data: values,
        barWidth: '60%',
        itemStyle: {
          color: blueColor,
          borderRadius: [3, 3, 0, 0]
        }
      }]
    });

    return chart;
  }

  /**
   * Render account health grid (DOM-based, internal audience only).
   * @param {HTMLElement} container - Grid container element
   * @param {Object} healthData - account_health data object
   */
  function renderAccountHealthGrid(container, healthData) {
    if (!healthData) return;

    var healthBadgeClass = 'health-badge ';
    var healthLabel = healthData.customer_health || '\u2014';
    if (healthLabel === 'Green') healthBadgeClass += 'health-badge-green';
    else if (healthLabel === 'Yellow' || healthLabel === 'Amber') healthBadgeClass += 'health-badge-amber';
    else if (healthLabel === 'Red') healthBadgeClass += 'health-badge-red';

    var renewalDate = healthData.renewal_date ? new Date(healthData.renewal_date + 'T00:00:00') : null;
    var renewalFormatted = renewalDate
      ? renewalDate.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
      : '\u2014';

    var arrFormatted = healthData.arr != null
      ? '$' + Math.round(healthData.arr).toLocaleString()
      : '\u2014';

    var deployLabel = healthData.deployment_type
      ? healthData.deployment_type.split('-').map(function(w) {
          return w.charAt(0).toUpperCase() + w.slice(1);
        }).join(' ')
      : '\u2014';

    var churnColor3 = '';
    if (healthData.churn_probability_3mo != null) {
      if (healthData.churn_probability_3mo < 0.10) churnColor3 = 'var(--green)';
      else if (healthData.churn_probability_3mo < 0.25) churnColor3 = 'var(--amber)';
      else churnColor3 = 'var(--red)';
    }

    var html = '<div class="chart-label">ACCOUNT HEALTH</div>';
    html += '<div class="account-health-grid">';

    // Renewal date
    html += '<div class="health-card">';
    html += '<div class="health-card-label">RENEWAL</div>';
    html += '<div class="health-card-value">' + renewalFormatted + '</div>';
    html += '</div>';

    // ARR
    html += '<div class="health-card">';
    html += '<div class="health-card-label">ARR</div>';
    html += '<div class="health-card-value">' + arrFormatted + '</div>';
    html += '</div>';

    // CS Tier
    html += '<div class="health-card">';
    html += '<div class="health-card-label">CS TIER</div>';
    html += '<div class="health-card-value">' + (healthData.cs_tier || '\u2014') + '</div>';
    html += '</div>';

    // Customer Health
    html += '<div class="health-card">';
    html += '<div class="health-card-label">HEALTH</div>';
    html += '<div class="health-card-value"><span class="' + healthBadgeClass + '">' + healthLabel + '</span></div>';
    html += '</div>';

    // Churn probability
    if (healthData.churn_probability_3mo != null) {
      var churn3 = (healthData.churn_probability_3mo * 100).toFixed(0) + '% (3mo)';
      var churn5 = healthData.churn_probability_5mo != null
        ? (healthData.churn_probability_5mo * 100).toFixed(0) + '% (5mo)'
        : '\u2014';
      html += '<div class="health-card">';
      html += '<div class="health-card-label">CHURN RISK</div>';
      html += '<div class="health-card-value" style="color:' + churnColor3 + '">' + churn3 + ' / ' + churn5 + '</div>';
      html += '</div>';
    }

    // Subscription Plan
    html += '<div class="health-card">';
    html += '<div class="health-card-label">PLAN</div>';
    html += '<div class="health-card-value">' + (healthData.subscription_plan || '\u2014') + '</div>';
    html += '</div>';

    // Deployment Type
    html += '<div class="health-card">';
    html += '<div class="health-card-label">DEPLOYMENT</div>';
    html += '<div class="health-card-value">' + deployLabel + '</div>';
    html += '</div>';

    html += '</div>';
    container.innerHTML = html;
  }

  // ── PANEL REGISTRATION ──

  PanelRegistry.register({
    id: 'usage',
    group: 'usage',
    label: 'Seats & Adoption',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>',
    dataKey: 'usage',
    badgeKey: null,

    /**
     * Render the Usage panel into its container.
     * @param {HTMLElement} container - Panel container element
     * @param {Object} data - INTELLIGENCE_DATA.usage (resolved by shell via dataKey parent)
     * @param {Object} config - { audience: 'internal'|'external' }
     * @returns {Object} { charts: [ECharts instances] }
     */
    render: function(container, data, config) {
      // Inject scoped CSS
      PanelRegistry.injectCSS('usage', PANEL_CSS);

      var charts = [];

      // Handle unavailable data
      if (!data || !data.available) {
        var reason = data ? data.reason : 'not_configured';
        var messages = {
          'not_configured': 'Not configured \u2014 add sfdc_account_id to templates/customers.yaml',
          'no_data': 'No usage data available for this customer',
          'api_error': 'BigQuery data unavailable \u2014 check ADC credentials with /bigquery-setup'
        };
        var msg = messages[reason] || messages['no_data'];

        container.innerHTML =
          '<div class="usage-empty-state">' +
            '<div class="usage-empty-icon">' +
              '<svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="var(--text-tertiary)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">' +
                '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>' +
              '</svg>' +
            '</div>' +
            '<div class="usage-empty-title">No Usage Data</div>' +
            '<div class="usage-empty-desc">' + msg + '</div>' +
          '</div>';

        return { charts: charts };
      }

      // Build panel layout
      var html = '';

      // KPI row
      html += '<div class="usage-kpi-row" id="usage-kpi-row"></div>';

      // Seat utilization chart
      html += '<div class="usage-chart-section">';
      html += '<div class="chart-label">SEAT UTILIZATION</div>';
      html += '<div id="usage-seat-chart" style="width:100%;height:280px;"></div>';
      html += '</div>';

      // Two-column layout for radar + weave
      html += '<div class="usage-two-col">';

      // Radar chart (product areas) -- conditionally shown
      if (data.product_areas && data.product_areas.length > 0) {
        html += '<div class="usage-chart-section" id="usage-radar-section">';
        html += '<div class="chart-label">PRODUCT ADOPTION</div>';
        html += '<div id="usage-radar-chart" style="width:100%;height:380px;"></div>';
        html += '</div>';
      }

      // Weave ingestion chart
      html += '<div class="usage-chart-section">';
      html += '<div class="chart-label">WEAVE INGESTION</div>';
      html += '<div id="usage-weave-chart" style="width:100%;height:240px;"></div>';
      html += '</div>';

      html += '</div>'; // end two-col

      // Tracked hours chart
      html += '<div class="usage-chart-section">';
      html += '<div class="chart-label">TRACKED HOURS</div>';
      html += '<div id="usage-hours-chart" style="width:100%;height:240px;"></div>';
      html += '</div>';

      // Account health grid (internal only)
      if (config && config.audience === 'internal' && data.account_health) {
        html += '<div class="usage-chart-section" id="usage-health-section"></div>';
      }

      container.innerHTML = html;

      // Render KPIs
      var kpiRow = container.querySelector('#usage-kpi-row');
      if (kpiRow) {
        renderKPIs(kpiRow, data);
      }

      // Render seat chart
      var seatEl = container.querySelector('#usage-seat-chart');
      if (seatEl) {
        var seatChart = renderSeatChart(seatEl, data);
        if (seatChart) charts.push(seatChart);
      }

      // Render radar chart (only if product areas present)
      if (data.product_areas && data.product_areas.length > 0) {
        var radarEl = container.querySelector('#usage-radar-chart');
        if (radarEl) {
          var radarChart = renderRadarChart(radarEl, data);
          if (radarChart) charts.push(radarChart);
        }
      }

      // Render Weave chart
      var weaveEl = container.querySelector('#usage-weave-chart');
      if (weaveEl) {
        var weaveChart = renderWeaveChart(weaveEl, data);
        if (weaveChart) charts.push(weaveChart);
      }

      // Render hours chart
      var hoursEl = container.querySelector('#usage-hours-chart');
      if (hoursEl) {
        var hoursChart = renderHoursChart(hoursEl, data);
        if (hoursChart) charts.push(hoursChart);
      }

      // Render account health grid (internal only)
      if (config && config.audience === 'internal' && data.account_health) {
        var healthSection = container.querySelector('#usage-health-section');
        if (healthSection) {
          renderAccountHealthGrid(healthSection, data.account_health);
        }
      }

      return { charts: charts };
    },

    /**
     * Get headline stats for the Overview panel stats strip.
     * @param {Object} data - INTELLIGENCE_DATA.usage
     * @returns {Array} [{ label, value, color }]
     */
    getHeadlineStats: function(data) {
      if (!data || !data.available) return [];
      var stats = [];

      if (data.seat_utilization) {
        var pct = data.seat_utilization.utilization_percent;
        var color = pct >= 70 ? 'var(--green)' : pct >= 40 ? 'var(--amber)' : 'var(--red)';
        stats.push({
          label: 'Seat Utilization',
          value: Math.round(pct) + '%',
          color: color
        });
      }

      if (data.weave) {
        stats.push({
          label: 'Weave',
          value: data.weave.ingestion_gb.toFixed(0) + ' GB',
          color: 'var(--text-primary)'
        });
      }

      if (data.tracked_hours) {
        stats.push({
          label: 'Runs (30d)',
          value: formatNumber(data.tracked_hours.last_30d_run_count),
          color: 'var(--text-primary)'
        });
      }

      return stats;
    },

    /**
     * Get attention items for the Overview panel callouts.
     * @param {Object} data - INTELLIGENCE_DATA.usage
     * @returns {Array} [{ severity, text, action }]
     */
    getAttentionItems: function(data) {
      if (!data || !data.available) return [];
      var items = [];

      // Low seat utilization
      if (data.seat_utilization && data.seat_utilization.utilization_percent < 40) {
        items.push({
          severity: 'medium',
          text: 'Low seat utilization (' + Math.round(data.seat_utilization.utilization_percent) + '%)',
          action: { panel: 'usage' }
        });
      }

      // Declining seat utilization
      if (data.trends && data.trends.seat_utilization_change < -10) {
        items.push({
          severity: 'medium',
          text: 'Seat utilization declining (' + data.trends.seat_utilization_change.toFixed(1) + '%)',
          action: { panel: 'usage' }
        });
      }

      // Elevated churn risk
      if (data.account_health && data.account_health.churn_probability_3mo > 0.2) {
        items.push({
          severity: 'high',
          text: 'Elevated churn risk (' + (data.account_health.churn_probability_3mo * 100).toFixed(0) + '%)',
          action: { panel: 'usage' }
        });
      }

      return items;
    }
  });

})();
