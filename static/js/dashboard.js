const banner = document.getElementById('status-banner');
let refreshTimer = null;

const setText = (id, value) => {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = value;
};

const formatNumber = (value, unit = '') => {
  if (value === null || value === undefined) return `--${unit ? ' ' + unit : ''}`;
  return `${Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 })}${unit ? ' ' + unit : ''}`;
};

const formatCurrency = (value, currency) => {
  if (value === null || value === undefined) return '--';
  return `${currency} ${Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
};

const setArrow = (id, direction) => {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = direction === 'Importing' || direction === 'Discharging' ? '→' : direction === 'Charging' || direction === 'Exporting' ? '←' : '·';
};

const showError = (message) => {
  if (!banner) return;
  banner.textContent = message;
  banner.classList.remove('d-none');
};

const clearError = () => {
  if (!banner) return;
  banner.textContent = '';
  banner.classList.add('d-none');
};

const renderData = (payload) => {
  clearError();
  setText('plant-name', payload.plant_name || 'Sunsynk Plant');
  setText('pv-watts', formatNumber(payload.pv_watts, 'W'));
  setText('pv-direction', payload.pv_watts > 0 ? 'Generating' : 'Idle');
  setText('battery-watts', formatNumber(payload.battery_watts, 'W'));
  setText('battery-direction', payload.battery_direction);
  setText('grid-watts', formatNumber(payload.grid_watts, 'W'));
  setText('grid-direction', payload.grid_direction);
  setText('load-watts', formatNumber(payload.load_watts, 'W'));
  setText('battery-soc', `SOC ${payload.soc ?? '--'}%`);
  setText('etoday', formatNumber(payload.etoday, 'kWh'));
  setText('etotal', formatNumber(payload.etotal, 'kWh'));
  setText('currency', payload.currency || 'R');
  setText('income-today', formatCurrency(payload.income_today, payload.currency || 'R'));
  setText('grid-import-today', formatNumber(payload.grid_import_today, 'kWh'));
  setText('grid-export-today', formatNumber(payload.grid_export_today, 'kWh'));
  setText('grid-import-value', `Cost: ${formatCurrency(payload.grid_import_value, payload.currency || 'R')}`);
  setText('grid-export-value', `Value: ${formatCurrency(payload.grid_export_value, payload.currency || 'R')}`);
  setText('last-updated', payload.last_updated || 'pending');

  setArrow('pv-arrow', payload.pv_watts > 0 ? 'Importing' : 'Idle');
  setArrow('battery-arrow', payload.battery_direction);
  setArrow('grid-arrow', payload.grid_direction);
};

const scheduleRefresh = (delay) => {
  if (refreshTimer) {
    clearTimeout(refreshTimer);
  }
  refreshTimer = setTimeout(fetchStatus, delay);
};

async function fetchStatus() {
  try {
    const response = await fetch('/api/status');
    const result = await response.json();
    if (!result.success) {
      throw new Error(result.error || 'Unknown error fetching Sunsynk data');
    }
    renderData(result.data);
    scheduleRefresh(result.refreshInterval ? result.refreshInterval * 1000 : DASHBOARD_REFRESH || 60000);
  } catch (err) {
    showError(err.message);
    scheduleRefresh(15000);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  fetchStatus();
  scheduleRefresh(DASHBOARD_REFRESH || 60000);
});
