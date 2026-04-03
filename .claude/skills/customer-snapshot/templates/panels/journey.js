/**
 * User Journey Panel — Dashboard V2
 *
 * Five visualization sections:
 *   1. KPI stats strip (4 cards)
 *   2. Adoption Funnel: Sankey diagram + Funnel chart (two-col)
 *   3. Stage Completion table
 *   4. User Timeline (custom Gantt-style chart)
 *   5. ML Maturity score + breakdown
 *
 * Data source: INTELLIGENCE_DATA.analytics.journey
 * Registers with PanelRegistry. No ES module syntax.
 */
(function() {
  'use strict';

  function isDark() {
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  }

  // --- CSS (auto-scoped by shell via #panel-journey prefix) ---
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
.ticket-table {\
  width: 100%;\
  border-collapse: collapse;\
}\
.ticket-table th {\
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
.ticket-table td {\
  font-family: "Outfit", system-ui, sans-serif;\
  font-size: 14px;\
  font-weight: 400;\
  padding: 10px 12px;\
  border-bottom: 1px solid var(--border-subtle);\
  vertical-align: middle;\
}\
.ticket-table tr:hover {\
  background: var(--bg-hover);\
  transition: background 0.15s;\
}\
.ticket-table tr:last-child td {\
  border-bottom: none;\
}\
.maturity-badge {\
  display: inline-block;\
  padding: 4px 12px;\
  border-radius: 10px;\
  font-family: "JetBrains Mono", monospace;\
  font-size: 11px;\
  font-weight: 600;\
  text-transform: uppercase;\
  letter-spacing: 1px;\
}\
.maturity-badge.advanced {\
  color: var(--green);\
  background: var(--green-dim);\
  border: 1px solid var(--green-border);\
}\
.maturity-badge.intermediate {\
  color: var(--amber);\
  background: var(--amber-dim);\
  border: 1px solid var(--amber-border);\
}\
.maturity-badge.beginner {\
  color: var(--blue);\
  background: var(--blue-dim);\
  border: 1px solid var(--blue-border);\
}\
.funnel-row {\
  display: flex;\
  align-items: center;\
  gap: 12px;\
  margin-bottom: 8px;\
}\
.funnel-label {\
  width: 140px;\
  font-family: "Outfit", system-ui, sans-serif;\
  font-size: 13px;\
  font-weight: 500;\
  color: var(--text-primary);\
  text-align: right;\
}\
.funnel-bar-outer {\
  flex: 1;\
  height: 28px;\
  background: var(--bg-surface);\
  border-radius: 4px;\
  position: relative;\
  overflow: hidden;\
}\
.funnel-stat {\
  width: 100px;\
  font-family: "JetBrains Mono", monospace;\
  font-size: 12px;\
  color: var(--text-secondary);\
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

  function maturityClass(tier) {
    if (!tier) return 'beginner';
    var t = tier.toLowerCase();
    if (t.indexOf('advanced') >= 0) return 'advanced';
    if (t.indexOf('intermediate') >= 0) return 'intermediate';
    return 'beginner';
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
      '<line x1="6" y1="3" x2="6" y2="15"></line><circle cx="18" cy="6" r="3"></circle><circle cx="6" cy="18" r="3"></circle>' +
      '<path d="M18 9a9 9 0 0 1-9 9"></path></svg></div>' +
      '<div class="placeholder-title">User Journey</div>' +
      '<div class="placeholder-desc">No user adoption data available. Ensure the customer has an sfdc_account_id configured in customers.yaml and dim_users data exists in BigQuery.</div>' +
      '</div>';
  }

  // --- Registration ---

  PanelRegistry.register({
    id: 'journey',

    render: function(container, data, config) {
      var charts = [];

      // CSS injection guard
      if (!document.querySelector('style[data-panel="journey"]')) {
        PanelRegistry.injectCSS('journey', PANEL_CSS);
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

      // --- ADOPTION FUNNEL section (two-col: Sankey left, Funnel bars right) ---
      html += '<div class="section-label">ADOPTION FUNNEL</div>';
      html += '<div class="two-col">';
      html += '<div class="panel-card"><div id="journey-sankey" style="width:100%;height:400px;"></div></div>';
      html += '<div class="panel-card"><div id="journey-funnel" style="width:100%;height:400px;"></div></div>';
      html += '</div>';

      // --- STAGE COMPLETION section ---
      html += '<div class="section-label">STAGE COMPLETION</div>';
      html += '<div class="full-width"><div class="panel-card">';
      var stages = data.stage_completion || [];
      if (stages.length > 0) {
        html += '<table class="ticket-table">';
        html += '<thead><tr><th>Stage</th><th style="text-align:right">Users</th><th style="text-align:right">Median Days</th></tr></thead>';
        html += '<tbody>';
        for (var i = 0; i < stages.length; i++) {
          var s = stages[i];
          var bgStyle = i % 2 === 1 ? ' style="background:var(--bg-surface)"' : '';
          html += '<tr' + bgStyle + '>';
          html += '<td>' + escapeHtml(s.stage) + '</td>';
          html += '<td style="text-align:right">' + (s.count != null ? s.count : '--') + '</td>';
          html += '<td style="text-align:right">' + (s.median_days != null ? s.median_days.toFixed(1) : '--') + '</td>';
          html += '</tr>';
        }
        html += '</tbody></table>';
      } else {
        html += '<div style="text-align:center;padding:32px;color:var(--text-tertiary);font-size:14px;">No stage completion data</div>';
      }
      html += '</div></div>';

      // --- USER TIMELINE section ---
      html += '<div class="section-label">USER TIMELINE</div>';
      html += '<div class="full-width"><div class="panel-card">';
      var timeline = data.timeline || [];
      if (timeline.length > 0) {
        html += '<div id="journey-timeline" style="width:100%;height:320px;"></div>';
      } else {
        html += '<div style="text-align:center;padding:32px;color:var(--text-tertiary);font-size:14px;">No user timeline data available</div>';
      }
      html += '</div></div>';

      // --- ML MATURITY section ---
      html += '<div class="section-label">ML MATURITY</div>';
      html += '<div class="full-width"><div class="panel-card">';
      var ml = data.ml_maturity;
      if (ml) {
        var tierClass = maturityClass(ml.tier);
        html += '<div style="display:flex;align-items:center;gap:16px;margin-bottom:16px;">';
        html += '<div class="stat-value" style="color:var(--text-primary)">' + (ml.score != null ? ml.score.toFixed(1) : '--') + '</div>';
        html += '<div class="maturity-badge ' + tierClass + '">' + escapeHtml(ml.tier || 'Unknown') + '</div>';
        html += '</div>';

        // Breakdown as mini bar chart
        var bd = ml.breakdown || {};
        var bdKeys = Object.keys(bd);
        if (bdKeys.length > 0) {
          html += '<div id="journey-maturity" style="width:100%;height:' + Math.max(120, bdKeys.length * 32 + 40) + 'px;"></div>';
        }
      } else {
        html += '<div style="text-align:center;padding:32px;color:var(--text-tertiary);font-size:14px;">No ML maturity data available</div>';
      }
      html += '</div></div>';

      // Inject DOM
      container.innerHTML = html;

      // --- Render ECharts: Sankey ---
      var sankey = data.sankey || { nodes: [], links: [] };
      if (sankey.nodes.length > 0) {
        var sankeyEl = container.querySelector('#journey-sankey');
        if (sankeyEl) {
          var sankeyChart = ChartHelpers.createChart(sankeyEl);

          var nodeColors = {
            'All Users': 'var(--text-secondary)',
            'SDK Installed': 'var(--blue)',
            'First Run': 'var(--green)',
            'First Sweep': 'var(--accent)',
            'First Table': 'var(--accent)',
            'First Weave Call': 'var(--accent)',
            'No SDK': 'var(--red)',
            'SDK Only': 'var(--amber)',
            'Runs Only': 'var(--amber)'
          };
          // Resolve CSS vars for ECharts
          var resolvedNodeColors = {};
          Object.keys(nodeColors).forEach(function(key) {
            var val = nodeColors[key];
            if (val.indexOf('var(--') === 0) {
              var token = val.replace('var(--', '').replace(')', '');
              resolvedNodeColors[key] = ChartHelpers.getColor(token) || '#888';
            } else {
              resolvedNodeColors[key] = val;
            }
          });

          var coloredNodes = sankey.nodes.map(function(n) {
            return {
              name: n.name,
              itemStyle: {
                color: resolvedNodeColors[n.name] || ChartHelpers.getColor('text-tertiary') || '#666',
                borderColor: 'transparent'
              }
            };
          });

          sankeyChart.setOption({
            tooltip: {
              trigger: 'item',
              formatter: function(p) {
                if (p.dataType === 'edge') {
                  return p.data.source + ' \u2192 ' + p.data.target + '<br/>' + p.data.value + ' users';
                }
                return p.name + ': ' + (p.value || '') + ' users';
              }
            },
            series: [{
              type: 'sankey',
              layout: 'none',
              emphasis: { focus: 'adjacency' },
              nodeAlign: 'left',
              nodeWidth: 20,
              nodeGap: 16,
              layoutIterations: 0,
              data: coloredNodes,
              links: sankey.links,
              lineStyle: {
                color: 'gradient',
                opacity: 0.3,
                curveness: 0.5
              },
              label: {
                color: ChartHelpers.getColor('text-primary') || '#e8eaed',
                fontFamily: "'Outfit', sans-serif",
                fontSize: 13,
                formatter: function(p) {
                  return p.name + '\n' + (p.value || '');
                }
              },
              left: 40,
              right: 120,
              top: 20,
              bottom: 20
            }]
          });
          charts.push(sankeyChart);
        }
      }

      // --- Render ECharts: Funnel ---
      var funnel = data.funnel || [];
      if (funnel.length > 0) {
        var funnelEl = container.querySelector('#journey-funnel');
        if (funnelEl) {
          var funnelChart = ChartHelpers.createChart(funnelEl);
          var maxCount = funnel[0].count || 1;

          funnelChart.setOption({
            tooltip: {
              trigger: 'item',
              formatter: function(p) {
                return p.name + '<br/>Users: ' + p.value + ' (' + (p.data.pct != null ? p.data.pct + '%' : '--') + ')';
              }
            },
            series: [{
              type: 'funnel',
              left: 40,
              right: 40,
              top: 20,
              bottom: 20,
              minSize: '10%',
              maxSize: '100%',
              sort: 'descending',
              gap: 2,
              label: {
                show: true,
                position: 'inside',
                fontFamily: "'Outfit', sans-serif",
                fontSize: 13,
                formatter: function(p) {
                  return p.name + '\n' + p.value;
                }
              },
              labelLine: { show: false },
              itemStyle: {
                borderColor: ChartHelpers.getColor('bg-elevated') || '#141820',
                borderWidth: 1
              },
              emphasis: {
                label: { fontSize: 14 }
              },
              data: funnel.map(function(f) {
                return {
                  name: f.stage,
                  value: f.count,
                  pct: f.pct
                };
              })
            }]
          });
          charts.push(funnelChart);
        }
      }

      // --- Render ECharts: User Timeline (custom Gantt-style) ---
      if (timeline.length > 0) {
        var timelineEl = container.querySelector('#journey-timeline');
        if (timelineEl) {
          var timelineChart = ChartHelpers.createChart(timelineEl);
          var usernames = timeline.map(function(u) { return u.username; }).reverse();
          var stageColors = {
            'First Run': ChartHelpers.getColor('green') || '#4ade80',
            'First Sweep': ChartHelpers.getColor('accent') || '#d4a853',
            'First Table': ChartHelpers.getColor('blue') || '#60a5fa',
            'First Weave Call': ChartHelpers.getColor('amber') || '#fbbf24',
            'SDK Installed': ChartHelpers.getColor('text-secondary') || '#8b92a0'
          };
          var defaultColor = ChartHelpers.getColor('text-tertiary') || '#5c6370';

          // Build scatter data: each point is a (date, user) with stage info
          var scatterData = [];
          var legendStages = {};
          for (var ti = 0; ti < timeline.length; ti++) {
            var user = timeline[ti];
            var userIdx = timeline.length - 1 - ti;
            var stages_arr = user.stages || [];
            for (var si = 0; si < stages_arr.length; si++) {
              var stg = stages_arr[si];
              scatterData.push({
                value: [stg.date, userIdx],
                stage: stg.stage,
                username: user.username
              });
              legendStages[stg.stage] = true;
            }
          }

          // Group by stage for separate series
          var stageGroups = {};
          for (var di = 0; di < scatterData.length; di++) {
            var d = scatterData[di];
            if (!stageGroups[d.stage]) stageGroups[d.stage] = [];
            stageGroups[d.stage].push(d.value);
          }

          var series = Object.keys(stageGroups).map(function(stage) {
            return {
              name: stage,
              type: 'scatter',
              symbolSize: 10,
              data: stageGroups[stage],
              itemStyle: { color: stageColors[stage] || defaultColor }
            };
          });

          timelineChart.setOption({
            tooltip: {
              trigger: 'item',
              formatter: function(p) {
                return usernames[p.value[1]] + '<br/>' + p.seriesName + ': ' + p.value[0];
              }
            },
            legend: {
              bottom: 0,
              textStyle: {
                color: ChartHelpers.getColor('text-secondary') || '#8b92a0',
                fontSize: 11,
                fontFamily: "'JetBrains Mono', monospace"
              },
              itemWidth: 12,
              itemHeight: 12
            },
            grid: {
              left: 120,
              right: 16,
              top: 16,
              bottom: 40
            },
            xAxis: {
              type: 'time',
              axisLabel: ChartHelpers.axisLabelConfig(),
              axisLine: { lineStyle: { color: ChartHelpers.getColor('border-subtle') || '#1e2430' } },
              splitLine: ChartHelpers.gridLine()
            },
            yAxis: {
              type: 'category',
              data: usernames,
              axisLabel: {
                fontFamily: "'Outfit', sans-serif",
                fontSize: 12,
                color: ChartHelpers.getColor('text-primary') || '#e8eaed',
                overflow: 'truncate',
                width: 100
              },
              axisLine: { lineStyle: { color: ChartHelpers.getColor('border-subtle') || '#1e2430' } },
              axisTick: { show: false }
            },
            series: series
          });
          charts.push(timelineChart);
        }
      }

      // --- Render ECharts: ML Maturity Breakdown bar chart ---
      if (ml && ml.breakdown) {
        var bdEl = container.querySelector('#journey-maturity');
        if (bdEl) {
          var maturityChart = ChartHelpers.createChart(bdEl);
          var bdObj = ml.breakdown;
          var bdNames = Object.keys(bdObj);
          var bdValues = bdNames.map(function(k) { return bdObj[k]; });

          maturityChart.setOption({
            tooltip: {
              trigger: 'axis',
              axisPointer: { type: 'shadow' }
            },
            grid: { left: 140, right: 24, top: 8, bottom: 8 },
            xAxis: {
              type: 'value',
              min: 0,
              max: 100,
              axisLabel: {
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 11,
                color: ChartHelpers.getColor('text-tertiary') || '#5c6370',
                formatter: '{value}%'
              },
              splitLine: ChartHelpers.gridLine()
            },
            yAxis: {
              type: 'category',
              data: bdNames,
              axisLabel: {
                fontFamily: "'Outfit', sans-serif",
                fontSize: 12,
                color: ChartHelpers.getColor('text-primary') || '#e8eaed'
              },
              axisLine: { lineStyle: { color: ChartHelpers.getColor('border-subtle') || '#1e2430' } },
              axisTick: { show: false }
            },
            series: [{
              type: 'bar',
              data: bdValues.map(function(v) {
                var color = v >= 70 ? (ChartHelpers.getColor('green') || '#4ade80')
                  : v >= 40 ? (ChartHelpers.getColor('amber') || '#fbbf24')
                  : (ChartHelpers.getColor('red') || '#f87171');
                return { value: v, itemStyle: { color: color, borderRadius: [0, 3, 3, 0] } };
              }),
              barMaxWidth: 18
            }]
          });
          charts.push(maturityChart);
        }
      }

      return { charts: charts };
    },

    getHeadlineStats: function(data) {
      if (!data || !data.available) return [];

      var stats = [];
      var kpis = data.kpis || [];
      if (kpis.length > 0) {
        stats.push({
          label: 'Total Users',
          value: kpis[0].value || '0',
          color: 'var(--text-primary)'
        });
      }

      if (data.ml_maturity) {
        var tier = data.ml_maturity.tier || '--';
        var tierColor = 'var(--text-secondary)';
        if (tier.toLowerCase().indexOf('advanced') >= 0) tierColor = 'var(--green)';
        else if (tier.toLowerCase().indexOf('intermediate') >= 0) tierColor = 'var(--amber)';
        stats.push({
          label: 'ML Maturity',
          value: tier,
          color: tierColor
        });
      }

      return stats;
    },

    getAttentionItems: function(data) {
      if (!data || !data.available) return [];

      var items = [];
      var nr = data.never_reached;
      if (nr && nr.stages) {
        for (var i = 0; i < nr.stages.length; i++) {
          var stage = nr.stages[i];
          if (stage.pct > 80) {
            items.push({
              severity: 'medium',
              text: stage.pct + '% of users never reached ' + stage.stage,
              action: { panel: 'journey' }
            });
          }
        }
      }

      return items;
    }
  });
})();
