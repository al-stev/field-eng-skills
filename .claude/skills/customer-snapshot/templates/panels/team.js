/**
 * Team Detection Panel — Dashboard V2
 *
 * Three visualizations:
 *   1. Team Breakdown table with member counts and top product areas
 *   2. Team Activity horizontal bar chart
 *   3. Product Adoption by Team heatmap
 *
 * Three-tier data status:
 *   - "available": full rendering with real team names
 *   - "names_unavailable": charts shown with anonymized names + banner
 *   - "unavailable": full empty state
 *
 * Registers with PanelRegistry. No ES module syntax.
 */
(function() {
  'use strict';

  // --- Dark mode detection ---
  function isDark() {
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  }

  // --- CSS (auto-scoped by shell via #panel-team prefix) ---
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
.team-table {\
  width: 100%;\
  border-collapse: collapse;\
}\
.team-table th {\
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
.team-table td {\
  font-family: "Outfit", system-ui, sans-serif;\
  font-size: 14px;\
  font-weight: 400;\
  padding: 10px 12px;\
  border-bottom: 1px solid var(--border-subtle);\
  vertical-align: middle;\
}\
.team-table tr:hover {\
  background: var(--bg-hover);\
}\
.team-table tr:last-child td {\
  border-bottom: none;\
}\
.team-anon-banner {\
  background: var(--amber-dim);\
  border: 1px solid var(--amber-border);\
  border-radius: 6px;\
  padding: 12px 16px;\
  margin-bottom: 24px;\
  font-family: "Outfit", system-ui, sans-serif;\
  font-size: 14px;\
  color: var(--amber);\
}\
.team-product-tag {\
  display: inline-block;\
  padding: 2px 8px;\
  border-radius: 10px;\
  font-family: "JetBrains Mono", monospace;\
  font-size: 11px;\
  font-weight: 400;\
  color: var(--text-tertiary);\
  background: var(--bg-surface);\
  margin: 1px 2px;\
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
   * Escape HTML entities.
   */
  function esc(str) {
    if (!str) return '';
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  // --- REGISTRATION ---
  PanelRegistry.register({
    id: 'team',
    group: 'user-intel',
    label: 'Team Detection',
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>',
    dataKey: 'analytics.team',

    render: function(container, data, config) {
      var charts = [];

      // CSS injection guard
      if (!document.querySelector('style[data-panel="team"]')) {
        if (typeof PanelRegistry.injectCSS === 'function') {
          PanelRegistry.injectCSS('team', PANEL_CSS);
        }
      }

      // --- Empty state: no data at all ---
      if (!data || !data.available) {
        container.innerHTML =
          '<div class="placeholder-panel">' +
            '<div class="placeholder-icon">' +
              '<svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="var(--text-tertiary)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">' +
                '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>' +
                '<circle cx="9" cy="7" r="4"></circle>' +
                '<path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>' +
                '<path d="M16 3.13a4 4 0 0 1 0 7.75"></path>' +
              '</svg>' +
            '</div>' +
            '<div class="placeholder-title">Team Detection</div>' +
            '<div class="placeholder-desc">Team data not available. For dedicated cloud deployments, telemetry is anonymized and does not include team or entity fields.</div>' +
          '</div>';
        return { charts: [] };
      }

      // --- Three-tier team_data_status handling ---
      var status = data.team_data_status || 'available';

      // Full empty state for "unavailable"
      if (status === 'unavailable') {
        container.innerHTML =
          '<div class="placeholder-panel">' +
            '<div class="placeholder-icon">' +
              '<svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="var(--text-tertiary)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">' +
                '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>' +
                '<circle cx="9" cy="7" r="4"></circle>' +
                '<path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>' +
                '<path d="M16 3.13a4 4 0 0 1 0 7.75"></path>' +
              '</svg>' +
            '</div>' +
            '<div class="placeholder-title">Team Detection</div>' +
            '<div class="placeholder-desc">Team data not available. For dedicated cloud deployments, telemetry is anonymized and does not include team or entity fields.</div>' +
          '</div>';
        return { charts: [] };
      }

      // --- Banner for "names_unavailable" ---
      var bannerHtml = '';
      if (status === 'names_unavailable') {
        bannerHtml = '<div class="team-anon-banner">' +
          'Team names are anonymized for this deployment type. Activity patterns are still visible.' +
        '</div>';
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

      // --- Team Breakdown Table ---
      var teams = data.teams || [];
      var champions = data.champions || null;

      // Build champion lookup by team name
      var champByTeam = {};
      if (champions && Array.isArray(champions)) {
        for (var c = 0; c < champions.length; c++) {
          var ch = champions[c];
          var tName = ch.team || '';
          if (!champByTeam[tName]) champByTeam[tName] = [];
          champByTeam[tName].push(ch);
        }
      }

      var tableHtml = '<div class="full-width">' +
        '<div class="section-label">Team Breakdown</div>' +
        '<div class="panel-card" style="overflow-x:auto;">' +
          '<table class="team-table">' +
            '<thead><tr>' +
              '<th>Team</th>' +
              '<th style="text-align:right">Members</th>' +
              '<th style="text-align:right">Events</th>' +
              '<th style="text-align:right">Last Active</th>' +
              '<th>Top Product Areas</th>' +
            '</tr></thead>' +
            '<tbody>';

      for (var t = 0; t < teams.length; t++) {
        var team = teams[t];
        var teamName = esc(team.name || 'Unknown');
        // Support both top_product_areas (array) and top_product (string)
        var productAreas = team.top_product_areas || (team.top_product ? [team.top_product] : []);
        productAreas = productAreas.slice(0, 4);
        var productHtml = productAreas.map(function(pa) {
          return '<span class="team-product-tag">' + esc(pa) + '</span>';
        }).join(' ');
        if (productAreas.length === 0) productHtml = '<span style="color:var(--text-tertiary)">--</span>';

        // Add champion info if available
        var champInfo = '';
        var teamChamps = champByTeam[team.name] || [];
        if (teamChamps.length > 0) {
          var champNames = teamChamps.slice(0, 2).map(function(ch) {
            return esc(ch.display_name || ch.username || 'Unknown');
          }).join(', ');
          if (teamChamps.length > 2) champNames += ' +' + (teamChamps.length - 2);
          champInfo = '<div style="font-size:12px;font-weight:400;color:var(--text-tertiary);margin-top:2px;">' +
            'Top: ' + champNames + '</div>';
        }

        // Add member names if available
        var memberInfo = '';
        if (team.members && Array.isArray(team.members) && team.members.length > 0) {
          var memberNames = team.members.slice(0, 5).join(', ');
          if (team.members.length > 5) memberNames += ' +' + (team.members.length - 5) + ' more';
          memberInfo = '<div style="font-size:12px;font-weight:400;color:var(--text-tertiary);margin-top:2px;">' + esc(memberNames) + '</div>';
        }

        tableHtml += '<tr>' +
          '<td style="font-weight:500;color:var(--text-primary)">' + teamName + champInfo + memberInfo + '</td>' +
          '<td style="text-align:right;color:var(--text-secondary)">' + fmt(team.member_count) + '</td>' +
          '<td style="text-align:right;color:var(--text-secondary)">' + fmt(team.total_events) + '</td>' +
          '<td style="text-align:right;color:var(--text-secondary);font-family:JetBrains Mono,monospace;font-size:11px;">' + esc(team.last_active || (team.active_days != null ? fmt(team.active_days) + 'd' : '--')) + '</td>' +
          '<td>' + productHtml + '</td>' +
        '</tr>';
      }

      tableHtml += '</tbody></table></div></div>';

      // --- Chart containers ---
      var chartsHtml =
        '<div class="two-col">' +
          '<div>' +
            '<div class="section-label">Team Activity</div>' +
            '<div class="panel-card">' +
              '<div id="team-activity-chart" style="width:100%;height:320px;"></div>' +
            '</div>' +
          '</div>' +
          '<div>' +
            '<div class="section-label">Product Adoption by Team</div>' +
            '<div class="panel-card">' +
              '<div id="team-heatmap-chart" style="width:100%;height:400px;"></div>' +
            '</div>' +
          '</div>' +
        '</div>';

      container.innerHTML = bannerHtml + kpiHtml + tableHtml + chartsHtml;

      // --- Team Activity horizontal bar chart ---
      setTimeout(function() {
        var actEl = container.querySelector('#team-activity-chart');
        if (!actEl) return;
        var actChart = ChartHelpers.createChart(actEl);

        // Normalize team_activity: supports both array of {team, events, users}
        // and object {team_names, events, users} (parallel arrays from transform)
        var rawTA = data.team_activity || [];
        var teamNames, events, users;
        if (Array.isArray(rawTA)) {
          teamNames = rawTA.map(function(d) { return d.team; }).reverse();
          events = rawTA.map(function(d) { return d.events; }).reverse();
          users = rawTA.map(function(d) { return d.users; }).reverse();
        } else if (rawTA.team_names) {
          teamNames = (rawTA.team_names || []).slice().reverse();
          events = (rawTA.events || []).slice().reverse();
          users = (rawTA.users || []).slice().reverse();
        } else {
          teamNames = []; events = []; users = [];
        }

        actChart.setOption({
          tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            formatter: function(params) {
              var html = '<strong>' + params[0].axisValue + '</strong>';
              params.forEach(function(p) {
                html += '<br/>' + p.marker + ' ' + p.seriesName + ': ' + (p.value || 0).toLocaleString();
              });
              return html;
            }
          },
          legend: {
            data: ['Events', 'Users'],
            bottom: 0,
            textStyle: {
              color: isDark() ? '#8b92a0' : '#5c5c5c',
              fontSize: 11,
              fontFamily: 'JetBrains Mono, monospace'
            },
            itemWidth: 12,
            itemHeight: 12
          },
          grid: { left: 120, right: 24, top: 16, bottom: 40 },
          xAxis: {
            type: 'value',
            axisLabel: {
              color: isDark() ? '#5c6370' : '#8c8c8c',
              fontSize: 11,
              formatter: function(v) { return v >= 1000 ? (v / 1000).toFixed(0) + 'k' : v; }
            },
            splitLine: { lineStyle: { color: isDark() ? '#1e2430' : '#e0ded9', type: 'dashed' } }
          },
          yAxis: {
            type: 'category',
            data: teamNames,
            axisLabel: {
              color: isDark() ? '#e8eaed' : '#1a1a1a',
              fontSize: 12,
              fontFamily: 'Outfit, sans-serif',
              width: 100,
              overflow: 'truncate'
            },
            axisLine: { lineStyle: { color: isDark() ? '#1e2430' : '#e0ded9' } },
            axisTick: { show: false }
          },
          series: [
            {
              name: 'Events',
              type: 'bar',
              data: events,
              itemStyle: { color: isDark() ? '#60a5fa' : '#3b82f6', borderRadius: [0, 3, 3, 0] },
              barMaxWidth: 18
            },
            {
              name: 'Users',
              type: 'bar',
              data: users,
              itemStyle: { color: isDark() ? '#4ade80' : '#22c55e', borderRadius: [0, 3, 3, 0] },
              barMaxWidth: 18
            }
          ]
        });
        charts.push(actChart);
      }, 10);

      // --- Product Adoption by Team heatmap ---
      setTimeout(function() {
        var hmEl = container.querySelector('#team-heatmap-chart');
        if (!hmEl) return;
        var hmChart = ChartHelpers.createChart(hmEl);
        var rawHeat = data.team_product_heatmap || [];

        // Normalize: supports both array of {team, product_area, events}
        // and object {team_names, product_areas, matrix} from transform
        var productAreas, hmTeams, matrixData;
        var maxEvents = 0;

        if (Array.isArray(rawHeat)) {
          // Original expected format
          var productSet = {};
          var teamSet = {};
          for (var h = 0; h < rawHeat.length; h++) {
            productSet[rawHeat[h].product_area] = true;
            teamSet[rawHeat[h].team] = true;
          }
          productAreas = Object.keys(productSet);
          hmTeams = Object.keys(teamSet);
          matrixData = [];
          for (var m = 0; m < rawHeat.length; m++) {
            var pIdx = productAreas.indexOf(rawHeat[m].product_area);
            var tIdx = hmTeams.indexOf(rawHeat[m].team);
            var evts = rawHeat[m].events || 0;
            if (evts > maxEvents) maxEvents = evts;
            matrixData.push([pIdx, tIdx, evts]);
          }
        } else if (rawHeat.team_names && rawHeat.product_areas && rawHeat.matrix) {
          // Transform format: {team_names, product_areas, matrix: [[teamIdx, productIdx, events]]}
          hmTeams = rawHeat.team_names || [];
          productAreas = rawHeat.product_areas || [];
          matrixData = [];
          var rawMatrix = rawHeat.matrix || [];
          for (var rm = 0; rm < rawMatrix.length; rm++) {
            var entry = rawMatrix[rm];
            var eVal = entry[2] || 0;
            if (eVal > maxEvents) maxEvents = eVal;
            // Transform matrix is [teamIdx, productIdx, events], chart needs [productIdx, teamIdx, events]
            matrixData.push([entry[1], entry[0], eVal]);
          }
        } else {
          productAreas = []; hmTeams = []; matrixData = [];
        }

        hmChart.setOption({
          tooltip: {
            position: 'top',
            formatter: function(p) {
              var val = p.value || p.data;
              var teamName = hmTeams[val[1]] || 'Unknown';
              var prodArea = productAreas[val[0]] || 'Unknown';
              var count = val[2] || 0;
              return '<strong>' + teamName + '</strong><br/>' +
                prodArea + ': ' + count.toLocaleString() + ' events';
            }
          },
          grid: { left: 120, right: 60, top: 8, bottom: 56 },
          xAxis: {
            type: 'category',
            data: productAreas,
            position: 'bottom',
            axisLabel: {
              color: isDark() ? '#5c6370' : '#8c8c8c',
              fontSize: 10,
              fontFamily: 'JetBrains Mono, monospace',
              rotate: productAreas.length > 5 ? 30 : 0
            },
            axisLine: { lineStyle: { color: isDark() ? '#1e2430' : '#e0ded9' } },
            axisTick: { show: false }
          },
          yAxis: {
            type: 'category',
            data: hmTeams,
            axisLabel: {
              color: isDark() ? '#e8eaed' : '#1a1a1a',
              fontSize: 11,
              fontFamily: 'Outfit, sans-serif',
              width: 100,
              overflow: 'truncate'
            },
            axisLine: { lineStyle: { color: isDark() ? '#1e2430' : '#e0ded9' } },
            axisTick: { show: false }
          },
          visualMap: {
            type: 'continuous',
            min: 0,
            max: maxEvents || 1,
            calculable: true,
            orient: 'horizontal',
            left: 'center',
            bottom: 0,
            itemWidth: 12,
            itemHeight: 80,
            textStyle: { color: isDark() ? '#5c6370' : '#8c8c8c', fontSize: 10 },
            inRange: {
              color: ['rgba(96,165,250,0.08)', '#60a5fa']
            }
          },
          series: [{
            type: 'heatmap',
            data: matrixData,
            label: {
              show: true,
              fontSize: 10,
              color: isDark() ? '#e8eaed' : '#1a1a1a',
              formatter: function(p) {
                var val = p.value || p.data;
                var count = val[2] || 0;
                if (count === 0) return '';
                return count >= 1000 ? (count / 1000).toFixed(1) + 'k' : count;
              }
            },
            emphasis: {
              itemStyle: { shadowBlur: 8, shadowColor: 'rgba(0,0,0,0.3)' }
            }
          }]
        });
        charts.push(hmChart);
      }, 20);

      return { charts: charts };
    },

    getHeadlineStats: function(data) {
      if (!data || !data.available) return [];
      var teamCount = data.teams ? data.teams.length : 0;
      var status = data.team_data_status || 'available';
      var statusLabel = status === 'available' ? 'Full' : status === 'names_unavailable' ? 'Anonymized' : 'N/A';
      var statusColor = status === 'available' ? 'var(--green)' : 'var(--amber)';

      return [
        { label: 'Teams', value: String(teamCount), color: 'var(--text-primary)' },
        { label: 'Team Status', value: statusLabel, color: statusColor }
      ];
    },

    getAttentionItems: function(data) {
      if (!data || !data.available) return [];
      var items = [];
      var teams = data.teams || [];

      for (var i = 0; i < teams.length; i++) {
        var team = teams[i];
        if (team.member_count === 1 && (team.total_events || 0) > 100) {
          items.push({
            severity: 'low',
            text: 'Team "' + (team.name || 'Unknown') + '" has only 1 member but high activity -- expansion opportunity',
            action: { panel: 'team' }
          });
        }
      }

      return items;
    }
  });
})();
