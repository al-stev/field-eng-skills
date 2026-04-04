/**
 * SDK Versions Panel — Dashboard V2
 *
 * Four visualization sections:
 *   1. Version Distribution — donut chart + freshness assessment bar
 *   2. Freshness Assessment — stacked freshness bar with category counts
 *   3. Version Trend — stacked area chart over time
 *   4. Upgrade Recommendations — actionable table of users on stale SDKs
 *
 * Data shape: analytics.sdk_versions from SdkVersionsTransform
 *   { available, donut[], timeline[], versions[], version_table[],
 *     freshness_summary{}, latest_version, snapshot_month, kpis[], narrative }
 *
 * Registers with PanelRegistry. No ES module syntax.
 */
(function() {
  'use strict';

  // --- CSS (auto-scoped by shell via #panel-sdk-versions prefix) ---
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
.freshness-bar {\
  display: flex;\
  height: 24px;\
  border-radius: 4px;\
  overflow: hidden;\
  margin-bottom: 16px;\
}\
.freshness-segment {\
  display: flex;\
  align-items: center;\
  justify-content: center;\
  font-family: "JetBrains Mono", monospace;\
  font-size: 11px;\
  font-weight: 600;\
  color: #fff;\
}\
.freshness-current { background: var(--green); }\
.freshness-recent { background: var(--blue); }\
.freshness-stale { background: var(--amber); }\
.freshness-ancient { background: var(--red); }\
.freshness-stat {\
  display: flex;\
  align-items: center;\
  gap: 8px;\
  padding: 8px 0;\
}\
.freshness-dot {\
  width: 10px;\
  height: 10px;\
  border-radius: 50%;\
  flex-shrink: 0;\
}\
.freshness-stat-label {\
  font-family: "Outfit", system-ui, sans-serif;\
  font-size: 14px;\
  font-weight: 400;\
  color: var(--text-secondary);\
  flex: 1;\
}\
.freshness-stat-value {\
  font-family: "JetBrains Mono", monospace;\
  font-size: 14px;\
  font-weight: 600;\
  color: var(--text-primary);\
}\
.upgrade-table {\
  width: 100%;\
  border-collapse: collapse;\
}\
.upgrade-table th {\
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
.upgrade-table td {\
  padding: 8px 12px;\
  border-bottom: 1px solid var(--border-subtle);\
  font-family: "Outfit", system-ui, sans-serif;\
  font-size: 14px;\
}\
.upgrade-table tr:hover {\
  background: var(--bg-hover);\
}\
.freshness-badge {\
  display: inline-block;\
  padding: 2px 8px;\
  border-radius: 10px;\
  font-family: "JetBrains Mono", monospace;\
  font-size: 11px;\
  font-weight: 600;\
}\
.show-all-toggle {\
  cursor: pointer;\
  font-family: "JetBrains Mono", monospace;\
  font-size: 11px;\
  font-weight: 600;\
  color: var(--text-secondary);\
  margin-top: 12px;\
  display: inline-block;\
  user-select: none;\
}\
.show-all-toggle:hover {\
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

  function isDark() {
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  }

  /** Freshness color mapping using CSS variables. */
  var FRESHNESS_COLORS = {
    current: 'var(--green)',
    recent: 'var(--blue)',
    stale: 'var(--amber)',
    ancient: 'var(--red)'
  };

  var FRESHNESS_DIM = {
    current: 'var(--green-dim)',
    recent: 'var(--blue-dim)',
    stale: 'var(--amber-dim)',
    ancient: 'var(--red-dim)'
  };

  var FRESHNESS_BORDER = {
    current: 'var(--green-border)',
    recent: 'var(--blue-border)',
    stale: 'var(--amber-border)',
    ancient: 'var(--red-border)'
  };

  /** Resolve CSS variable to actual color for ECharts. */
  function resolveColor(cssVar) {
    if (!cssVar || cssVar.indexOf('var(') !== 0) return cssVar;
    var varName = cssVar.replace('var(', '').replace(')', '');
    return getComputedStyle(document.documentElement).getPropertyValue(varName).trim() || cssVar;
  }

  /** Freshness sort order (ancient first for upgrade table). */
  var FRESHNESS_ORDER = { ancient: 0, stale: 1, recent: 2, current: 3 };

  function freshnessBadge(level) {
    var color = FRESHNESS_COLORS[level] || 'var(--text-tertiary)';
    var dim = FRESHNESS_DIM[level] || 'var(--bg-surface)';
    var border = FRESHNESS_BORDER[level] || 'var(--border-subtle)';
    var label = (level || 'unknown').charAt(0).toUpperCase() + (level || 'unknown').slice(1);
    return '<span class="freshness-badge" style="color:' + color + ';background:' + dim + ';border:1px solid ' + border + ';">' + label + '</span>';
  }

  // --- SQL COPY BUTTON ---

  var SQL_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"></ellipse><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path></svg>';

  function sqlCopyBtn(queryKey) {
    return '<span class="sql-copy-btn" data-query-key="' + queryKey + '" title="Copy SQL query to clipboard" aria-label="Copy SQL query">' + SQL_ICON + '</span>';
  }

  // --- REGISTRATION ---
  PanelRegistry.register({
    id: 'sdk-versions',
    group: 'product-intel',
    label: 'SDK Versions',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="16.5" y1="9.4" x2="7.5" y2="4.21"></line><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline><line x1="12" y1="22.08" x2="12" y2="12"></line></svg>',
    badgeKey: 'stale_count',
    dataKey: 'analytics.sdk_versions',

    render: function(container, data, config) {
      var charts = [];
      var cssInjected = document.querySelector('style[data-panel="sdk-versions"]');

      // Inject CSS once
      if (!cssInjected && typeof PanelRegistry.injectCSS === 'function') {
        PanelRegistry.injectCSS('sdk-versions', PANEL_CSS);
      }

      // Empty state
      if (!data || !data.available) {
        container.innerHTML = '<div class="placeholder-panel">' +
          '<div class="placeholder-icon">' +
          '<svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="var(--text-tertiary)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">' +
          '<line x1="16.5" y1="9.4" x2="7.5" y2="4.21"></line>' +
          '<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>' +
          '<polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline>' +
          '<line x1="12" y1="22.08" x2="12" y2="12"></line></svg></div>' +
          '<div class="placeholder-title">SDK Versions</div>' +
          '<div class="placeholder-desc">No SDK version data available. This requires cli_version or local_version fields in usage events.</div>' +
          '</div>';
        return { charts: [] };
      }

      var donutData = data.donut || [];
      var timeline = data.timeline || [];
      var versions = data.versions || [];
      var versionTable = data.version_table || [];
      var freshness = data.freshness_summary || {};
      var kpis = data.kpis || [];
      var snapshotMonth = data.snapshot_month || '';

      // Total users for freshness bar percentages
      var totalUsers = (freshness.current || 0) + (freshness.recent || 0) +
        (freshness.stale || 0) + (freshness.ancient || 0);
      if (totalUsers === 0) totalUsers = 1; // Avoid division by zero

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

      // --- Version Distribution section (two-col: donut + freshness) ---
      var distHtml = '<div class="two-col">' +
        '<div class="panel-card">' +
        '<div class="section-label">VERSION DISTRIBUTION</div>' +
        '<div id="sdk-donut-chart" style="width:100%;height:300px;"></div>' +
        '</div>' +
        '<div class="panel-card">' +
        '<div class="section-label">FRESHNESS ASSESSMENT</div>' +
        '<div class="freshness-bar">';

      // Build freshness bar segments
      var categories = ['current', 'recent', 'stale', 'ancient'];
      categories.forEach(function(cat) {
        var count = freshness[cat] || 0;
        if (count > 0) {
          var pct = Math.round(count / totalUsers * 100);
          distHtml += '<div class="freshness-segment freshness-' + cat + '" style="width:' +
            pct + '%;">' + (pct >= 8 ? pct + '%' : '') + '</div>';
        }
      });

      distHtml += '</div>';

      // Freshness category stats
      categories.forEach(function(cat) {
        var count = freshness[cat] || 0;
        var color = FRESHNESS_COLORS[cat];
        var label = cat.charAt(0).toUpperCase() + cat.slice(1);
        var pct = Math.round(count / totalUsers * 100);
        distHtml += '<div class="freshness-stat">' +
          '<div class="freshness-dot" style="background:' + color + ';"></div>' +
          '<span class="freshness-stat-label">' + label + '</span>' +
          '<span class="freshness-stat-value">' + count + ' user' + (count !== 1 ? 's' : '') +
          ' (' + pct + '%)</span>' +
          '</div>';
      });

      distHtml += '</div></div>';

      // --- Version Trend section ---
      var trendHtml = '<div class="full-width">' +
        '<div class="section-label">VERSION TREND</div>' +
        '<div class="panel-card">' +
        '<div id="sdk-trend-chart" style="width:100%;height:380px;"></div>' +
        '</div></div>';

      // --- Upgrade Recommendations section ---
      var upgradeHtml = '<div class="full-width">' +
        '<div class="section-label">UPGRADE RECOMMENDATIONS</div>' +
        '<div class="panel-card">';

      // Sort version_table by freshness severity (ancient first), then by current_users desc
      var sortedTable = versionTable.slice().sort(function(a, b) {
        var orderA = FRESHNESS_ORDER[a.freshness] != null ? FRESHNESS_ORDER[a.freshness] : 2;
        var orderB = FRESHNESS_ORDER[b.freshness] != null ? FRESHNESS_ORDER[b.freshness] : 2;
        if (orderA !== orderB) return orderA - orderB;
        return (b.current_users || 0) - (a.current_users || 0);
      });

      // Filter to stale/ancient only for upgrade recommendations
      var upgradeRows = sortedTable.filter(function(v) {
        return v.freshness === 'stale' || v.freshness === 'ancient';
      });

      if (upgradeRows.length === 0) {
        upgradeHtml += '<div style="text-align:center;padding:16px;color:var(--text-tertiary);font-size:14px;">' +
          'All users are on current or recent SDK versions. No upgrades needed.</div>';
      } else {
        upgradeHtml += '<table class="upgrade-table">' +
          '<thead><tr>' +
          '<th>Version</th>' +
          '<th>Freshness</th>' +
          '<th>Current Users</th>' +
          '<th>First Seen</th>' +
          '<th>Last Seen</th>' +
          '</tr></thead><tbody>';

        var showLimit = 15;
        var visibleRows = upgradeRows.slice(0, showLimit);
        var hiddenRows = upgradeRows.slice(showLimit);

        visibleRows.forEach(function(v) {
          upgradeHtml += '<tr>' +
            '<td style="font-family:JetBrains Mono,monospace;font-weight:600;color:var(--text-primary);">' + v.version + '</td>' +
            '<td>' + freshnessBadge(v.freshness) + '</td>' +
            '<td style="color:var(--text-primary);">' + (v.current_users || 0) + '</td>' +
            '<td style="color:var(--text-secondary);">' + (v.first_seen || '') + '</td>' +
            '<td style="color:var(--text-secondary);">' + (v.last_seen || '') + '</td>' +
            '</tr>';
        });

        if (hiddenRows.length > 0) {
          hiddenRows.forEach(function(v) {
            upgradeHtml += '<tr class="sdk-hidden-row" style="display:none;">' +
              '<td style="font-family:JetBrains Mono,monospace;font-weight:600;color:var(--text-primary);">' + v.version + '</td>' +
              '<td>' + freshnessBadge(v.freshness) + '</td>' +
              '<td style="color:var(--text-primary);">' + (v.current_users || 0) + '</td>' +
              '<td style="color:var(--text-secondary);">' + (v.first_seen || '') + '</td>' +
              '<td style="color:var(--text-secondary);">' + (v.last_seen || '') + '</td>' +
              '</tr>';
          });
        }

        upgradeHtml += '</tbody></table>';

        if (hiddenRows.length > 0) {
          upgradeHtml += '<div class="show-all-toggle" id="sdk-show-all-toggle">' +
            'Show all ' + upgradeRows.length + ' versions</div>';
        }
      }

      upgradeHtml += '</div></div>';

      // Assemble full HTML
      container.innerHTML = kpiHtml + periodHtml + distHtml + trendHtml + upgradeHtml;

      // --- Wire up show-all toggle ---
      var toggle = container.querySelector('#sdk-show-all-toggle');
      if (toggle) {
        toggle.addEventListener('click', function() {
          var rows = container.querySelectorAll('.sdk-hidden-row');
          var showing = toggle.getAttribute('data-showing') === 'true';
          for (var i = 0; i < rows.length; i++) {
            rows[i].style.display = showing ? 'none' : '';
          }
          toggle.textContent = showing
            ? 'Show all ' + upgradeRows.length + ' versions'
            : 'Show fewer';
          toggle.setAttribute('data-showing', String(!showing));
        });
      }

      // --- Render donut chart ---
      var donutEl = container.querySelector('#sdk-donut-chart');
      if (donutEl && donutData.length > 0) {
        var donutChart = ChartHelpers.createChart(donutEl);
        var chartData = donutData.map(function(d) {
          return {
            name: d.version + ' (' + d.pct + '%)',
            value: d.users,
            itemStyle: { color: resolveColor(FRESHNESS_COLORS[d.freshness] || 'var(--text-tertiary)') }
          };
        });

        donutChart.setOption({
          tooltip: {
            trigger: 'item',
            formatter: function(p) {
              return '<strong>' + p.name + '</strong><br/>' + p.value + ' users';
            }
          },
          legend: {
            orient: 'vertical',
            right: 8,
            top: 'center',
            textStyle: { fontSize: 11, fontFamily: 'JetBrains Mono, monospace' },
            itemWidth: 12,
            itemHeight: 12,
            itemGap: 6
          },
          series: [{
            type: 'pie',
            radius: ['45%', '70%'],
            center: ['35%', '50%'],
            avoidLabelOverlap: true,
            label: { show: false },
            emphasis: {
              label: {
                show: true,
                fontSize: 14,
                fontWeight: 600,
                fontFamily: 'Outfit, sans-serif'
              },
              itemStyle: {
                shadowBlur: 10,
                shadowOffsetX: 0,
                shadowColor: 'rgba(0, 0, 0, 0.3)'
              }
            },
            data: chartData
          }]
        });
        charts.push(donutChart);
      }

      // --- Render version trend stacked area ---
      var trendEl = container.querySelector('#sdk-trend-chart');
      if (trendEl && timeline.length > 0 && versions.length > 0) {
        var trendChart = ChartHelpers.createChart(trendEl);
        var months = timeline.map(function(t) { return t.month; });

        // Build a version-to-freshness lookup from donut data
        var versionFreshness = {};
        donutData.forEach(function(d) {
          versionFreshness[d.version] = d.freshness;
        });

        // Fallback colors for versions not in donut
        var fallbackColors = ['#9333ea', '#06b6d4', '#ec4899', '#84cc16', '#f97316'];

        var series = versions.map(function(v, i) {
          var freshLevel = versionFreshness[v];
          var color;
          if (freshLevel) {
            color = resolveColor(FRESHNESS_COLORS[freshLevel]);
          } else {
            color = fallbackColors[i % fallbackColors.length];
          }

          return {
            name: v,
            type: 'line',
            stack: 'total',
            areaStyle: {},
            smooth: false,
            symbol: 'none',
            lineStyle: { width: 1 },
            emphasis: { focus: 'series' },
            data: timeline.map(function(t) { return t[v] || 0; }),
            itemStyle: { color: color }
          };
        });

        var trendOption = {
          tooltip: {
            trigger: 'axis',
            formatter: function(params) {
              var html = '<strong>' + params[0].axisValue + '</strong>';
              params.slice().reverse().forEach(function(p) {
                if (p.value > 0) {
                  html += '<br/>' + p.marker + ' ' + p.seriesName + ': ' + p.value + ' users';
                }
              });
              return html;
            }
          },
          legend: {
            data: versions.slice().reverse(),
            bottom: 0,
            type: 'scroll',
            textStyle: { fontSize: 11, fontFamily: 'JetBrains Mono, monospace' },
            itemWidth: 12,
            itemHeight: 12
          },
          grid: { left: 48, right: 16, top: 16, bottom: 60 },
          xAxis: {
            type: 'category',
            data: months,
            axisLabel: {
              fontSize: 11,
              interval: months.length > 12 ? 1 : 0
            },
            axisTick: { show: false }
          },
          yAxis: {
            type: 'value',
            name: 'Users',
            nameTextStyle: { fontSize: 11 },
            axisLabel: { fontSize: 11 },
            splitLine: { lineStyle: { type: 'dashed' } }
          },
          series: series
        };

        // Add dataZoom for 12+ months
        if (months.length >= 12) {
          trendOption.dataZoom = [
            { type: 'inside' },
            { type: 'slider', height: 20, bottom: 24 }
          ];
          trendOption.grid.bottom = 80;
          trendOption.legend.bottom = 48;
        }

        trendChart.setOption(trendOption);
        charts.push(trendChart);
      }

      return { charts: charts };
    },

    getHeadlineStats: function(data) {
      if (!data || !data.available) return [];

      var freshness = data.freshness_summary || {};
      var staleCount = (freshness.stale || 0) + (freshness.ancient || 0);
      var currentCount = freshness.current || 0;

      return [
        {
          label: 'Stale SDKs',
          value: String(staleCount),
          color: staleCount > 0 ? 'var(--amber)' : 'var(--green)'
        },
        {
          label: 'On Current',
          value: String(currentCount),
          color: 'var(--green)'
        }
      ];
    },

    getAttentionItems: function(data) {
      if (!data || !data.available) return [];

      var items = [];
      var freshness = data.freshness_summary || {};

      // Ancient users are high severity
      if ((freshness.ancient || 0) > 0) {
        items.push({
          severity: 'high',
          text: freshness.ancient + ' user(s) on ancient SDK versions',
          action: { panel: 'sdk-versions' }
        });
      }

      // More stale than current is medium severity
      var staleCount = (freshness.stale || 0) + (freshness.ancient || 0);
      var currentCount = freshness.current || 0;
      if (staleCount > currentCount && currentCount > 0) {
        items.push({
          severity: 'medium',
          text: 'More users on stale SDKs than current',
          action: { panel: 'sdk-versions' }
        });
      }

      return items;
    }
  });

})();
