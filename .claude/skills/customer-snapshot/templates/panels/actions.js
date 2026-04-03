/**
 * Actions Panel — Dashboard V2
 *
 * SE Actions panel extracted from v1 intelligence-dashboard.html renderActionsPanel().
 * Renders Asana task table grouped by section with priority badges, overdue flags,
 * stale indicators, Jira cross-links, and scope toggle (my_tasks / team).
 *
 * No ECharts dependency — pure DOM rendering.
 */
(function() {
  'use strict';

  // ── Constants (self-contained, copied from v1) ──

  var ACTIONS_PRIO_ORDER = { 'P0': 0, 'P1': 1, 'P2': 2, 'P3': 3 };

  var ACTIONS_SECTION_COLORS = {
    'In Progress': { bg: 'var(--blue-dim)', color: 'var(--blue)' },
    'To Do': { bg: 'var(--amber-dim)', color: 'var(--amber)' },
    'Waiting on Customer': { bg: 'var(--orange-dim)', color: 'var(--orange)' },
    'Waiting on Eng': { bg: 'var(--orange-dim)', color: 'var(--orange)' },
    'Scheduled/Future': { bg: 'var(--gray-dim)', color: 'var(--gray)' },
    'Done': { bg: 'var(--green-dim)', color: 'var(--green)' }
  };

  // ── Panel CSS ──

  var PANEL_CSS = '\
.section-label {\
  font-family: var(--font-mono);\
  font-size: 11px;\
  font-weight: 600;\
  text-transform: uppercase;\
  letter-spacing: 1.5px;\
  color: var(--text-tertiary);\
  margin-bottom: 16px;\
}\
.actions-header {\
  display: flex;\
  align-items: center;\
  gap: 12px;\
  margin-bottom: 16px;\
}\
.actions-title {\
  font-family: var(--font-mono);\
  font-size: 11px;\
  font-weight: 600;\
  text-transform: uppercase;\
  letter-spacing: 1.5px;\
  color: var(--text-tertiary);\
}\
.actions-count-badge {\
  font-family: var(--font-mono);\
  font-size: 11px;\
  font-weight: 600;\
  color: var(--text-primary);\
  background: var(--bg-hover);\
  padding: 2px 8px;\
  border-radius: 10px;\
}\
.actions-scope-toggle {\
  display: flex;\
  gap: 4px;\
  margin-left: auto;\
}\
.actions-scope-toggle .pill {\
  font-family: var(--font-mono);\
  font-size: 11px;\
  font-weight: 600;\
  color: var(--text-tertiary);\
  background: none;\
  border: 1px solid var(--border-subtle);\
  padding: 2px 8px;\
  border-radius: 10px;\
  cursor: pointer;\
  transition: all 0.15s;\
}\
.actions-scope-toggle .pill:hover {\
  color: var(--text-secondary);\
  border-color: var(--border);\
}\
.actions-scope-toggle .pill.active {\
  color: var(--accent);\
  border-color: var(--accent);\
  background: var(--accent-dim);\
}\
.actions-summary-bar {\
  display: flex;\
  gap: 24px;\
  margin-bottom: 24px;\
  flex-wrap: wrap;\
}\
.actions-stat {\
  display: flex;\
  align-items: center;\
  gap: 6px;\
}\
.actions-stat-dot {\
  width: 8px;\
  height: 8px;\
  border-radius: 50%;\
}\
.actions-stat-count {\
  font-family: var(--font-body);\
  font-size: 28px;\
  font-weight: 600;\
  line-height: 1.1;\
  color: var(--text-primary);\
}\
.actions-stat-label {\
  font-family: var(--font-mono);\
  font-size: 11px;\
  font-weight: 600;\
  text-transform: uppercase;\
  letter-spacing: 1.5px;\
  color: var(--text-tertiary);\
}\
.actions-group-label {\
  font-family: var(--font-mono);\
  font-size: 11px;\
  font-weight: 600;\
  text-transform: uppercase;\
  letter-spacing: 1.5px;\
  color: var(--text-tertiary);\
  margin-bottom: 8px;\
  margin-top: 16px;\
}\
.actions-task-list {\
  margin-bottom: 16px;\
}\
.actions-task-row {\
  display: flex;\
  align-items: center;\
  gap: 8px;\
  padding: 10px 12px;\
  border-bottom: 1px solid var(--border-subtle);\
  transition: background 0.15s;\
}\
.actions-task-row:hover {\
  background: var(--bg-hover);\
}\
.actions-priority-dot {\
  width: 8px;\
  height: 8px;\
  border-radius: 50%;\
  flex-shrink: 0;\
}\
.actions-priority-dot.p0,\
.actions-priority-dot.p1 {\
  background: var(--red);\
}\
.actions-priority-dot.p2 {\
  background: var(--amber);\
}\
.actions-priority-dot.p3 {\
  background: var(--gray);\
}\
.actions-priority-dot.none {\
  background: var(--border-subtle);\
}\
.actions-task-name {\
  font-family: var(--font-body);\
  font-size: 14px;\
  font-weight: 400;\
  color: var(--text-primary);\
  text-decoration: none;\
  max-width: 400px;\
  overflow: hidden;\
  text-overflow: ellipsis;\
  white-space: nowrap;\
  flex: 1;\
}\
.actions-task-name:hover {\
  color: var(--accent);\
}\
.actions-section-pill {\
  font-family: var(--font-mono);\
  font-size: 11px;\
  font-weight: 400;\
  padding: 2px 8px;\
  border-radius: 10px;\
  white-space: nowrap;\
  flex-shrink: 0;\
}\
.actions-due {\
  font-family: var(--font-mono);\
  font-size: 11px;\
  font-weight: 400;\
  color: var(--text-tertiary);\
  white-space: nowrap;\
  flex-shrink: 0;\
}\
.actions-due.overdue {\
  color: var(--red);\
  font-weight: 600;\
}\
.actions-stale-indicator {\
  width: 8px;\
  height: 8px;\
  border-radius: 50%;\
  background: var(--amber);\
  flex-shrink: 0;\
}\
.actions-jira-badge {\
  font-family: var(--font-mono);\
  font-size: 11px;\
  font-weight: 400;\
  color: var(--blue);\
  text-decoration: none;\
  white-space: nowrap;\
}\
.actions-jira-badge:hover {\
  text-decoration: underline;\
}\
.actions-assignee {\
  font-family: var(--font-mono);\
  font-size: 11px;\
  font-weight: 400;\
  color: var(--text-tertiary);\
  white-space: nowrap;\
  flex-shrink: 0;\
}\
.actions-expand-link {\
  font-family: var(--font-mono);\
  font-size: 11px;\
  font-weight: 400;\
  color: var(--accent);\
  cursor: pointer;\
  padding: 8px 0;\
}\
.actions-expand-link:hover {\
  text-decoration: underline;\
}\
.actions-project-link {\
  font-family: var(--font-mono);\
  font-size: 11px;\
  font-weight: 400;\
  margin-top: 8px;\
}\
.actions-project-link a {\
  color: var(--accent);\
  text-decoration: none;\
}\
.actions-project-link a:hover {\
  text-decoration: underline;\
}\
.actions-unavailable {\
  font-family: var(--font-body);\
  font-size: 14px;\
  font-weight: 400;\
  color: var(--text-secondary);\
  padding: 24px;\
}\
.actions-unavailable-hint {\
  font-family: var(--font-mono);\
  font-size: 11px;\
  font-weight: 400;\
  color: var(--text-tertiary);\
  padding: 0 24px;\
}\
';

  // ── Icon SVG (checkmark in box) ──

  var ICON_SVG = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 11l3 3L22 4"></path><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path></svg>';

  // ── Helpers ──

  function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function formatDueDate(dateStr) {
    if (!dateStr) return '';
    var d = new Date(dateStr + 'T00:00:00');
    return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
  }

  // ── Registration ──

  PanelRegistry.register({
    id: 'actions',
    group: 'activity',
    label: 'SE Actions',
    icon: ICON_SVG,
    badgeKey: 'actions.tasks.length',
    dataKey: 'actions',

    render: function(container, data, config) {
      // Inject scoped CSS on first render
      if (!document.querySelector('style[data-panel="actions"]')) {
        PanelRegistry.injectCSS('actions', PANEL_CSS);
      }

      // Closure state for scope toggle and expand/collapse
      var _actionsScope = (data && data.scope) || 'my_tasks';
      var _actionsExpanded = false;

      function renderInner() {
        // Graceful degradation
        if (!data || !data.available) {
          var reason = data && data.reason === 'api_error'
            ? 'Asana data unavailable &mdash; API error during fetch'
            : 'Asana not configured for this customer';
          var hint = data && data.reason === 'api_error'
            ? 'Check ASANA_TOKEN in ~/.tsm-ai/.env'
            : 'Add action_tracker_id to templates/customers.yaml, or run /asana-setup';
          container.innerHTML =
            '<div class="section-label">SE Actions</div>' +
            '<div class="actions-unavailable">' + reason + '</div>' +
            '<div class="actions-unavailable-hint">' + hint + '</div>';
          return;
        }

        // Filter tasks by scope
        var tasks = (data.tasks || []).slice();
        if (_actionsScope === 'my_tasks' && data.current_user) {
          tasks = tasks.filter(function(t) {
            return t.assignee && t.assignee.gid === data.current_user.gid;
          });
        }

        // Sort: overdue first, then by priority (P0 > P1 > P2 > P3 > null), then by due date
        tasks.sort(function(a, b) {
          if (a.overdue !== b.overdue) return a.overdue ? -1 : 1;
          var pa = ACTIONS_PRIO_ORDER[a.priority] !== undefined ? ACTIONS_PRIO_ORDER[a.priority] : 99;
          var pb = ACTIONS_PRIO_ORDER[b.priority] !== undefined ? ACTIONS_PRIO_ORDER[b.priority] : 99;
          if (pa !== pb) return pa - pb;
          if (a.due_on && b.due_on) return a.due_on.localeCompare(b.due_on);
          if (a.due_on) return -1;
          if (b.due_on) return 1;
          return 0;
        });

        // Group by status category
        var groups = { 'In Progress': [], 'Waiting': [], 'To Do': [], 'Other': [] };
        tasks.forEach(function(t) {
          if (t.section === 'In Progress') groups['In Progress'].push(t);
          else if (t.section === 'Waiting on Customer' || t.section === 'Waiting on Eng') groups['Waiting'].push(t);
          else if (t.section === 'To Do') groups['To Do'].push(t);
          else groups['Other'].push(t);
        });

        // Compute summary
        var summary = {
          total: tasks.length,
          in_progress: groups['In Progress'].length,
          waiting: groups['Waiting'].length,
          todo: groups['To Do'].length,
          overdue: tasks.filter(function(t) { return t.overdue; }).length,
          stale: tasks.filter(function(t) { return t.stale; }).length
        };

        // Build header with scope toggle
        var html = '<div class="actions-header">' +
          '<span class="actions-title">SE Actions</span>' +
          '<span class="actions-count-badge">' + summary.total + '</span>' +
          '<div class="actions-scope-toggle">' +
            '<button class="pill' + (_actionsScope === 'my_tasks' ? ' active' : '') + '" data-actions-scope="my_tasks">My Tasks</button>' +
            '<button class="pill' + (_actionsScope === 'team' ? ' active' : '') + '" data-actions-scope="team">Team</button>' +
          '</div>' +
        '</div>';

        // Summary bar
        html += '<div class="actions-summary-bar">' +
          '<span class="actions-stat">' +
            '<span class="actions-stat-dot" style="background:var(--blue)"></span>' +
            '<span class="actions-stat-count">' + summary.in_progress + '</span>' +
            '<span class="actions-stat-label">In Progress</span>' +
          '</span>' +
          '<span class="actions-stat">' +
            '<span class="actions-stat-dot" style="background:var(--orange)"></span>' +
            '<span class="actions-stat-count">' + summary.waiting + '</span>' +
            '<span class="actions-stat-label">Waiting</span>' +
          '</span>' +
          '<span class="actions-stat">' +
            '<span class="actions-stat-dot" style="background:var(--amber)"></span>' +
            '<span class="actions-stat-count">' + summary.todo + '</span>' +
            '<span class="actions-stat-label">To Do</span>' +
          '</span>';

        if (summary.overdue > 0) {
          html += '<span class="actions-stat">' +
            '<span class="actions-stat-dot" style="background:var(--red)"></span>' +
            '<span class="actions-stat-count" style="color:var(--red)">' + summary.overdue + '</span>' +
            '<span class="actions-stat-label">Overdue</span>' +
          '</span>';
        }
        if (summary.stale > 0) {
          html += '<span class="actions-stat">' +
            '<span class="actions-stat-dot" style="background:var(--amber)"></span>' +
            '<span class="actions-stat-count" style="color:var(--amber)">' + summary.stale + '</span>' +
            '<span class="actions-stat-label">Stale</span>' +
          '</span>';
        }
        html += '</div>';

        // Task list by group
        var showTeamAssignee = _actionsScope === 'team';
        var maxVisible = 10;
        var taskIndex = 0;

        var groupOrder = ['In Progress', 'Waiting', 'To Do', 'Other'];
        groupOrder.forEach(function(groupName) {
          var groupTasks = groups[groupName];
          if (groupTasks.length === 0) return;

          html += '<div class="actions-group-label">' + groupName + ' (' + groupTasks.length + ')</div>';
          html += '<div class="actions-task-list">';

          groupTasks.forEach(function(t) {
            taskIndex++;
            var hidden = !_actionsExpanded && taskIndex > maxVisible ? ' style="display:none" data-actions-overflow' : '';

            // Priority dot class
            var priClass = t.priority ? t.priority.toLowerCase() : 'none';

            // Section pill color
            var secColor = ACTIONS_SECTION_COLORS[t.section] || { bg: 'var(--gray-dim)', color: 'var(--gray)' };

            // Due date
            var dueHtml = '';
            if (t.due_on) {
              var dueLabel = formatDueDate(t.due_on);
              if (t.overdue) {
                dueHtml = '<span class="actions-due overdue">' + dueLabel + ' overdue</span>';
              } else {
                dueHtml = '<span class="actions-due">' + dueLabel + '</span>';
              }
            }

            // Stale indicator
            var staleHtml = '';
            if (t.stale) {
              staleHtml = '<span class="actions-stale-indicator" title="Stale: ' + (t.stale_days || '7+') + 'd since last update"></span>';
            }

            // Linked Jira badge
            var jiraHtml = '';
            if (t.linked_jira) {
              jiraHtml = '<a class="actions-jira-badge" href="https://coreweave.atlassian.net/browse/' + escapeHtml(t.linked_jira) + '" target="_blank" rel="noopener">' + escapeHtml(t.linked_jira) + '</a>';
            }

            // Assignee (team view only)
            var assigneeHtml = '';
            if (showTeamAssignee && t.assignee) {
              assigneeHtml = '<span class="actions-assignee">' + escapeHtml(t.assignee.name) + '</span>';
            }

            // Task name (strip Jira reference from display name)
            var displayName = t.name || '';
            if (t.linked_jira) {
              displayName = displayName.replace(/\s*\(WB-\d+\)\s*$/, '');
            }

            // Badges group (stale + jira)
            var badgesHtml = '';
            if (staleHtml || jiraHtml) {
              badgesHtml = '<span style="display:flex;align-items:center;gap:6px">' + staleHtml + jiraHtml + '</span>';
            }

            html += '<div class="actions-task-row"' + hidden + '>' +
              '<span class="actions-priority-dot ' + priClass + '" title="' + escapeHtml(t.priority || 'No priority') + '"></span>' +
              '<a class="actions-task-name" href="' + escapeHtml(t.url || '#') + '" target="_blank" rel="noopener" title="' + escapeHtml(t.name) + '">' + escapeHtml(displayName) + '</a>' +
              '<span class="actions-section-pill" style="background:' + secColor.bg + ';color:' + secColor.color + '">' + escapeHtml(t.section) + '</span>' +
              dueHtml +
              badgesHtml +
              assigneeHtml +
            '</div>';
          });

          html += '</div>';
        });

        // Show all / collapse link
        if (tasks.length > maxVisible) {
          if (_actionsExpanded) {
            html += '<div class="actions-expand-link" data-actions-expand>Show fewer</div>';
          } else {
            html += '<div class="actions-expand-link" data-actions-expand>Show all ' + tasks.length + ' tasks</div>';
          }
        }

        // Project link
        if (data.project_url) {
          html += '<div class="actions-project-link">' +
            '<a href="' + escapeHtml(data.project_url) + '" target="_blank" rel="noopener">Open in Asana &rarr;</a>' +
          '</div>';
        }

        container.innerHTML = html;

        // Wire scope toggle
        var scopeBtns = container.querySelectorAll('[data-actions-scope]');
        for (var i = 0; i < scopeBtns.length; i++) {
          scopeBtns[i].addEventListener('click', function(e) {
            _actionsScope = e.currentTarget.getAttribute('data-actions-scope');
            _actionsExpanded = false;
            renderInner();
          });
        }

        // Wire expand/collapse
        var expandLink = container.querySelector('[data-actions-expand]');
        if (expandLink) {
          expandLink.addEventListener('click', function() {
            _actionsExpanded = !_actionsExpanded;
            renderInner();
          });
        }
      }

      renderInner();
      return { charts: [] };
    },

    getHeadlineStats: function(data) {
      if (!data || !data.available) return [];
      return [
        { label: 'SE Actions', value: String(data.summary ? data.summary.total || 0 : 0), color: 'var(--text-primary)' },
        { label: 'In Progress', value: String(data.summary ? data.summary.in_progress || 0 : 0), color: 'var(--blue)' },
        { label: 'Overdue', value: String(data.summary ? data.summary.overdue || 0 : 0), color: (data.summary && data.summary.overdue > 0) ? 'var(--red)' : 'var(--text-tertiary)' }
      ];
    },

    getAttentionItems: function(data) {
      if (!data || !data.available) return [];
      var items = [];
      if (data.summary && data.summary.overdue > 0) {
        items.push({ severity: 'high', text: data.summary.overdue + ' overdue SE actions', action: { panel: 'actions' } });
      }
      if (data.summary && data.summary.stale > 0) {
        items.push({ severity: 'medium', text: data.summary.stale + ' stale actions (7+ days)', action: { panel: 'actions' } });
      }
      return items;
    }
  });

})();
