/**
 * Usage Correlation Panel -- Dashboard V2
 *
 * Product combination heatmap, account positioning, expansion signals.
 * SE-Internal Only privacy badge. Cross-account analysis with anonymized data.
 *
 * Data source: INTELLIGENCE_DATA.analytics.correlation
 * Transform: UsageCorrelationTransform
 *
 * Registers with PanelRegistry. No ES module syntax.
 */
(function() {
  'use strict';

  // --- Helpers ---
  function isDark() {
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  }

  // --- CSS (auto-scoped by shell via #panel-correlation prefix) ---
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
.privacy-badge {\
  display: inline-flex;\
  align-items: center;\
  gap: 6px;\
  padding: 4px 12px;\
  border-radius: 4px;\
  background: var(--red-dim);\
  border: 1px solid var(--red-border);\
  color: var(--red);\
  font-family: "JetBrains Mono", monospace;\
  font-size: 11px;\
  font-weight: 600;\
  text-transform: uppercase;\
  letter-spacing: 1.5px;\
  margin-bottom: 24px;\
}\
.expansion-card {\
  background: var(--bg-elevated);\
  border: 1px solid var(--border-subtle);\
  border-radius: 6px;\
  padding: 16px;\
  margin-bottom: 12px;\
}\
.expansion-area {\
  font-family: "Outfit", system-ui, sans-serif;\
  font-size: 14px;\
  font-weight: 600;\
  color: var(--text-primary);\
}\
.expansion-detail {\
  font-family: "JetBrains Mono", monospace;\
  font-size: 11px;\
  color: var(--text-tertiary);\
  margin-top: 4px;\
}\
.nba-list {\
  list-style: none;\
  padding: 0;\
  margin: 0;\
}\
.nba-item {\
  padding: 8px 0;\
  border-bottom: 1px solid var(--border-subtle);\
  display: flex;\
  justify-content: space-between;\
  align-items: center;\
}\
.nba-item:last-child {\
  border-bottom: none;\
}\
.nba-area {\
  font-family: "Outfit", system-ui, sans-serif;\
  font-size: 14px;\
  font-weight: 600;\
  color: var(--text-primary);\
}\
.nba-lift {\
  font-family: "JetBrains Mono", monospace;\
  font-size: 11px;\
  color: var(--green);\
}\
.pos-badge {\
  display: inline-block;\
  padding: 2px 8px;\
  border-radius: 10px;\
  font-family: "JetBrains Mono", monospace;\
  font-size: 11px;\
  font-weight: 400;\
  margin: 2px 4px 2px 0;\
}\
.pos-badge.active {\
  color: var(--green);\
  background: var(--green-dim);\
  border: 1px solid var(--green-border);\
}\
.pos-badge.missing {\
  color: var(--amber);\
  background: var(--amber-dim);\
  border: 1px solid var(--amber-border);\
}\
.match-row {\
  display: flex;\
  align-items: center;\
  gap: 8px;\
  padding: 6px 0;\
  font-family: "Outfit", system-ui, sans-serif;\
  font-size: 14px;\
  color: var(--text-secondary);\
}\
.match-icon {\
  font-size: 14px;\
  flex-shrink: 0;\
}\
.pos-summary {\
  font-family: "Outfit", system-ui, sans-serif;\
  font-size: 14px;\
  font-weight: 600;\
  color: var(--text-primary);\
  margin-bottom: 12px;\
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
    id: 'correlation',
    group: 'product-intelligence',
    label: 'Usage Correlation',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect></svg>',
    dataKey: 'analytics.correlation',

    render: function(container, data, config) {
      var charts = [];

      // Inject CSS once
      if (!_cssInjected && typeof PanelRegistry.injectCSS === 'function') {
        PanelRegistry.injectCSS('correlation', PANEL_CSS);
        _cssInjected = true;
      }

      // Empty state
      if (!data || !data.available) {
        container.innerHTML =
          '<div class="placeholder-panel">' +
            '<div class="placeholder-icon">' +
              '<svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="var(--text-tertiary)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">' +
                '<rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect>' +
              '</svg>' +
            '</div>' +
            '<div class="placeholder-title">No Correlation Data</div>' +
            '<div class="placeholder-desc">No cross-account correlation data available. This analysis requires data from 10+ accounts to ensure privacy.</div>' +
          '</div>';
        return { charts: charts };
      }

      // --- Privacy badge ---
      var privacyHtml =
        '<div class="privacy-badge">' +
          '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>' +
          'SE-INTERNAL ONLY' +
        '</div>';

      // --- KPI stats strip ---
      var kpis = data.kpis || [];
      var statsHtml = '<div class="stats-strip">';
      for (var k = 0; k < kpis.length && k < 4; k++) {
        statsHtml += '<div class="stat-card">' +
          '<div class="stat-value" style="color:var(--text-primary)">' + (kpis[k].value || '--') + '</div>' +
          '<div class="stat-label">' + (kpis[k].label || '') + '</div>' +
        '</div>';
      }
      statsHtml += '</div>';

      // --- Build container HTML ---
      container.innerHTML = privacyHtml + statsHtml +
        '<div class="section-label">PRODUCT CORRELATION MATRIX</div>' +
        '<div class="full-width panel-card">' +
          '<div id="corr-heatmap" style="width:100%;height:500px;"></div>' +
        '</div>' +
        '<div class="two-col">' +
          '<div class="panel-card" id="corr-positioning"></div>' +
          '<div class="panel-card" id="corr-expansion"></div>' +
        '</div>';

      // =========================================================
      // CHART: Product Correlation Matrix (Heatmap)
      // =========================================================
      var heatmapEl = container.querySelector('#corr-heatmap');
      if (heatmapEl && data.correlation_matrix) {
        var cm = data.correlation_matrix;
        var areas = cm.product_areas || [];
        var matrixData = cm.matrix || [];

        // Build symmetric heatmap data from upper-triangle entries
        var heatData = [];
        for (var mi = 0; mi < matrixData.length; mi++) {
          var entry = matrixData[mi];
          var ri = entry[0], ci = entry[1], coOcc = entry[2], retPct = entry[3], cohort = entry[4];
          heatData.push([ci, ri, coOcc, retPct, cohort]);
          heatData.push([ri, ci, coOcc, retPct, cohort]);
        }
        // Diagonal: self (100%)
        for (var di = 0; di < areas.length; di++) {
          heatData.push([di, di, 100, 100, 0]);
        }

        var heatChart = ChartHelpers.createChart(heatmapEl);
        charts.push(heatChart);

        heatChart.setOption({
          tooltip: Object.assign({}, ChartHelpers.tooltipConfig(), {
            trigger: 'item',
            formatter: function(p) {
              var val = p.data;
              if (val[0] === val[1]) return areas[val[0]] + ' (self)';
              return '<div style="font-weight:600;margin-bottom:4px">' + areas[val[1]] + ' + ' + areas[val[0]] + '</div>' +
                '<div>' + val[2] + '% co-occurrence, ' + val[3] + '% retention</div>';
            }
          }),
          grid: { left: 140, right: 80, top: 100, bottom: 80 },
          xAxis: {
            type: 'category',
            data: areas,
            position: 'top',
            axisLabel: Object.assign({}, ChartHelpers.axisLabelConfig(), { rotate: 45, interval: 0 }),
            axisLine: { lineStyle: { color: ChartHelpers.getColor('border-subtle') } },
            axisTick: { show: false },
            splitArea: { show: true, areaStyle: { color: ['transparent', 'rgba(255,255,255,0.02)'] } }
          },
          yAxis: {
            type: 'category',
            data: areas,
            inverse: true,
            axisLabel: Object.assign({}, ChartHelpers.axisLabelConfig(), { interval: 0 }),
            axisLine: { lineStyle: { color: ChartHelpers.getColor('border-subtle') } },
            axisTick: { show: false }
          },
          visualMap: {
            type: 'continuous',
            min: 0,
            max: 100,
            calculable: true,
            orient: 'horizontal',
            left: 'center',
            bottom: 0,
            inRange: { color: ['rgba(96,165,250,0.08)', '#60a5fa'] },
            textStyle: { color: ChartHelpers.getColor('text-secondary'), fontSize: 11 },
            text: ['High', 'Low']
          },
          series: [{
            type: 'heatmap',
            data: heatData,
            label: {
              show: true,
              fontSize: 10,
              fontFamily: "'JetBrains Mono', monospace",
              formatter: function(p) {
                return p.data[0] === p.data[1] ? '' : p.data[2] + '%';
              }
            },
            emphasis: {
              itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.5)' }
            }
          }]
        });
      }

      // =========================================================
      // SECTION: Account Positioning
      // =========================================================
      var posEl = container.querySelector('#corr-positioning');
      if (posEl) {
        var ap = data.account_positioning || {};
        var activeAreas = ap.active_areas || [];
        var totalAreas = ap.total_areas || 0;
        var matchPatterns = ap.match_patterns || [];

        var posHtml = '<div class="section-label">ACCOUNT POSITIONING</div>';
        posHtml += '<div class="pos-summary">Using ' + activeAreas.length + ' of ' + totalAreas + ' product areas</div>';

        // Active areas as badges
        posHtml += '<div style="margin-bottom:16px;">';
        for (var ai = 0; ai < activeAreas.length; ai++) {
          posHtml += '<span class="pos-badge active">' + activeAreas[ai] + '</span>';
        }
        posHtml += '</div>';

        // Match patterns
        for (var pi = 0; pi < matchPatterns.length; pi++) {
          var mp = matchPatterns[pi];
          if (mp.match) {
            posHtml += '<div class="match-row">' +
              '<span class="match-icon" style="color:var(--green)">&#10003;</span>' +
              '<span>Using ' + mp.combo + ' &mdash; ' + mp.retention_boost + ' retention</span>' +
            '</div>';
          } else {
            posHtml += '<div class="match-row">' +
              '<span class="match-icon" style="color:var(--amber)">&#9679;</span>' +
              '<span>Missing ' + (mp.missing || mp.combo) + ' &mdash; ' + mp.retention_boost + ' potential lift</span>' +
            '</div>';
          }
        }

        posEl.innerHTML = posHtml;
      }

      // =========================================================
      // SECTION: Expansion Signals
      // =========================================================
      var expEl = container.querySelector('#corr-expansion');
      if (expEl) {
        var nba = data.next_best_action || [];
        var signals = data.expansion_signals || [];

        var expHtml = '<div class="section-label">EXPANSION SIGNALS</div>';

        if (nba.length > 0) {
          expHtml += '<ul class="nba-list">';
          for (var ni = 0; ni < nba.length; ni++) {
            var item = nba[ni];
            expHtml += '<li class="nba-item">' +
              '<span class="nba-area">' + item.product_area + '</span>' +
              '<span class="nba-lift">+' + (typeof item.avg_retention_lift === 'number' ? item.avg_retention_lift.toFixed(0) : item.avg_retention_lift) + '% retention lift</span>' +
            '</li>';
          }
          expHtml += '</ul>';
        }

        if (signals.length > 0) {
          if (nba.length > 0) {
            expHtml += '<div style="margin-top:16px;"></div>';
          }
          for (var si = 0; si < signals.length; si++) {
            var sig = signals[si];
            expHtml += '<div class="expansion-card">' +
              '<div class="expansion-area">' + sig.product_area + '</div>' +
              '<div class="expansion-detail">' + sig.usage_pct + '% usage &middot; ' + sig.allocation + '</div>' +
            '</div>';
          }
        }

        if (nba.length === 0 && signals.length === 0) {
          expHtml += '<div style="font-family:Outfit,system-ui,sans-serif;font-size:14px;color:var(--text-tertiary);padding:16px 0;">No immediate expansion recommendations.</div>';
        }

        expEl.innerHTML = expHtml;
      }

      return { charts: charts };
    },

    getHeadlineStats: function(data) {
      if (!data || !data.available) return [];
      var kpis = data.kpis || [];
      var stats = [];
      if (kpis.length > 0) {
        stats.push({
          label: 'Product Areas',
          value: kpis[0].value,
          color: 'var(--text-primary)'
        });
      }
      if (kpis.length > 3) {
        var expVal = kpis[3].value;
        stats.push({
          label: 'Expansion Signals',
          value: expVal,
          color: parseInt(expVal) > 0 ? 'var(--green)' : 'var(--text-secondary)'
        });
      }
      return stats;
    },

    getAttentionItems: function(data) {
      if (!data || !data.available) return [];
      var items = [];
      if (data.next_best_action && data.next_best_action.length > 0) {
        var top = data.next_best_action[0];
        items.push({
          severity: 'low',
          text: 'Expansion opportunity: ' + top.product_area + ' (' + (typeof top.avg_retention_lift === 'number' ? top.avg_retention_lift.toFixed(0) : top.avg_retention_lift) + '% retention lift)',
          action: { panel: 'correlation' }
        });
      }
      return items;
    }
  });
})();
