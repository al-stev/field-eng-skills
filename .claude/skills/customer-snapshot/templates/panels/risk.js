/**
 * Risk Scoring Panel -- Dashboard V2
 *
 * Composite risk gauge (0-100), factor radar with historical comparison,
 * risk trend line, renewal context, and recommended actions.
 *
 * Data source: INTELLIGENCE_DATA.analytics.risk
 * Transform: RiskScoringTransform
 *
 * Registers with PanelRegistry. No ES module syntax.
 */
(function() {
  'use strict';

  // --- Helpers ---
  function isDark() {
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  }

  function riskColor(score) {
    if (score >= 70) return 'var(--red)';
    if (score >= 40) return 'var(--amber)';
    return 'var(--green)';
  }

  function renewalColor(days) {
    if (typeof days !== 'number') return 'var(--text-primary)';
    if (days < 30) return 'var(--red)';
    if (days < 90) return 'var(--amber)';
    return 'var(--text-primary)';
  }

  // --- CSS (auto-scoped by shell via #panel-risk prefix) ---
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
.veto-banner {\
  display: flex;\
  align-items: center;\
  gap: 8px;\
  padding: 8px 16px;\
  border-radius: 4px;\
  background: var(--amber-dim);\
  border: 1px solid var(--amber-border);\
  color: var(--amber);\
  font-family: "JetBrains Mono", monospace;\
  font-size: 11px;\
  font-weight: 600;\
  margin-top: 8px;\
}\
.renewal-row {\
  display: grid;\
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));\
  gap: 16px;\
  margin-bottom: 32px;\
  padding: 16px;\
  background: var(--bg-elevated);\
  border: 1px solid var(--border-subtle);\
  border-radius: 6px;\
}\
.renewal-item-label {\
  font-family: "JetBrains Mono", monospace;\
  font-size: 11px;\
  font-weight: 600;\
  text-transform: uppercase;\
  letter-spacing: 1.5px;\
  color: var(--text-tertiary);\
}\
.renewal-item-value {\
  font-family: "Outfit", system-ui, sans-serif;\
  font-size: 16px;\
  font-weight: 600;\
  color: var(--text-primary);\
  margin-top: 4px;\
}\
.rec-list {\
  list-style: none;\
  padding: 0;\
  margin: 0;\
  counter-reset: rec-counter;\
}\
.rec-item {\
  counter-increment: rec-counter;\
  padding: 12px 0;\
  border-bottom: 1px solid var(--border-subtle);\
  font-family: "Outfit", system-ui, sans-serif;\
  font-size: 14px;\
  color: var(--text-primary);\
  display: flex;\
  align-items: flex-start;\
  gap: 12px;\
}\
.rec-item:last-child {\
  border-bottom: none;\
}\
.rec-num {\
  display: inline-flex;\
  align-items: center;\
  justify-content: center;\
  min-width: 24px;\
  height: 24px;\
  border-radius: 12px;\
  background: var(--bg-surface);\
  font-family: "JetBrains Mono", monospace;\
  font-size: 11px;\
  font-weight: 600;\
  color: var(--text-tertiary);\
  flex-shrink: 0;\
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
    id: 'risk',
    group: 'product-intelligence',
    label: 'Risk Scoring',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>',
    dataKey: 'analytics.risk',

    render: function(container, data, config) {
      var charts = [];

      // Inject CSS once
      if (!_cssInjected && typeof PanelRegistry.injectCSS === 'function') {
        PanelRegistry.injectCSS('risk', PANEL_CSS);
        _cssInjected = true;
      }

      // Empty state
      if (!data || !data.available) {
        container.innerHTML =
          '<div class="placeholder-panel">' +
            '<div class="placeholder-icon">' +
              '<svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="var(--text-tertiary)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">' +
                '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line>' +
              '</svg>' +
            '</div>' +
            '<div class="placeholder-title">No Risk Data</div>' +
            '<div class="placeholder-desc">No risk scoring data available. This requires engagement score history and optionally renewal_predictions data.</div>' +
          '</div>';
        return { charts: charts };
      }

      var risk = data.risk || {};
      var score = risk.score || 0;
      var riskTrend = data.risk_trend || {};
      var renewalCtx = data.renewal_context || {};
      var riskRadar = data.risk_radar || {};
      var narrative = data.narrative || {};

      // --- KPI stats strip ---
      var kpis = data.kpis || [];
      var statsHtml = '<div class="stats-strip">';
      for (var k = 0; k < kpis.length && k < 4; k++) {
        var statColor = 'var(--text-primary)';
        // Color-code Risk Score and Risk Tier
        if (k === 0 || k === 1) {
          statColor = riskColor(score);
        }
        statsHtml += '<div class="stat-card">' +
          '<div class="stat-value" style="color:' + statColor + '">' + (kpis[k].value || '--') + '</div>' +
          '<div class="stat-label">' + (kpis[k].label || '') + '</div>' +
        '</div>';
      }
      statsHtml += '</div>';

      // --- Build container HTML ---
      container.innerHTML = statsHtml +
        '<div class="section-label">COMPOSITE RISK</div>' +
        '<div class="two-col">' +
          '<div class="panel-card">' +
            '<div id="risk-gauge" style="width:100%;height:200px;"></div>' +
            '<div id="risk-veto"></div>' +
          '</div>' +
          '<div class="panel-card">' +
            '<div class="section-label">RISK FACTORS</div>' +
            '<div id="risk-radar" style="width:100%;height:300px;"></div>' +
          '</div>' +
        '</div>' +
        '<div id="risk-renewal"></div>' +
        '<div class="section-label">RISK TREND</div>' +
        '<div class="full-width panel-card">' +
          '<div id="risk-trend" style="width:100%;height:320px;"></div>' +
        '</div>' +
        '<div class="section-label">RECOMMENDED ACTIONS</div>' +
        '<div class="full-width panel-card" id="risk-recs"></div>';

      // =========================================================
      // CHART 1: Composite Risk Gauge
      // =========================================================
      var gaugeEl = container.querySelector('#risk-gauge');
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
                  [0.4, '#4ade80'],
                  [0.7, '#fbbf24'],
                  [1, '#f87171']
                ]
              }
            },
            pointer: { length: '60%', width: 6, itemStyle: { color: ChartHelpers.getColor('text-primary') } },
            axisTick: { show: false },
            splitLine: { show: false },
            axisLabel: {
              color: ChartHelpers.getColor('text-tertiary'),
              fontSize: 11,
              formatter: function(v) {
                if (v === 0) return 'Low';
                if (v === 50) return 'Med';
                if (v === 100) return 'High';
                return '';
              }
            },
            detail: {
              valueAnimation: true,
              fontSize: 36,
              fontFamily: "'Instrument Serif', Georgia, serif",
              color: ChartHelpers.getColor('text-primary'),
              offsetCenter: [0, '70%'],
              formatter: function(v) { return Math.round(v); }
            },
            title: {
              offsetCenter: [0, '90%'],
              fontSize: 14,
              fontFamily: "'Outfit', sans-serif",
              color: ChartHelpers.getColor('text-secondary')
            },
            data: [{ value: score, name: 'Risk Score' }]
          }]
        });
      }

      // Veto banner
      var vetoEl = container.querySelector('#risk-veto');
      if (vetoEl && risk.veto_applied) {
        vetoEl.innerHTML =
          '<div class="veto-banner">' +
            '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>' +
            'Veto rule applied: churn probability >80% floors risk at 70' +
          '</div>';
      }

      // =========================================================
      // CHART 2: Risk Radar
      // =========================================================
      var radarEl = container.querySelector('#risk-radar');
      if (radarEl && riskRadar.indicators) {
        var radarChart = ChartHelpers.createChart(radarEl);
        charts.push(radarChart);

        var indicators = [];
        var rawIndicators = riskRadar.indicators || [];
        for (var ii = 0; ii < rawIndicators.length; ii++) {
          var ind = rawIndicators[ii];
          if (typeof ind === 'string') {
            indicators.push({ name: ind, max: 100 });
          } else {
            indicators.push({ name: ind.name || '', max: ind.max || 100 });
          }
        }

        var radarData = [
          {
            value: riskRadar.current || [],
            name: 'Current',
            areaStyle: { color: 'rgba(248,113,113,0.2)' },
            lineStyle: { color: '#f87171', width: 2 }
          }
        ];
        if (riskRadar.historical_3mo) {
          radarData.push({
            value: riskRadar.historical_3mo,
            name: '3 months ago',
            areaStyle: { color: 'rgba(96,165,250,0.1)' },
            lineStyle: { color: '#60a5fa', width: 1, type: 'dashed' }
          });
        }
        if (riskRadar.historical_6mo) {
          radarData.push({
            value: riskRadar.historical_6mo,
            name: '6 months ago',
            areaStyle: { color: 'rgba(128,128,128,0.05)' },
            lineStyle: { color: ChartHelpers.getColor('text-tertiary'), width: 1, type: 'dotted' }
          });
        }

        radarChart.setOption({
          tooltip: Object.assign({}, ChartHelpers.tooltipConfig(), { trigger: 'item' }),
          legend: {
            data: radarData.map(function(d) { return d.name; }),
            bottom: 0,
            textStyle: {
              color: ChartHelpers.getColor('text-secondary'),
              fontFamily: "'Outfit', sans-serif",
              fontSize: 12
            }
          },
          radar: {
            indicator: indicators,
            shape: 'circle',
            axisName: {
              color: ChartHelpers.getColor('text-secondary'),
              fontSize: 11,
              fontFamily: "'Outfit', sans-serif"
            },
            splitArea: { areaStyle: { color: ['transparent'] } },
            splitLine: { lineStyle: { color: ChartHelpers.getColor('border-subtle') } },
            axisLine: { lineStyle: { color: ChartHelpers.getColor('border-subtle') } }
          },
          series: [{ type: 'radar', data: radarData }]
        });
      }

      // =========================================================
      // SECTION: Renewal Context
      // =========================================================
      var renewalEl = container.querySelector('#risk-renewal');
      if (renewalEl) {
        var dtr = renewalCtx.days_to_renewal;
        var dtrDisplay = (dtr != null && dtr !== 'N/A') ? dtr + ' days' : 'N/A';
        var dtrColor = renewalColor(typeof dtr === 'number' ? dtr : null);
        var arrDisplay = renewalCtx.arr ? '$' + Math.round(renewalCtx.arr / 1000) + 'K' : 'N/A';
        var seatUtil = renewalCtx.seat_utilization != null ? renewalCtx.seat_utilization + '%' : 'N/A';

        renewalEl.innerHTML =
          '<div class="renewal-row">' +
            '<div>' +
              '<div class="renewal-item-label">To Renewal</div>' +
              '<div class="renewal-item-value" style="color:' + dtrColor + '">' + dtrDisplay + '</div>' +
            '</div>' +
            '<div>' +
              '<div class="renewal-item-label">Contract End</div>' +
              '<div class="renewal-item-value">' + (renewalCtx.contract_end || 'N/A') + '</div>' +
            '</div>' +
            '<div>' +
              '<div class="renewal-item-label">ARR</div>' +
              '<div class="renewal-item-value">' + arrDisplay + '</div>' +
            '</div>' +
            '<div>' +
              '<div class="renewal-item-label">Seat Utilization</div>' +
              '<div class="renewal-item-value">' + seatUtil + '</div>' +
            '</div>' +
          '</div>';
      }

      // =========================================================
      // CHART 3: Risk Trend Line
      // =========================================================
      var trendEl = container.querySelector('#risk-trend');
      if (trendEl && riskTrend.months) {
        var trendChart = ChartHelpers.createChart(trendEl);
        charts.push(trendChart);

        var months = riskTrend.months || [];
        var scores = riskTrend.scores || [];
        var tiers = riskTrend.tiers || [];

        var trendOption = {
          tooltip: Object.assign({}, ChartHelpers.tooltipConfig(), {
            trigger: 'axis',
            formatter: function(params) {
              var idx = params[0].dataIndex;
              var tier = tiers[idx] || '';
              return '<div style="font-weight:600;margin-bottom:4px">' + months[idx] + '</div>' +
                '<div>Risk score ' + scores[idx] + ' (' + tier + ')</div>';
            }
          }),
          grid: { left: 48, right: 24, top: 32, bottom: 60 },
          xAxis: {
            type: 'category',
            data: months,
            boundaryGap: false,
            axisLabel: ChartHelpers.axisLabelConfig(),
            axisLine: { lineStyle: { color: ChartHelpers.getColor('border-subtle') } },
            axisTick: { show: false }
          },
          yAxis: {
            type: 'value',
            min: 0,
            max: 100,
            splitNumber: 5,
            axisLabel: ChartHelpers.axisLabelConfig(),
            splitLine: ChartHelpers.gridLine(),
            axisLine: { show: false },
            axisTick: { show: false }
          },
          series: [{
            type: 'line',
            data: scores,
            smooth: true,
            lineStyle: { color: '#f87171', width: 2 },
            itemStyle: { color: '#f87171' },
            areaStyle: { color: 'rgba(248,113,113,0.08)' },
            markArea: {
              silent: true,
              data: [
                [{ yAxis: 70, itemStyle: { color: 'rgba(248,113,113,0.06)' } }, { yAxis: 100 }],
                [{ yAxis: 40, itemStyle: { color: 'rgba(251,191,36,0.06)' } }, { yAxis: 70 }]
              ]
            },
            markLine: {
              silent: true,
              symbol: 'none',
              data: [
                {
                  yAxis: 40,
                  lineStyle: { type: 'dashed', color: '#fbbf24', width: 1 },
                  label: { show: true, formatter: 'Medium', color: '#fbbf24', fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }
                },
                {
                  yAxis: 70,
                  lineStyle: { type: 'dashed', color: '#f87171', width: 1 },
                  label: { show: true, formatter: 'High', color: '#f87171', fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }
                }
              ]
            }
          }]
        };

        // Add dataZoom if 12+ months
        if (months.length >= 12) {
          trendOption.dataZoom = [
            { type: 'inside' },
            { type: 'slider', bottom: 10 }
          ];
        }

        trendChart.setOption(trendOption);
      }

      // =========================================================
      // SECTION: Recommended Actions
      // =========================================================
      var recsEl = container.querySelector('#risk-recs');
      if (recsEl) {
        var recommendations = narrative.recommendations || [];
        if (recommendations.length > 0) {
          var recsHtml = '<ol class="rec-list">';
          for (var ri = 0; ri < recommendations.length; ri++) {
            recsHtml += '<li class="rec-item">' +
              '<span class="rec-num">' + (ri + 1) + '</span>' +
              '<span>' + recommendations[ri] + '</span>' +
            '</li>';
          }
          recsHtml += '</ol>';
          recsEl.innerHTML = recsHtml;
        } else {
          recsEl.innerHTML = '<div style="font-family:Outfit,system-ui,sans-serif;font-size:14px;color:var(--text-tertiary);padding:8px 0;">No specific recommendations at this time.</div>';
        }
      }

      return { charts: charts };
    },

    getHeadlineStats: function(data) {
      if (!data || !data.available) return [];
      var score = data.risk ? data.risk.score : null;
      if (score === null || score === undefined) return [];
      var color = riskColor(score);
      return [
        {
          label: 'Churn Risk',
          value: Math.round(score) + '/100',
          color: color
        },
        {
          label: 'Risk Tier',
          value: score >= 70 ? 'High' : score >= 40 ? 'Medium' : 'Low',
          color: color
        }
      ];
    },

    getAttentionItems: function(data) {
      if (!data || !data.available) return [];
      var items = [];
      if (data.risk && data.risk.score >= 70) {
        items.push({
          severity: 'high',
          text: 'High churn risk (' + Math.round(data.risk.score) + '/100)',
          action: { panel: 'risk' }
        });
      }
      if (data.renewal_context && data.renewal_context.days_to_renewal !== 'N/A' && typeof data.renewal_context.days_to_renewal === 'number' && data.renewal_context.days_to_renewal < 90) {
        items.push({
          severity: 'medium',
          text: 'Renewal in ' + data.renewal_context.days_to_renewal + ' days',
          action: { panel: 'risk' }
        });
      }
      return items;
    }
  });
})();
