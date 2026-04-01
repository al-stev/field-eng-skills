/**
 * Panel Registry — Dashboard V2
 *
 * Global panel registration contract. Each panel JS file calls
 * PanelRegistry.register() with its config. The shell discovers
 * registered panels and builds navigation + rendering from them.
 *
 * No ES module syntax (file:// CORS constraint).
 */
(function() {
  'use strict';

  var PanelRegistry = {
    _panels: {},
    _renderOrder: [],

    /**
     * Register a panel. Validates required fields.
     * @param {Object} config - Panel configuration
     * @param {string} config.id - Unique panel identifier (matches hash route)
     * @param {Function} config.render - render(container, data, config) -> { charts: [] }
     * @param {Function} config.getHeadlineStats - getHeadlineStats(data) -> [{ label, value, color }]
     * @param {Function} config.getAttentionItems - getAttentionItems(data) -> [{ severity, text, action }]
     */
    register: function(config) {
      var required = ['id', 'render', 'getHeadlineStats', 'getAttentionItems'];
      for (var i = 0; i < required.length; i++) {
        if (!config[required[i]]) {
          console.error('[PanelRegistry] Missing required field: ' + required[i], config);
          return;
        }
      }
      if (typeof config.render !== 'function') {
        console.error('[PanelRegistry] render must be a function', config.id);
        return;
      }
      if (typeof config.getHeadlineStats !== 'function') {
        console.error('[PanelRegistry] getHeadlineStats must be a function', config.id);
        return;
      }
      if (typeof config.getAttentionItems !== 'function') {
        console.error('[PanelRegistry] getAttentionItems must be a function', config.id);
        return;
      }

      this._panels[config.id] = config;
      this._renderOrder.push(config.id);
    },

    /**
     * Get a panel config by id.
     */
    get: function(id) {
      return this._panels[id] || null;
    },

    /**
     * Get all panels in registration order.
     */
    getAll: function() {
      var self = this;
      return this._renderOrder.map(function(id) {
        return self._panels[id];
      });
    },

    /**
     * Walk dot-separated path through nested objects.
     * @param {Object} obj - Root object
     * @param {string} dotPath - Dot-separated key path (e.g. 'usage.seat_utilization')
     * @returns {*} Resolved value or undefined
     */
    _resolveKey: function(obj, dotPath) {
      if (!obj || !dotPath) return undefined;
      var parts = dotPath.split('.');
      var current = obj;
      for (var i = 0; i < parts.length; i++) {
        if (current === null || current === undefined) return undefined;
        if (parts[i] === 'length' && Array.isArray(current)) return current.length;
        current = current[parts[i]];
      }
      return current;
    },

    /**
     * Render a panel into its container. Wraps in try/catch.
     * Resolves the panel's dataKey against the full data object so each
     * panel receives its own data slice (e.g. issues panel gets data.issues).
     * Panels with no dataKey (e.g. overview) receive the full data object.
     * @param {string} id - Panel id
     * @param {HTMLElement} container - DOM element to render into
     * @param {Object} data - INTELLIGENCE_DATA
     * @param {Object} config - { audience: 'internal'|'external' }
     * @returns {Object|null} - { charts: [...] } or null on error
     */
    renderPanel: function(id, container, data, config) {
      var panel = this._panels[id];
      if (!panel) {
        console.error('[PanelRegistry] Panel not found: ' + id);
        return null;
      }
      try {
        // Resolve the panel's data slice via its dataKey
        var panelData = data;
        if (panel.dataKey) {
          panelData = this._resolveKey(data, panel.dataKey);
        }
        return panel.render(container, panelData, config);
      } catch (err) {
        console.error('[PanelRegistry] Error rendering panel ' + id + ':', err);
        container.innerHTML = '<div class="placeholder-panel">' +
          '<div class="placeholder-icon" style="border-color:var(--red-border);background:var(--red-dim)">' +
          '<svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="var(--red)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">' +
          '<circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg></div>' +
          '<div class="placeholder-title">Panel failed to load</div>' +
          '<div class="placeholder-desc">Check browser console for details.</div>' +
          '</div>';
        return null;
      }
    },

    /**
     * Inject scoped CSS for a panel. Prepends #panel-{id} to every selector.
     * Handles comma-separated selectors, nested selectors, and skips @-rules.
     * @param {string} id - Panel id
     * @param {string} cssText - Raw CSS text
     */
    injectCSS: function(id, cssText) {
      var prefix = '#panel-' + id;
      var scoped = cssText.replace(
        /([^{}@/][^{}]*?)(\{)/g,
        function(match, selectors, brace) {
          // Skip if this looks like a @-rule body or keyframe percentage
          if (/^\s*(@|from|to|\d+%)/.test(selectors)) {
            return match;
          }
          var parts = selectors.split(',').map(function(sel) {
            sel = sel.trim();
            if (!sel || /^@/.test(sel) || /^from$|^to$|^\d+%$/.test(sel)) {
              return sel;
            }
            return prefix + ' ' + sel;
          });
          return parts.join(', ') + brace;
        }
      );

      var style = document.createElement('style');
      style.setAttribute('data-panel', id);
      style.textContent = scoped;
      document.head.appendChild(style);
    }
  };

  window.PanelRegistry = PanelRegistry;
})();
