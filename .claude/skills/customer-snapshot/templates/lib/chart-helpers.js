/**
 * Chart Helpers — Dashboard V2
 *
 * Shared ECharts utilities with theme-aware chart creation.
 * All panels use these helpers for consistent styling.
 *
 * No ES module syntax (file:// CORS constraint).
 */
(function() {
  'use strict';

  var _themeRegistered = false;

  function registerWandbTheme() {
    if (_themeRegistered) return;
    _themeRegistered = true;

    var accent = getColor('accent') || '#d4a853';
    var blue = getColor('blue') || '#60a5fa';
    var green = getColor('green') || '#4ade80';
    var amber = getColor('amber') || '#fbbf24';
    var red = getColor('red') || '#f87171';
    var orange = getColor('orange') || '#fb923c';
    var gray = getColor('gray') || '#6b7280';
    var textPrimary = getColor('text-primary') || '#e8eaed';
    var textTertiary = getColor('text-tertiary') || '#5c6370';
    var borderSubtle = getColor('border-subtle') || '#1e2430';

    echarts.registerTheme('wandb', {
      color: [accent, blue, green, amber, red, orange, gray],
      backgroundColor: 'transparent',
      textStyle: {
        fontFamily: "'Outfit', system-ui, sans-serif",
        color: textPrimary
      },
      categoryAxis: {
        axisLine: { lineStyle: { color: borderSubtle } },
        axisTick: { lineStyle: { color: borderSubtle } },
        axisLabel: {
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 11,
          fontWeight: 600,
          color: textTertiary
        },
        splitLine: { lineStyle: { color: borderSubtle } }
      },
      valueAxis: {
        axisLine: { lineStyle: { color: borderSubtle } },
        axisTick: { lineStyle: { color: borderSubtle } },
        axisLabel: {
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 11,
          fontWeight: 600,
          color: textTertiary
        },
        splitLine: { lineStyle: { color: borderSubtle } }
      },
      tooltip: {
        backgroundColor: getColor('bg-elevated') || '#141820',
        borderColor: getColor('border') || '#2a3040',
        textStyle: {
          color: textPrimary,
          fontFamily: "'Outfit', system-ui, sans-serif",
          fontSize: 13
        }
      },
      legend: {
        textStyle: {
          fontFamily: "'Outfit', system-ui, sans-serif",
          color: textTertiary
        }
      }
    });
  }

  function getColor(tokenName) {
    return getComputedStyle(document.documentElement)
      .getPropertyValue('--' + tokenName).trim();
  }

  var ChartHelpers = {
    _instances: [],

    /**
     * Create a themed ECharts instance in a container.
     * Registers the wandb theme on first call.
     * @param {HTMLElement} container - DOM element for the chart
     * @returns {Object} ECharts instance
     */
    createChart: function(container) {
      registerWandbTheme();
      var chart = echarts.init(container, 'wandb');
      this._instances.push(chart);
      return chart;
    },

    /**
     * Resize all tracked ECharts instances. Safe to call anytime.
     */
    resizeAll: function() {
      for (var i = 0; i < this._instances.length; i++) {
        try {
          this._instances[i].resize();
        } catch (e) {
          // Instance may have been disposed
        }
      }
    },

    /**
     * Get a CSS custom property value by token name.
     * @param {string} tokenName - Token name without -- prefix
     * @returns {string} Computed value
     */
    getColor: function(tokenName) {
      return getColor(tokenName);
    },

    /**
     * Standard tooltip configuration using design tokens.
     * @returns {Object} ECharts tooltip config
     */
    tooltipConfig: function() {
      return {
        backgroundColor: getColor('bg-elevated'),
        borderColor: getColor('border'),
        textStyle: {
          color: getColor('text-primary'),
          fontFamily: "'Outfit', system-ui, sans-serif",
          fontSize: 13
        }
      };
    },

    /**
     * Standard axis label configuration.
     * @returns {Object} ECharts axisLabel config
     */
    axisLabelConfig: function() {
      return {
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 11,
        fontWeight: 600,
        color: getColor('text-tertiary')
      };
    },

    /**
     * Standard grid line configuration.
     * @returns {Object} ECharts splitLine config
     */
    gridLine: function() {
      return {
        lineStyle: {
          color: getColor('border-subtle')
        }
      };
    },

    /**
     * Format a number with locale separators.
     * @param {number} n
     * @returns {string}
     */
    formatNumber: function(n) {
      if (n == null || isNaN(n)) return '0';
      return Number(n).toLocaleString();
    },

    /**
     * Calculate days between a date string and a reference date.
     * @param {string} dateStr - ISO date string
     * @param {Date} [refDate] - Reference date (default: now)
     * @returns {number} Days between
     */
    daysBetween: function(dateStr, refDate) {
      var d = new Date(dateStr);
      var r = refDate || new Date();
      return Math.floor((r - d) / (1000 * 60 * 60 * 24));
    },

    /**
     * Convert "2025-03" to "Mar 25".
     * @param {string} ym - Year-month string
     * @returns {string} Formatted month
     */
    formatMonth: function(ym) {
      var parts = ym.split('-');
      var months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
      return months[parseInt(parts[1]) - 1] + ' ' + parts[0].slice(2);
    }
  };

  window.ChartHelpers = ChartHelpers;
})();
