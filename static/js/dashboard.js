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

const setArrow = (id, flow, orientation = 'horizontal', label) => {
  const el = document.getElementById(id);
  if (!el) return;

  const icon = el.querySelector('.arrow-icon');
  const text = el.querySelector('.arrow-label');

  let symbol = '·';
  const forwardSymbol =
    orientation === 'vertical'
      ? '↓'
      : orientation === 'vertical-up'
      ? '↑'
      : '→';
  const reverseSymbol =
    orientation === 'vertical'
      ? '↑'
      : orientation === 'vertical-up'
      ? '↓'
      : '←';

  if (flow === 'forward') {
    symbol = forwardSymbol;
  } else if (flow === 'reverse') {
    symbol = reverseSymbol;
  }

  if (icon) {
    icon.textContent = symbol;
  } else {
    el.textContent = symbol;
  }

  if (text && label) {
    text.textContent = label;
  }

  el.dataset.flow = flow || 'idle';
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
  setText(
    'grid-rate',
    `Rate: ${formatCurrency(payload.grid_import_rate, payload.currency || 'R')}/kWh`
  );
  setText('last-updated', payload.last_updated || 'pending');

  setArrow(
    'pv-arrow',
    payload.pv_watts > 0 ? 'forward' : 'idle',
    'horizontal',
    payload.pv_watts > 0 ? 'PV to inverter' : 'PV idle'
  );

  const batteryFlow =
    payload.battery_direction === 'Discharging'
      ? 'forward'
      : payload.battery_direction === 'Charging'
      ? 'reverse'
      : 'idle';
  setArrow(
    'battery-arrow',
    batteryFlow,
    'vertical-up',
    batteryFlow === 'forward'
      ? 'Battery to inverter'
      : batteryFlow === 'reverse'
      ? 'Charging from inverter'
      : 'Battery idle'
  );

  const gridFlow =
    payload.grid_direction === 'Importing'
      ? 'forward'
      : payload.grid_direction === 'Exporting'
      ? 'reverse'
      : 'idle';
  setArrow(
    'grid-arrow',
    gridFlow,
    'vertical',
    gridFlow === 'forward'
      ? 'Grid to inverter'
      : gridFlow === 'reverse'
      ? 'Exporting to grid'
      : 'Grid idle'
  );

  setArrow(
    'load-arrow',
    payload.load_watts > 0 ? 'forward' : 'idle',
    'horizontal',
    payload.load_watts > 0 ? 'Inverter to load' : 'Load idle'
  );
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
