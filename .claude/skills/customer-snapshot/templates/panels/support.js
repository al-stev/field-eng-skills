/**
 * Support Tickets Panel — Dashboard V2
 *
 * Five ECharts visualizations:
 *   1. Monthly volume trend (bar)
 *   2. Concern treemap
 *   3. Active ticket age scatter (with Jira click-through)
 *   4. Top submitters stacked bars
 *   5. Submitter-concern heatmap
 *
 * Registers with PanelRegistry. No ES module syntax.
 */
(function() {
  'use strict';

  // --- CSS (auto-scoped by shell via #panel-support prefix) ---
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
.age-badge {\
  display: inline-block;\
  padding: 2px 8px;\
  border-radius: 10px;\
  font-family: "JetBrains Mono", monospace;\
  font-size: 11px;\
  font-weight: 400;\
}\
.age-badge.green {\
  color: var(--green);\
  background: var(--green-dim);\
  border: 1px solid var(--green-border);\
}\
.age-badge.amber {\
  color: var(--amber);\
  background: var(--amber-dim);\
  border: 1px solid var(--amber-border);\
}\
.age-badge.red {\
  color: var(--red);\
  background: var(--red-dim);\
  border: 1px solid var(--red-border);\
}\
.priority-badge {\
  display: inline-block;\
  padding: 2px 8px;\
  border-radius: 10px;\
  font-family: "JetBrains Mono", monospace;\
  font-size: 11px;\
  font-weight: 400;\
}\
.priority-badge.urgent {\
  color: var(--red);\
  background: var(--red-dim);\
  border: 1px solid var(--red-border);\
}\
.priority-badge.high {\
  color: var(--amber);\
  background: var(--amber-dim);\
  border: 1px solid var(--amber-border);\
}\
.priority-badge.normal {\
  color: var(--blue);\
  background: var(--blue-dim);\
  border: 1px solid var(--blue-border);\
}\
.priority-badge.low {\
  color: var(--text-tertiary);\
  background: var(--bg-surface);\
  border: 1px solid var(--border-subtle);\
}\
.jira-link {\
  font-family: "JetBrains Mono", monospace;\
  font-size: 11px;\
  font-weight: 400;\
  color: var(--blue);\
  text-decoration: none;\
}\
.jira-link:hover {\
  text-decoration: underline;\
}\
.concern-label {\
  font-family: "JetBrains Mono", monospace;\
  font-size: 11px;\
  font-weight: 400;\
  color: var(--text-tertiary);\
  background: var(--bg-surface);\
  padding: 2px 8px;\
  border-radius: 10px;\
}\
.scatter-detail-toggle {\
  cursor: pointer;\
  font-family: "JetBrains Mono", monospace;\
  font-size: 11px;\
  font-weight: 600;\
  color: var(--text-secondary);\
  margin-top: 12px;\
  display: inline-block;\
  user-select: none;\
}\
.scatter-detail-toggle:hover {\
  color: var(--accent);\
}\
.scatter-detail-table {\
  display: none;\
  margin-top: 12px;\
}\
.subject-cell {\
  max-width: 300px;\
  overflow: hidden;\
  text-overflow: ellipsis;\
  white-space: nowrap;\
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
   * Map snake_case concern names to human-readable display names.
   */
  function humanizeConcern(raw) {
    var map = {
      'workspace': 'Workspace',
      'crashed_run': 'Crashed Runs',
      'app__runs_table': 'Runs Table',
      'charts': 'Charts',
      'performance': 'Performance',
      'client__authentication': 'Authentication',
      'reports': 'Reports',
      'admin__service_accounts': 'Service Accounts',
      'connectivity': 'Connectivity',
      'resuming': 'Resuming',
      'app__other': 'App (Other)',
      'app__login': 'Login',
      'client__public_api': 'Public API',
      'cloud_services': 'Cloud Services'
    };
    if (map[raw]) return map[raw];
    // Fallback: replace __ with " / ", _ with " ", title case
    return raw
      .replace(/__/g, ' / ')
      .replace(/_/g, ' ')
      .replace(/\b\w/g, function(c) { return c.toUpperCase(); });
  }

  /**
   * Return an HTML age badge with color coding.
   * Green: <30d, Amber: 30-90d, Red: >90d.
   */
  function ageBadge(days) {
    var cls = 'green';
    if (days >= 90) cls = 'red';
    else if (days >= 30) cls = 'amber';
    return '<span class="age-badge ' + cls + '">' + days + 'd</span>';
  }

  /**
   * Return an HTML priority badge.
   */
  function priorityBadge(priority) {
    var p = (priority || 'normal').toLowerCase();
    var label = p.charAt(0).toUpperCase() + p.slice(1);
    var cls = 'normal';
    if (p === 'urgent') cls = 'urgent';
    else if (p === 'high') cls = 'high';
    else if (p === 'low') cls = 'low';
    return '<span class="priority-badge ' + cls + '">' + label + '</span>';
  }

  // --- REGISTRATION ---
  PanelRegistry.register({
    id: 'support',
    group: 'intelligence',
    label: 'Support',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>',
    badgeKey: 'usage.support_tickets.total',
    dataKey: 'usage.support_tickets',

    render: function(container, data, config) {
      var charts = [];

      // Compute stats
      var total = data.total || 0;
      var activeTickets = (data.recent_tickets || []).filter(function(t) {
        return t.status !== 'closed' && t.status !== 'solved';
      });
      var activeCount = activeTickets.length;
      var closedCount = (data.by_status && data.by_status.closed) || 0;
      var solvedCount = (data.by_status && data.by_status.solved) || 0;
      var resolvedPct = total > 0 ? Math.round((closedCount + solvedCount) / total * 100) : 0;
      var monthCount = (data.monthly_volume && data.monthly_volume.length) || 1;
      var avgPerMonth = (total / Math.max(monthCount, 1)).toFixed(1);

      // Inject CSS
      if (typeof PanelRegistry.injectCSS === 'function') {
        PanelRegistry.injectCSS('support', PANEL_CSS);
      }

      // Build DOM
      container.innerHTML = '\
        <div class="stats-strip">\
          <div class="stat-card">\
            <div class="stat-value" style="color:var(--text-primary)">' + total + '</div>\
            <div class="stat-label">Tickets (12mo)</div>\
          </div>\
          <div class="stat-card">\
            <div class="stat-value" style="color:var(--amber)">' + activeCount + '</div>\
            <div class="stat-label">Active</div>\
          </div>\
          <div class="stat-card">\
            <div class="stat-value" style="color:var(--green)">' + resolvedPct + '%</div>\
            <div class="stat-label">Resolved</div>\
          </div>\
          <div class="stat-card">\
            <div class="stat-value" style="color:var(--text-primary)">' + avgPerMonth + '</div>\
            <div class="stat-label">Avg / Month</div>\
          </div>\
        </div>\
        \
        <div class="section-label">Volume &amp; Concerns</div>\
        <div class="two-col">\
          <div class="panel-card">\
            <div id="chart-volume" style="width:100%;height:320px;"></div>\
          </div>\
          <div class="panel-card">\
            <div id="chart-concerns" style="width:100%;height:320px;"></div>\
          </div>\
        </div>\
        \
        <div class="section-label">Active Tickets</div>\
        <div class="full-width panel-card">\
          <div id="chart-scatter" style="width:100%;height:360px;"></div>\
          <div class="scatter-detail-toggle" id="scatter-toggle">Show detail table</div>\
          <div class="scatter-detail-table" id="scatter-detail">\
            <table class="ticket-table">\
              <thead>\
                <tr>\
                  <th>Jira</th>\
                  <th>Subject</th>\
                  <th>Priority</th>\
                  <th>Age</th>\
                  <th>Status</th>\
                  <th>Concern</th>\
                </tr>\
              </thead>\
              <tbody id="scatter-tbody"></tbody>\
            </table>\
          </div>\
        </div>\
        \
        <div class="section-label">Submitter Analysis</div>\
        <div class="two-col">\
          <div class="panel-card">\
            <div id="chart-submitters" style="width:100%;height:360px;"></div>\
          </div>\
          <div class="panel-card">\
            <div id="chart-heatmap" style="width:100%;height:360px;"></div>\
          </div>\
        </div>\
      ';

      // --- Detail table toggle ---
      var toggleEl = container.querySelector('#scatter-toggle');
      var detailEl = container.querySelector('#scatter-detail');
      if (toggleEl && detailEl) {
        toggleEl.addEventListener('click', function() {
          var showing = detailEl.style.display === 'block';
          detailEl.style.display = showing ? 'none' : 'block';
          toggleEl.textContent = showing ? 'Show detail table' : 'Hide detail table';
        });
      }

      // --- Populate detail table ---
      var tbody = container.querySelector('#scatter-tbody');
      if (tbody && activeTickets.length > 0) {
        var sorted = activeTickets.slice().sort(function(a, b) {
          return ChartHelpers.daysBetween(a.created_at) - ChartHelpers.daysBetween(b.created_at);
        }).reverse();
        for (var i = 0; i < sorted.length; i++) {
          var t = sorted[i];
          var age = ChartHelpers.daysBetween(t.created_at);
          var jiraUrl = t.jira_id ? 'https://wandb.atlassian.net/browse/' + t.jira_id : '';
          var jiraCell = t.jira_id
            ? '<a class="jira-link" href="' + jiraUrl + '" target="_blank" rel="noopener" data-jira-key="' + t.jira_id + '">' + t.jira_id + '</a>'
            : '—';
          var tr = document.createElement('tr');
          tr.innerHTML = '<td>' + jiraCell + '</td>' +
            '<td class="subject-cell" title="' + (t.subject || '').replace(/"/g, '&quot;') + '">' + (t.subject || '—') + '</td>' +
            '<td>' + priorityBadge(t.priority) + '</td>' +
            '<td>' + ageBadge(age) + '</td>' +
            '<td>' + (t.status || '—') + '</td>' +
            '<td><span class="concern-label">' + humanizeConcern(t.concern || '') + '</span></td>';
          tbody.appendChild(tr);
        }
      }

      // =========================================================
      // CHART 1: Monthly Volume Trend (bar)
      // =========================================================
      var volumeContainer = container.querySelector('#chart-volume');
      if (volumeContainer && data.monthly_volume && data.monthly_volume.length > 0) {
        var volumeChart = ChartHelpers.createChart(volumeContainer);
        charts.push(volumeChart);

        var months = data.monthly_volume.map(function(m) {
          return ChartHelpers.formatMonth(m.month);
        });
        var counts = data.monthly_volume.map(function(m) { return m.count; });
        var maxCount = Math.max.apply(null, counts);
        var peakIdx = counts.indexOf(maxCount);

        var barColors = counts.map(function(c) {
          return c === maxCount ? ChartHelpers.getColor('amber') : ChartHelpers.getColor('blue');
        });

        volumeChart.setOption({
          tooltip: Object.assign({}, ChartHelpers.tooltipConfig(), {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            formatter: function(params) {
              var p = params[0];
              return '<div style="font-weight:600;margin-bottom:4px">' + p.axisValue + '</div>' +
                '<div>' + p.value + ' ticket' + (p.value !== 1 ? 's' : '') + '</div>';
            }
          }),
          grid: { left: 48, right: 24, top: 24, bottom: 32 },
          xAxis: {
            type: 'category',
            data: months,
            axisLabel: ChartHelpers.axisLabelConfig(),
            axisLine: { lineStyle: { color: ChartHelpers.getColor('border-subtle') } },
            axisTick: { show: false }
          },
          yAxis: {
            type: 'value',
            minInterval: 1,
            axisLabel: ChartHelpers.axisLabelConfig(),
            splitLine: ChartHelpers.gridLine(),
            axisLine: { show: false },
            axisTick: { show: false }
          },
          series: [{
            type: 'bar',
            data: counts.map(function(c, idx) {
              return {
                value: c,
                itemStyle: { color: barColors[idx] }
              };
            }),
            barWidth: '50%',
            itemStyle: { borderRadius: [3, 3, 0, 0] },
            markPoint: {
              symbol: 'pin',
              symbolSize: 36,
              itemStyle: { color: ChartHelpers.getColor('accent') },
              label: {
                formatter: String(maxCount),
                color: ChartHelpers.getColor('bg-primary') || '#0c0f14',
                fontSize: 11,
                fontWeight: 600
              },
              data: [{
                name: 'Peak',
                xAxis: peakIdx,
                yAxis: maxCount
              }]
            }
          }]
        });
      }

      // =========================================================
      // CHART 2: Concern Treemap
      // =========================================================
      var concernsContainer = container.querySelector('#chart-concerns');
      if (concernsContainer && data.top_concerns && data.top_concerns.length > 0) {
        var treemapChart = ChartHelpers.createChart(concernsContainer);
        charts.push(treemapChart);

        var concernTotal = data.top_concerns.reduce(function(s, c) { return s + c.count; }, 0);
        var treemapData = data.top_concerns.map(function(c) {
          return { name: humanizeConcern(c.concern), value: c.count };
        });

        // Check if all counts are equal
        var allEqual = data.top_concerns.every(function(c) {
          return c.count === data.top_concerns[0].count;
        });

        var treemapOption = {
          tooltip: Object.assign({}, ChartHelpers.tooltipConfig(), {
            trigger: 'item',
            formatter: function(params) {
              var pct = concernTotal > 0
                ? Math.round(params.value / concernTotal * 100)
                : 0;
              return '<div style="font-weight:600;margin-bottom:4px">' + params.name + '</div>' +
                '<div>' + params.value + ' ticket' + (params.value !== 1 ? 's' : '') +
                ' (' + pct + '%)</div>';
            }
          }),
          series: [{
            type: 'treemap',
            width: '100%',
            height: '100%',
            roam: false,
            nodeClick: false,
            breadcrumb: { show: false },
            label: {
              show: true,
              formatter: function(params) {
                return '{name|' + params.name + '}\n{count|' + params.value + '}';
              },
              rich: {
                name: {
                  fontSize: 14,
                  fontFamily: "'Outfit', system-ui, sans-serif",
                  fontWeight: 600,
                  color: ChartHelpers.getColor('text-primary'),
                  padding: [0, 0, 2, 0]
                },
                count: {
                  fontSize: 18,
                  fontFamily: "'JetBrains Mono', monospace",
                  fontWeight: 600,
                  color: ChartHelpers.getColor('text-primary')
                }
              },
              position: 'inside',
              align: 'center',
              verticalAlign: 'middle'
            },
            itemStyle: {
              borderColor: ChartHelpers.getColor('bg-primary') || '#0c0f14',
              borderWidth: 3,
              borderRadius: 4
            },
            emphasis: {
              itemStyle: {
                borderColor: ChartHelpers.getColor('accent'),
                borderWidth: 2
              }
            },
            levels: [{
              itemStyle: {
                borderColor: ChartHelpers.getColor('bg-primary') || '#0c0f14',
                borderWidth: 3,
                gapWidth: 3
              }
            }],
            data: treemapData
          }]
        };

        // Color mapping
        if (allEqual) {
          // Single accent color for all
          treemapOption.series[0].data = treemapData.map(function(d) {
            return Object.assign({}, d, {
              itemStyle: { color: ChartHelpers.getColor('accent') }
            });
          });
        } else {
          treemapOption.series[0].colorMappingBy = 'value';
          treemapOption.visualMap = {
            show: false,
            type: 'continuous',
            min: Math.min.apply(null, data.top_concerns.map(function(c) { return c.count; })),
            max: Math.max.apply(null, data.top_concerns.map(function(c) { return c.count; })),
            inRange: {
              color: [ChartHelpers.getColor('amber'), ChartHelpers.getColor('red')]
            }
          };
        }

        treemapChart.setOption(treemapOption);
      }

      // =========================================================
      // CHART 3: Active Ticket Age Scatter
      // =========================================================
      var scatterContainer = container.querySelector('#chart-scatter');
      if (scatterContainer && activeTickets.length > 0) {
        var scatterChart = ChartHelpers.createChart(scatterContainer);
        charts.push(scatterChart);

        var scatterData = activeTickets.map(function(t) {
          var age = ChartHelpers.daysBetween(t.created_at);
          var color = age >= 90 ? ChartHelpers.getColor('red')
            : age >= 30 ? ChartHelpers.getColor('amber')
            : ChartHelpers.getColor('green');
          var size = (t.priority || '').toLowerCase() === 'urgent' ? 18 : 12;
          return {
            value: [t.created_at, age],
            symbolSize: size,
            itemStyle: {
              color: color,
              borderColor: ChartHelpers.getColor('text-primary'),
              borderWidth: 1
            },
            jiraId: t.jira_id || null,
            subject: t.subject || '',
            priority: t.priority || 'normal',
            status: t.status || ''
          };
        });

        var maxAge = Math.max.apply(null, activeTickets.map(function(t) {
          return ChartHelpers.daysBetween(t.created_at);
        }));
        var yMax = Math.max(maxAge + 20, 100);

        scatterChart.setOption({
          tooltip: Object.assign({}, ChartHelpers.tooltipConfig(), {
            trigger: 'item',
            formatter: function(params) {
              var d = params.data;
              return '<div style="font-weight:600;margin-bottom:4px">' + (d.subject || '—') + '</div>' +
                '<div>Priority: ' + (d.priority || '—') + '</div>' +
                '<div>Age: ' + d.value[1] + ' days</div>' +
                (d.jiraId ? '<div style="margin-top:4px;font-size:11px;color:' + ChartHelpers.getColor('text-tertiary') + '">Click to open ' + d.jiraId + ' in Jira</div>' : '');
            }
          }),
          grid: { left: 56, right: 24, top: 24, bottom: 40 },
          xAxis: {
            type: 'time',
            axisLabel: Object.assign({}, ChartHelpers.axisLabelConfig(), {
              formatter: function(val) {
                var d = new Date(val);
                var months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
                return months[d.getMonth()] + ' ' + String(d.getFullYear()).slice(2);
              }
            }),
            axisLine: { lineStyle: { color: ChartHelpers.getColor('border-subtle') } },
            splitLine: { show: false }
          },
          yAxis: {
            type: 'value',
            name: 'Age (days)',
            nameTextStyle: {
              color: ChartHelpers.getColor('text-tertiary'),
              fontSize: 11,
              fontFamily: "'JetBrains Mono', monospace"
            },
            max: yMax,
            axisLabel: ChartHelpers.axisLabelConfig(),
            splitLine: ChartHelpers.gridLine(),
            axisLine: { show: false }
          },
          series: [
            // Green zone (0-30d)
            {
              type: 'scatter',
              silent: true,
              data: [],
              markArea: {
                silent: true,
                itemStyle: { color: ChartHelpers.getColor('green-dim') || 'rgba(74, 222, 128, 0.08)' },
                data: [[{ yAxis: 0 }, { yAxis: 30 }]]
              }
            },
            // Amber zone (30-90d)
            {
              type: 'scatter',
              silent: true,
              data: [],
              markArea: {
                silent: true,
                itemStyle: { color: ChartHelpers.getColor('amber-dim') || 'rgba(251, 191, 36, 0.08)' },
                data: [[{ yAxis: 30 }, { yAxis: 90 }]]
              }
            },
            // Red zone (90+d)
            {
              type: 'scatter',
              silent: true,
              data: [],
              markArea: {
                silent: true,
                itemStyle: { color: ChartHelpers.getColor('red-dim') || 'rgba(248, 113, 113, 0.08)' },
                data: [[{ yAxis: 90 }, { yAxis: yMax }]]
              }
            },
            // Actual data points
            {
              type: 'scatter',
              data: scatterData,
              emphasis: {
                itemStyle: {
                  borderColor: ChartHelpers.getColor('accent'),
                  borderWidth: 3,
                  shadowBlur: 12,
                  shadowColor: ChartHelpers.getColor('accent-dim')
                }
              },
              markLine: {
                silent: true,
                symbol: 'none',
                lineStyle: { type: 'dashed', width: 1 },
                label: {
                  fontSize: 10,
                  fontFamily: "'JetBrains Mono', monospace"
                },
                data: [
                  {
                    yAxis: 30,
                    lineStyle: { color: ChartHelpers.getColor('amber') },
                    label: {
                      formatter: '30d',
                      position: 'end',
                      color: ChartHelpers.getColor('amber')
                    }
                  },
                  {
                    yAxis: 90,
                    lineStyle: { color: ChartHelpers.getColor('red') },
                    label: {
                      formatter: '90d',
                      position: 'end',
                      color: ChartHelpers.getColor('red')
                    }
                  }
                ]
              }
            }
          ]
        });

        // Click handler: open Jira ticket
        scatterChart.on('click', function(params) {
          if (params.data && params.data.jiraId) {
            window.open('https://wandb.atlassian.net/browse/' + params.data.jiraId, '_blank');
          }
        });
      }

      // =========================================================
      // CHART 4: Top Submitters Stacked Bars
      // =========================================================
      var submittersContainer = container.querySelector('#chart-submitters');
      if (submittersContainer && data.top_submitters && data.top_submitters.length > 0) {
        var submittersChart = ChartHelpers.createChart(submittersContainer);
        charts.push(submittersChart);

        // Collect all unique concerns across submitters
        var allConcerns = {};
        data.top_submitters.forEach(function(s) {
          (s.concerns || []).forEach(function(c) {
            allConcerns[c.concern] = true;
          });
        });
        var concernKeys = Object.keys(allConcerns);

        var colorPalette = [
          ChartHelpers.getColor('accent'),
          ChartHelpers.getColor('blue'),
          ChartHelpers.getColor('green'),
          ChartHelpers.getColor('amber'),
          ChartHelpers.getColor('red'),
          ChartHelpers.getColor('orange') || '#fb923c'
        ];

        // Y-axis: submitter names (reversed for top-first display)
        var submitterNames = data.top_submitters.map(function(s) { return s.name; }).reverse();

        var stackedSeries = concernKeys.map(function(concern, idx) {
          return {
            name: humanizeConcern(concern),
            type: 'bar',
            stack: 'total',
            barWidth: 24,
            itemStyle: {
              color: colorPalette[idx % colorPalette.length],
              borderRadius: 0
            },
            emphasis: {
              itemStyle: {
                shadowBlur: 8,
                shadowColor: 'rgba(0,0,0,0.3)'
              }
            },
            data: data.top_submitters.map(function(s) {
              var found = (s.concerns || []).filter(function(c) {
                return c.concern === concern;
              });
              return found.length > 0 ? found[0].count : 0;
            }).reverse()
          };
        });

        // Add total count label on the rightmost bar
        if (stackedSeries.length > 0) {
          stackedSeries[stackedSeries.length - 1].label = {
            show: true,
            position: 'right',
            formatter: function(params) {
              // Sum all series values for this data index
              var sum = 0;
              data.top_submitters.forEach(function(s) {
                if (s.name === submitterNames[params.dataIndex]) {
                  sum = s.count;
                }
              });
              return sum;
            },
            color: ChartHelpers.getColor('text-secondary'),
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 11,
            fontWeight: 600
          };
        }

        submittersChart.setOption({
          tooltip: Object.assign({}, ChartHelpers.tooltipConfig(), {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            formatter: function(params) {
              var header = '<div style="font-weight:600;margin-bottom:6px">' + params[0].axisValue + '</div>';
              var rows = '';
              var sum = 0;
              params.forEach(function(p) {
                if (p.value > 0) {
                  sum += p.value;
                  rows += '<div style="display:flex;align-items:center;gap:6px;margin:2px 0">' +
                    '<span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:' + p.color + '"></span>' +
                    '<span>' + p.seriesName + '</span>' +
                    '<span style="margin-left:auto;font-weight:600">' + p.value + '</span></div>';
                }
              });
              return header + '<div style="margin-bottom:4px;color:' + ChartHelpers.getColor('accent') + '">' + sum + ' total</div>' + rows;
            }
          }),
          grid: { left: 130, right: 40, top: 12, bottom: 24 },
          xAxis: {
            type: 'value',
            axisLabel: ChartHelpers.axisLabelConfig(),
            axisLine: { show: false },
            axisTick: { show: false },
            splitLine: ChartHelpers.gridLine()
          },
          yAxis: {
            type: 'category',
            data: submitterNames,
            axisLabel: Object.assign({}, ChartHelpers.axisLabelConfig(), {
              fontFamily: "'Outfit', system-ui, sans-serif",
              fontSize: 13,
              fontWeight: 400,
              color: ChartHelpers.getColor('text-primary')
            }),
            axisLine: { show: false },
            axisTick: { show: false }
          },
          series: stackedSeries
        });
      }

      // =========================================================
      // CHART 5: Submitter-Concern Heatmap
      // =========================================================
      var heatmapContainer = container.querySelector('#chart-heatmap');
      if (heatmapContainer && data.top_submitters && data.top_submitters.length > 0) {
        var heatmapChart = ChartHelpers.createChart(heatmapContainer);
        charts.push(heatmapChart);

        // Collect unique concerns
        var hmConcerns = {};
        data.top_submitters.forEach(function(s) {
          (s.concerns || []).forEach(function(c) {
            hmConcerns[c.concern] = true;
          });
        });
        var hmConcernKeys = Object.keys(hmConcerns);
        var hmConcernLabels = hmConcernKeys.map(humanizeConcern);
        var hmNames = data.top_submitters.map(function(s) { return s.name; });

        // Build heatmap data: [concernIdx, submitterIdx, count]
        var hmData = [];
        var hmMax = 0;
        data.top_submitters.forEach(function(s, si) {
          hmConcernKeys.forEach(function(concern, ci) {
            var found = (s.concerns || []).filter(function(c) {
              return c.concern === concern;
            });
            var val = found.length > 0 ? found[0].count : 0;
            hmData.push([ci, si, val]);
            if (val > hmMax) hmMax = val;
          });
        });

        heatmapChart.setOption({
          tooltip: Object.assign({}, ChartHelpers.tooltipConfig(), {
            position: 'top',
            formatter: function(params) {
              if (params.value[2] === 0) return '';
              return '<div style="font-weight:600">' + hmNames[params.value[1]] + '</div>' +
                '<div>' + hmConcernLabels[params.value[0]] + ': ' + params.value[2] +
                ' ticket' + (params.value[2] !== 1 ? 's' : '') + '</div>';
            }
          }),
          grid: { left: 130, right: 24, top: 12, bottom: 80 },
          xAxis: {
            type: 'category',
            data: hmConcernLabels,
            position: 'bottom',
            axisLabel: Object.assign({}, ChartHelpers.axisLabelConfig(), {
              rotate: 35,
              interval: 0,
              fontFamily: "'Outfit', system-ui, sans-serif",
              fontSize: 11,
              fontWeight: 400,
              color: ChartHelpers.getColor('text-secondary')
            }),
            axisLine: { show: false },
            axisTick: { show: false }
          },
          yAxis: {
            type: 'category',
            data: hmNames,
            axisLabel: Object.assign({}, ChartHelpers.axisLabelConfig(), {
              fontFamily: "'Outfit', system-ui, sans-serif",
              fontSize: 12,
              fontWeight: 400,
              color: ChartHelpers.getColor('text-primary')
            }),
            axisLine: { show: false },
            axisTick: { show: false }
          },
          visualMap: {
            min: 0,
            max: Math.max(hmMax, 1),
            calculable: false,
            orient: 'horizontal',
            left: 'center',
            bottom: 0,
            inRange: {
              color: [
                ChartHelpers.getColor('blue-dim') || 'rgba(96, 165, 250, 0.10)',
                ChartHelpers.getColor('blue')
              ]
            },
            textStyle: {
              color: ChartHelpers.getColor('text-tertiary'),
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 10
            }
          },
          series: [{
            type: 'heatmap',
            data: hmData,
            label: {
              show: true,
              formatter: function(p) {
                return p.value[2] > 0 ? String(p.value[2]) : '';
              },
              color: ChartHelpers.getColor('text-primary'),
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 12,
              fontWeight: 600
            },
            itemStyle: {
              borderColor: ChartHelpers.getColor('bg-elevated') || '#141820',
              borderWidth: 3,
              borderRadius: 4
            },
            emphasis: {
              itemStyle: {
                shadowBlur: 8,
                shadowColor: ChartHelpers.getColor('accent-dim')
              }
            }
          }]
        });
      }

      return { charts: charts };
    },

    getHeadlineStats: function(data) {
      var total = data.total || 0;
      var activeTickets = (data.recent_tickets || []).filter(function(t) {
        return t.status !== 'closed' && t.status !== 'solved';
      });
      var activeCount = activeTickets.length;
      var closedCount = (data.by_status && data.by_status.closed) || 0;
      var solvedCount = (data.by_status && data.by_status.solved) || 0;
      var resolvedPct = total > 0 ? Math.round((closedCount + solvedCount) / total * 100) : 0;

      return [
        { label: 'Tickets (12mo)', value: String(total), color: 'var(--text-primary)' },
        { label: 'Active', value: String(activeCount), color: 'var(--amber)' },
        { label: 'Resolved', value: resolvedPct + '%', color: 'var(--green)' }
      ];
    },

    getAttentionItems: function(data) {
      var items = [];
      var recentTickets = data.recent_tickets || [];

      // Stale tickets (90+ days, not closed/solved)
      var staleTickets = recentTickets.filter(function(t) {
        if (t.status === 'closed' || t.status === 'solved') return false;
        return ChartHelpers.daysBetween(t.created_at) > 90;
      });
      if (staleTickets.length > 0) {
        items.push({
          severity: 'high',
          text: staleTickets.length + ' ticket' + (staleTickets.length !== 1 ? 's' : '') + ' stale 90+ days',
          action: { panel: 'support', filter: 'stale' }
        });
      }

      // Urgent priority tickets
      var urgentTickets = recentTickets.filter(function(t) {
        if (t.status === 'closed' || t.status === 'solved') return false;
        return (t.priority || '').toLowerCase() === 'urgent';
      });
      if (urgentTickets.length > 0) {
        items.push({
          severity: 'high',
          text: urgentTickets.length + ' urgent ticket' + (urgentTickets.length !== 1 ? 's' : '') + ' open',
          action: { panel: 'support', filter: 'urgent' }
        });
      }

      // Low resolution rate
      var total = data.total || 0;
      var closedCount = (data.by_status && data.by_status.closed) || 0;
      var solvedCount = (data.by_status && data.by_status.solved) || 0;
      if (total > 0) {
        var resolvedPct = Math.round((closedCount + solvedCount) / total * 100);
        if (resolvedPct < 50) {
          items.push({
            severity: 'medium',
            text: 'Low resolution rate (' + resolvedPct + '%)',
            action: { panel: 'support' }
          });
        }
      }

      return items;
    }
  });

})();
