const state = { hasData: false, cleaned: false, columns: null, columnTypes: null };

// Base URL of the Flask backend (set in index.html, e.g. via window.API_BASE_URL).
// Falls back to same-origin ("") for local dev where Flask serves both.
const API_BASE = (window.API_BASE_URL || '').replace(/\/$/, '');

async function api(url, opts = {}) {
  const res = await fetch(API_BASE + url, {
    // Needed so the Flask session cookie is sent/stored across the
    // Vercel <-> Render origins.
    credentials: 'include',
    ...opts,
  });
  let data;
  try { data = await res.json(); } catch (e) { data = null; }
  if (!res.ok) {
    const msg = (data && data.error) || `Request failed (${res.status})`;
    throw new Error(msg);
  }
  return data;
}

function wireDownloadLinks() {
  document.querySelectorAll('a[data-format]').forEach((a) => {
    a.addEventListener('click', (e) => {
      e.preventDefault();
      const fmt = a.getAttribute('data-format');
      window.location.href = `${API_BASE}/api/download?format=${fmt}&dataset=active`;
    });
  });
}
document.addEventListener('DOMContentLoaded', wireDownloadLinks);

function toast(message, ok = true) {
  const el = document.getElementById('toast');
  el.textContent = message;
  el.className = `toast show ${ok ? 'ok' : 'err'}`;
  setTimeout(() => el.classList.remove('show'), 3500);
}

function el(tag, attrs = {}, children = []) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'class') e.className = v;
    else if (k === 'html') e.innerHTML = v;
    else e.setAttribute(k, v);
  }
  (Array.isArray(children) ? children : [children]).forEach(c => {
    if (c === null || c === undefined) return;
    e.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
  });
  return e;
}

function fmtVal(v) {
  if (v === null || v === undefined) return '';
  if (typeof v === 'number') return Number.isInteger(v) ? v.toString() : v.toFixed(4).replace(/\.?0+$/, '');
  return String(v);
}

function renderTable(container, rows, options = {}) {
  container.innerHTML = '';
  if (!rows || rows.length === 0) {
    container.appendChild(el('div', { class: 'info-banner' }, 'No data.'));
    return;
  }
  const cols = options.columns || Object.keys(rows[0]);
  const table = el('table', { class: 'dframe' });
  const thead = el('thead', {}, el('tr', {}, cols.map(c => el('th', {}, c))));
  const tbody = el('tbody');
  rows.slice(0, options.limit || rows.length).forEach(row => {
    const tr = el('tr');
    cols.forEach(c => {
      let cellText = fmtVal(row[c]);
      const td = el('td', {}, cellText);
      if (c === 'Issues' && options.styleIssues) {
        td.className = cellText.includes('✓ OK') ? 'issue-ok' : (cellText.toLowerCase().includes('missing') || cellText.toLowerCase().includes('outlier')) ? 'issue-warn' : 'issue-bad';
      }
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
  table.appendChild(thead);
  table.appendChild(tbody);
  container.appendChild(table);
}

function renderMetrics(container, cards) {
  container.innerHTML = '';
  cards.forEach(({ value, label, sub }) => {
    container.appendChild(el('div', { class: 'metric-card' }, [
      el('div', { class: 'metric-value' }, String(value)),
      el('div', { class: 'metric-label' }, label),
      sub ? el('div', { class: 'metric-sub' }, sub) : null,
    ]));
  });
}

function renderChartImage(container, image, placeholderText) {
  container.innerHTML = '';
  if (image) {
    container.appendChild(el('img', { src: image }));
  } else {
    container.appendChild(el('div', { class: 'placeholder' }, placeholderText || 'No chart to display.'));
  }
}

function populateSelect(select, options, opts = {}) {
  select.innerHTML = '';
  if (opts.placeholder) select.appendChild(el('option', { value: '' }, opts.placeholder));
  if (opts.includeNone) select.appendChild(el('option', { value: 'None' }, 'None'));
  options.forEach(o => select.appendChild(el('option', { value: o }, o)));
  if (opts.selected) select.value = opts.selected;
}

function renderMultiselect(container, name, options, defaultChecked = []) {
  container.innerHTML = '';
  options.forEach(o => {
    const checked = defaultChecked.includes(o);
    const label = el('label', { class: checked ? 'checked' : '' });
    const input = el('input', { type: 'checkbox', value: o });
    input.checked = checked;
    input.addEventListener('change', () => label.classList.toggle('checked', input.checked));
    label.appendChild(input);
    label.appendChild(document.createTextNode(o));
    container.appendChild(label);
  });
}

function getMultiselectValues(container) {
  return Array.from(container.querySelectorAll('input:checked')).map(i => i.value);
}

const pageTitles = {
  clean: ['🧹 Data Cleaning Studio', 'Upload, inspect, configure and clean your dataset.'],
  visualize: ['📈 Visualization Studio', 'Explore your dataset through interactive charts and plots.'],
  analyze: ['🔬 Analysis Lab', 'Statistical analysis, outlier detection, and data profiling.'],
  chat: ['💬 AI Insights & Chat', "Ask Llama 3 (via Groq Cloud) anything about the dataset."],
};

function setActivePage(page) {
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.toggle('active', b.dataset.page === page));
  document.querySelectorAll('.page').forEach(p => p.classList.toggle('active', p.id === `page-${page}`));
  document.getElementById('heroTitle').textContent = pageTitles[page][0];
  document.getElementById('heroSub').textContent = pageTitles[page][1];
  document.getElementById('sidebarCleanOptions').style.display = page === 'clean' ? 'block' : 'none';
  document.getElementById('sidebarDatasetInfo').style.display = page !== 'clean' && state.hasData ? 'block' : 'none';

  if (page === 'visualize') initVisualizePage();
  if (page === 'analyze') initAnalyzePage();
  if (page === 'chat') initChatPage();
}

document.getElementById('nav').addEventListener('click', (e) => {
  const btn = e.target.closest('.nav-btn');
  if (!btn || btn.disabled) return;
  setActivePage(btn.dataset.page);
});

function updateNavLocks() {
  document.querySelectorAll('.nav-btn').forEach(b => {
    if (b.dataset.requiresData === 'true') b.disabled = !state.hasData;
  });
  document.getElementById('unlockHint').style.display = state.hasData ? 'none' : 'block';
}


document.addEventListener('click', (e) => {
  const tabBtn = e.target.closest('.tab-btn');
  if (!tabBtn) return;
  const group = tabBtn.closest('.tabs');
  const scope = group.parentElement;
  group.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b === tabBtn));
  scope.querySelectorAll(':scope > .tab-panel').forEach(p => {
    p.classList.toggle('active', p.id === tabBtn.dataset.tab || p.id === `${tabBtn.dataset.tab}`);
  });
});


const fileInput = document.getElementById('fileInput');
const dropZone = document.getElementById('dropZone');
document.getElementById('chooseFileBtn').addEventListener('click', () => fileInput.click());
dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('dragover'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
dropZone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropZone.classList.remove('dragover');
  if (e.dataTransfer.files.length) { fileInput.files = e.dataTransfer.files; handleUpload(); }
});
fileInput.addEventListener('change', handleUpload);

async function handleUpload() {
  const file = fileInput.files[0];
  if (!file) return;
  const formData = new FormData();
  formData.append('file', file);
  try {
    toast(`Uploading ${file.name}…`);
    const data = await api('/api/upload', { method: 'POST', body: formData });
    state.hasData = true;
    state.cleaned = false;
    updateNavLocks();
    renderCleanUpload(data);
    buildCleaningOptionsSidebar();
    toast('✅ File loaded successfully.');
  } catch (e) {
    toast(e.message, false);
  }
}

function renderCleanUpload(data) {
  document.getElementById('cleanContent').style.display = 'block';
  document.getElementById('cleanResults').style.display = 'none';
  document.getElementById('rawReviewSection').style.display = 'block';
  document.getElementById('showRawReviewBtn').style.display = 'none';
  const o = data.overview;
  renderMetrics(document.getElementById('rawMetrics'), [
    { value: o.rows, label: 'Rows' },
    { value: o.columns, label: 'Columns' },
    { value: o.missing_cells, label: 'Missing Cells', sub: `${o.missing_pct}%` },
    { value: o.duplicate_rows, label: 'Duplicate Rows' },
    { value: `${o.memory_usage_kb} KB`, label: 'Memory' },
    { value: o.total_cells, label: 'Total Cells' },
  ]);
  renderTable(document.getElementById('columnReport'), data.column_report, { styleIssues: true });
  renderTable(document.getElementById('rawPreview'), data.preview);

  loadImage('/api/charts/missing-heatmap', document.getElementById('missingHeatmap'), 'No missing values detected.');
  loadImage('/api/charts/dtype-pie?dataset=raw', document.getElementById('dtypePie'));
}

async function loadImage(url, container, placeholderIfNull) {
  container.innerHTML = '<div class="placeholder">Loading…</div>';
  try {
    const data = await api(url);
    renderChartImage(container, data.image, data.message || placeholderIfNull);
  } catch (e) {
    container.innerHTML = `<div class="placeholder">${e.message}</div>`;
  }
}

document.getElementById('showRawReviewBtn').addEventListener('click', () => {
  document.getElementById('rawReviewSection').style.display = 'block';
  document.getElementById('showRawReviewBtn').style.display = 'none';
});

document.getElementById('cleanBtn').addEventListener('click', async () => {
  const options = collectCleaningOptions();
  try {
    toast('Running cleaning pipeline…');
    const data = await api('/api/clean', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(options),
    });
    state.cleaned = true;
    renderCleanResults(data);
    toast('✅ Dataset Cleaned!');
  } catch (e) {
    toast(e.message, false);
  }
});

function renderCleanResults(data) {
  document.getElementById('rawReviewSection').style.display = 'none';
  document.getElementById('showRawReviewBtn').style.display = 'inline-block';
  document.getElementById('cleanResults').style.display = 'block';
  renderMetrics(document.getElementById('cleanMetrics'), [
    { value: `${data.raw_overview.rows} → ${data.overview.rows}`, label: 'Rows', sub: `removed ${data.rows_delta}` },
    { value: `${data.raw_overview.columns} → ${data.overview.columns}`, label: 'Columns', sub: `removed ${data.cols_delta}` },
    { value: `${data.raw_overview.missing_cells} → ${data.overview.missing_cells}`, label: 'Missing Cells' },
    { value: `${data.raw_overview.duplicate_rows} → ${data.overview.duplicate_rows}`, label: 'Duplicates' },
  ]);
  const log = document.getElementById('cleanLog');
  log.innerHTML = '';
  data.log.forEach(entry => log.appendChild(el('div', { class: 'log-entry' }, `› ${entry}`)));

  renderTable(document.getElementById('cleanPreview100'), data.preview);
  loadFullData('clean');
  renderTable(document.getElementById('cleanColumnReport'), data.column_report, { styleIssues: true });

  loadImage('/api/charts/missing-comparison', document.getElementById('missingComparison'), 'No missing values found in raw dataset.');

  populateSelect(document.getElementById('filterCol'), data.columns);
  loadColumnTypes().then(updateFilterConditions);
  loadActiveDataset();

  document.getElementById('sidebarDatasetInfo').innerHTML = `
    <div class="sidebar-section-header">📊 Active Dataset</div>
    <p><strong>Rows:</strong> ${data.overview.rows.toLocaleString()}</p>
    <p><strong>Columns:</strong> ${data.overview.columns}</p>
    <p><strong>Source:</strong> Cleaned data</p>`;
}

async function loadFullData(dataset) {
  const container = document.getElementById('cleanFullData');
  container.innerHTML = '<div class="placeholder">Loading…</div>';
  try {
    const data = await api(`/api/data?dataset=${dataset}`);
    renderTable(container, data.rows);
  } catch (e) { container.innerHTML = `<div class="placeholder">${e.message}</div>`; }
}

document.getElementById('filterCol').addEventListener('change', updateFilterConditions);

async function loadColumnTypes() {
  try {
    state.columnTypes = await api('/api/columns');
  } catch (e) {
    state.columnTypes = null;
  }
}

function updateFilterConditions() {
  const col = document.getElementById('filterCol').value;
  const types = state.columnTypes;
  const isNumeric = types && types.numeric && types.numeric.includes(col);
  const conditions = isNumeric ? ['=', '>', '<', '>=', '<='] : ['equals', 'contains'];
  populateSelect(document.getElementById('filterCondition'), conditions);
  const valueInput = document.getElementById('filterValue');
  valueInput.type = isNumeric ? 'number' : 'text';
  valueInput.placeholder = isNumeric ? 'Numeric value' : 'Text value';
}

document.getElementById('applyFilterBtn').addEventListener('click', async () => {
  const column = document.getElementById('filterCol').value;
  const condition = document.getElementById('filterCondition').value;
  const value = document.getElementById('filterValue').value;
  try {
    const data = await api('/api/filter', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ column, condition, value }),
    });
    toast(`✅ Filter applied — ${data.total.toLocaleString()} rows match.`);
    document.getElementById('clearFilterBtn').style.display = 'inline-block';
    loadActiveDataset();
  } catch (e) { toast(e.message, false); }
});

document.getElementById('clearFilterBtn').addEventListener('click', async () => {
  await api('/api/filter', { method: 'DELETE' });
  document.getElementById('clearFilterBtn').style.display = 'none';
  loadActiveDataset();
});

async function loadActiveDataset() {
  try {
    const data = await api('/api/data');
    const label = document.getElementById('clearFilterBtn').style.display === 'inline-block'
      ? `🔎 Filtered — ${data.total.toLocaleString()} rows`
      : `Full cleaned data — ${data.total.toLocaleString()} rows`;
    document.getElementById('activeDatasetLabel').textContent = label;
    renderTable(document.getElementById('activePreview20'), data.rows.slice(0, 20));
    renderTable(document.getElementById('activeFullData'), data.rows);
  } catch (e) { /* not ready yet */ }
}

function buildCleaningOptionsSidebar() {
  const box = document.getElementById('sidebarCleanOptions');
  box.innerHTML = `
    <div class="sidebar-section-header">🎛 Cleaning Options</div>
    <div class="opt-group-title">Structure</div>
    <label><input type="checkbox" id="opt_fix_names" checked> Fix column names</label>
    <label><input type="checkbox" id="opt_dup" checked> Remove duplicate rows</label>
    <label><input type="checkbox" id="opt_empty_rows" checked> Drop fully empty rows</label>
    <label><input type="checkbox" id="opt_const_cols" checked> Drop constant columns</label>
    <label><input type="checkbox" id="opt_high_miss"> Drop high-missing columns</label>
    <label>Missing % threshold: <input type="range" id="miss_thr" min="20" max="90" step="5" value="50"><span class="range-val" id="miss_thr_val">50%</span></label>

    <div class="opt-group-title">Text</div>
    <label><input type="checkbox" id="opt_strip" checked> Strip whitespace</label>
    <label>Standardize case:
      <select id="opt_case"><option value="none">none</option><option value="lower" selected>lower</option><option value="upper">upper</option><option value="title">title</option></select>
    </label>
    <label><input type="checkbox" id="opt_html"> Remove HTML tags</label>
    <label><input type="checkbox" id="opt_special"> Remove special characters</label>

    <div class="opt-group-title">Type Conversion</div>
    <label><input type="checkbox" id="opt_numeric" checked> Coerce numeric columns</label>
    <label><input type="checkbox" id="opt_dates" checked> Parse & format date columns</label>
    <label><input type="checkbox" id="opt_bool"> Convert yes/no, true/false to boolean</label>

    <div class="opt-group-title">Advanced</div>
    <label><input type="checkbox" id="opt_dup_cols"> Remove duplicate columns</label>
    <label><input type="checkbox" id="opt_currency"> Strip currency (₹$€£¥) &amp; % symbols</label>

    <div class="opt-group-title">Missing Values</div>
    <label>Fill numeric:
      <select id="opt_fill_num"><option value="none">none</option><option value="median" selected>median</option><option value="mean">mean</option><option value="zero">zero</option><option value="ffill">ffill</option><option value="bfill">bfill</option></select>
    </label>
    <label>Fill text:
      <select id="opt_fill_cat"><option value="none">none</option><option value="mode" selected>mode</option><option value="unknown">unknown</option><option value="ffill">ffill</option><option value="bfill">bfill</option></select>
    </label>

    <div class="opt-group-title">Outliers</div>
    <label>Method:
      <select id="opt_outlier"><option value="none">none</option><option value="iqr" selected>iqr</option><option value="zscore">zscore</option></select>
    </label>
    <label>Z threshold: <input type="range" id="z_thr" min="2" max="5" step="0.5" value="3"><span class="range-val" id="z_thr_val">3.0</span></label>

    <div class="opt-group-title">Normalization</div>
    <label>Normalize numeric:
      <select id="opt_norm"><option value="none" selected>none</option><option value="minmax">minmax</option><option value="zscore">zscore</option></select>
    </label>
  `;
  const missThr = document.getElementById('miss_thr');
  missThr.addEventListener('input', () => document.getElementById('miss_thr_val').textContent = `${missThr.value}%`);
  const zThr = document.getElementById('z_thr');
  zThr.addEventListener('input', () => document.getElementById('z_thr_val').textContent = Number(zThr.value).toFixed(1));
}

function collectCleaningOptions() {
  const val = (id) => document.getElementById(id).value;
  const checked = (id) => document.getElementById(id).checked;
  return {
    fix_column_names: checked('opt_fix_names'),
    remove_duplicates: checked('opt_dup'),
    drop_empty_rows: checked('opt_empty_rows'),
    drop_constant_columns: checked('opt_const_cols'),
    drop_high_missing: checked('opt_high_miss'),
    high_missing_threshold: Number(val('miss_thr')) / 100,
    strip_whitespace: checked('opt_strip'),
    standardize_case: val('opt_case'),
    remove_html: checked('opt_html'),
    remove_special_chars: checked('opt_special'),
    coerce_numeric: checked('opt_numeric'),
    parse_dates: checked('opt_dates'),
    convert_boolean: checked('opt_bool'),
    remove_duplicate_columns: checked('opt_dup_cols'),
    strip_currency: checked('opt_currency'),
    fill_numeric: val('opt_fill_num'),
    fill_categorical: val('opt_fill_cat'),
    outlier_method: val('opt_outlier'),
    zscore_threshold: Number(val('z_thr')),
    normalize: val('opt_norm'),
    reset_index: true,
  };
}

let vizInitialized = false;
async function initVisualizePage() {
  const cols = await api('/api/columns');
  state.columns = cols;

  populateSelect(document.getElementById('basicX'), cols.all);
  populateSelect(document.getElementById('basicY'), cols.numeric);
  populateSelect(document.getElementById('basicGroup'), cols.categorical);
  populateSelect(document.getElementById('basicColor'), ['Blue', 'Purple', 'Green', 'Orange', 'Red', 'Teal', 'Pink', 'Lavender']);
  document.getElementById('basicColor').selectedIndex = 0;
  toggleGroupSelect();
  loadChartGuide();

  populateSelect(document.getElementById('distCol'), cols.numeric);

  renderMultiselect(document.getElementById('corrColsWrap'), 'corr', cols.numeric, cols.numeric.slice(0, 8));

  populateSelect(document.getElementById('mvX'), cols.numeric);
  populateSelect(document.getElementById('mvY'), cols.numeric);
  populateSelect(document.getElementById('mvHue'), cols.categorical, { includeNone: true });
  populateSelect(document.getElementById('mvSize'), cols.numeric, { includeNone: true });

  const tsControls = document.getElementById('tsControls');
  if (cols.date.length === 0) {
    document.getElementById('tsNoDate').style.display = 'block';
    tsControls.style.display = 'none';
  } else {
    document.getElementById('tsNoDate').style.display = 'none';
    tsControls.style.display = 'flex';
    populateSelect(document.getElementById('tsDate'), cols.date);
    populateSelect(document.getElementById('tsVal'), cols.numeric);
  }

  if (!vizInitialized) {
    document.getElementById('basicTopN').addEventListener('input', (e) => document.getElementById('basicTopNVal').textContent = e.target.value);
    document.getElementById('distBins').addEventListener('input', (e) => document.getElementById('distBinsVal').textContent = e.target.value);

    document.getElementById('basicType').addEventListener('change', () => { toggleGroupSelect(); highlightChartGuide(); });
    document.getElementById('basicRenderBtn').addEventListener('click', renderBasicChart);
    document.getElementById('distRenderBtn').addEventListener('click', renderDistChart);
    document.getElementById('corrRenderBtn').addEventListener('click', renderCorrChart);
    document.getElementById('mvRenderBtn').addEventListener('click', renderMvChart);
    document.getElementById('tsRenderBtn').addEventListener('click', renderTsChart);
    vizInitialized = true;
  }
}

const GROUPED_CHART_TYPES = ['Grouped Bar', 'Stacked Bar', '100% Stacked Bar'];

function toggleGroupSelect() {
  const isGrouped = GROUPED_CHART_TYPES.includes(document.getElementById('basicType').value);
  document.getElementById('basicGroup').style.display = isGrouped ? 'inline-block' : 'none';
}

async function loadChartGuide() {
  const box = document.getElementById('chartGuideTable');
  if (box.dataset.loaded === 'true') { highlightChartGuide(); return; }
  try {
    const guide = await api('/api/chart/guide');
    box.innerHTML = '';
    guide.forEach(row => {
      const r = el('div', { class: 'chart-guide-row', 'data-type': row.type }, [
        el('div', { class: 'chart-guide-icon' }, row.icon),
        el('div', {}, [
          el('div', { class: 'chart-guide-name' }, row.type),
          el('div', { class: 'chart-guide-desc' }, row.best_for),
        ]),
      ]);
      box.appendChild(r);
    });
    box.dataset.loaded = 'true';
    highlightChartGuide();
  } catch (e) { box.innerHTML = `<div class="placeholder">${e.message}</div>`; }
}

function highlightChartGuide() {
  const current = document.getElementById('basicType').value;
  document.querySelectorAll('.chart-guide-row').forEach(r => {
    r.classList.toggle('active', r.dataset.type === current);
  });
}

async function renderBasicChart() {
  const out = document.getElementById('basicChartOut');
  out.innerHTML = '<div class="placeholder">Rendering…</div>';
  const colorIdx = document.getElementById('basicColor').selectedIndex;
  const chartType = document.getElementById('basicType').value;
  const params = new URLSearchParams({
    type: chartType,
    x: document.getElementById('basicX').value,
    y: document.getElementById('basicY').value,
    color_idx: colorIdx,
    top_n: document.getElementById('basicTopN').value,
    grid: document.getElementById('basicGrid').checked,
  });
  if (GROUPED_CHART_TYPES.includes(chartType)) {
    params.set('group', document.getElementById('basicGroup').value);
  }
  try {
    const data = await api(`/api/chart/basic?${params}`);
    renderChartImage(out, data.image);
  } catch (e) { out.innerHTML = `<div class="placeholder">${e.message}</div>`; }
}

async function renderDistChart() {
  const out = document.getElementById('distChartOut');
  out.innerHTML = '<div class="placeholder">Rendering…</div>';
  const params = new URLSearchParams({ col: document.getElementById('distCol').value, bins: document.getElementById('distBins').value });
  try {
    const data = await api(`/api/chart/distribution?${params}`);
    renderChartImage(out, data.image);
    renderTable(document.getElementById('distStatsTable'), data.stats);
  } catch (e) { out.innerHTML = `<div class="placeholder">${e.message}</div>`; }
}

async function renderCorrChart() {
  const out = document.getElementById('corrChartOut');
  const cols = getMultiselectValues(document.getElementById('corrColsWrap'));
  if (cols.length < 2) { toast('Select at least 2 numeric columns.', false); return; }
  const method = document.querySelector('input[name="corrMethod"]:checked').value;
  out.innerHTML = '<div class="placeholder">Rendering…</div>';
  try {
    const data = await api(`/api/chart/correlation?cols=${encodeURIComponent(cols.join(','))}&method=${method}`);
    renderChartImage(out, data.image);
    renderTable(document.getElementById('corrPairsTable'), data.pairs);
  } catch (e) { out.innerHTML = `<div class="placeholder">${e.message}</div>`; }
}

async function renderMvChart() {
  const out = document.getElementById('mvChartOut');
  out.innerHTML = '<div class="placeholder">Rendering…</div>';
  const params = new URLSearchParams({
    x: document.getElementById('mvX').value,
    y: document.getElementById('mvY').value,
    hue: document.getElementById('mvHue').value,
    size: document.getElementById('mvSize').value,
  });
  try {
    const data = await api(`/api/chart/multivariable?${params}`);
    renderChartImage(out, data.image);
  } catch (e) { out.innerHTML = `<div class="placeholder">${e.message}</div>`; }
}

async function renderTsChart() {
  const out = document.getElementById('tsChartOut');
  out.innerHTML = '<div class="placeholder">Rendering…</div>';
  const params = new URLSearchParams({
    date_col: document.getElementById('tsDate').value,
    val_col: document.getElementById('tsVal').value,
    agg: document.getElementById('tsAgg').value,
  });
  try {
    const data = await api(`/api/chart/timeseries?${params}`);
    renderChartImage(out, data.image);
  } catch (e) { out.innerHTML = `<div class="placeholder">${e.message}</div>`; }
}

let analyzeInitialized = false;
async function initAnalyzePage() {
  const cols = state.columns || await api('/api/columns');
  state.columns = cols;

  populateSelect(document.getElementById('grpBy'), cols.categorical);
  populateSelect(document.getElementById('grpVal'), cols.numeric);
  renderMultiselect(document.getElementById('grpHeatColsWrap'), 'grpHeat', cols.numeric, cols.numeric.slice(0, 6));

  populateSelect(document.getElementById('outCol'), cols.numeric);

  populateSelect(document.getElementById('vcCol'), cols.all);

  renderMultiselect(document.getElementById('kpiColsWrap'), 'kpi', cols.numeric, cols.numeric.slice(0, 4));
  populateSelect(document.getElementById('kpiFilterCol'), cols.categorical, { includeNone: true });

  loadAnalysisOverview();

  if (!analyzeInitialized) {
    document.getElementById('grpTopN').addEventListener('input', (e) => document.getElementById('grpTopNVal').textContent = e.target.value);
    document.getElementById('outThresh').addEventListener('input', (e) => document.getElementById('outThreshVal').textContent = e.target.value);
    document.getElementById('vcTopN').addEventListener('input', (e) => document.getElementById('vcTopNVal').textContent = e.target.value);

    document.getElementById('grpRenderBtn').addEventListener('click', renderGroupAnalysis);
    document.getElementById('grpHeatBtn').addEventListener('click', renderGroupHeatmap);
    document.getElementById('outRenderBtn').addEventListener('click', renderOutliers);
    document.getElementById('vcRenderBtn').addEventListener('click', renderValueCounts);
    document.getElementById('kpiRenderBtn').addEventListener('click', renderKpi);
    document.getElementById('kpiFilterCol').addEventListener('change', onKpiFilterColChange);

    loadDataProfile();
    analyzeInitialized = true;
  }
}

async function loadAnalysisOverview() {
  try {
    const data = await api('/api/analysis/overview');
    const s = data.summary;
    renderMetrics(document.getElementById('anOverviewMetrics'), [
      { value: s.rows, label: 'Rows' },
      { value: s.columns, label: 'Columns' },
      { value: s.missing, label: 'Missing', sub: `${s.missing_pct}%` },
      { value: s.duplicates, label: 'Duplicates' },
      { value: `${s.memory_kb} KB`, label: 'Memory' },
    ]);
    renderTable(document.getElementById('anNumericStats'), data.numeric_stats);
    renderTable(document.getElementById('anCategoricalStats'), data.categorical_stats);
  } catch (e) { toast(e.message, false); }
}

async function renderGroupAnalysis() {
  const out = document.getElementById('grpChartOut');
  out.innerHTML = '<div class="placeholder">Rendering…</div>';
  const params = new URLSearchParams({
    group_by: document.getElementById('grpBy').value,
    value: document.getElementById('grpVal').value,
    agg: document.getElementById('grpAgg').value,
    top_n: document.getElementById('grpTopN').value,
  });
  try {
    const data = await api(`/api/analysis/group?${params}`);
    renderChartImage(out, data.image);
    renderTable(document.getElementById('grpTable'), data.table);
  } catch (e) { out.innerHTML = `<div class="placeholder">${e.message}</div>`; }
}

async function renderGroupHeatmap() {
  const out = document.getElementById('grpHeatOut');
  const cols = getMultiselectValues(document.getElementById('grpHeatColsWrap'));
  if (!cols.length) { toast('Select at least one numeric column.', false); return; }
  out.innerHTML = '<div class="placeholder">Rendering…</div>';
  try {
    const data = await api(`/api/analysis/group-heatmap?group_by=${document.getElementById('grpBy').value}&cols=${encodeURIComponent(cols.join(','))}`);
    renderChartImage(out, data.image);
  } catch (e) { out.innerHTML = `<div class="placeholder">${e.message}</div>`; }
}

async function renderOutliers() {
  const out = document.getElementById('outChartOut');
  out.innerHTML = '<div class="placeholder">Rendering…</div>';
  const params = new URLSearchParams({
    col: document.getElementById('outCol').value,
    method: document.getElementById('outMethod').value,
    threshold: document.getElementById('outThresh').value,
  });
  try {
    const data = await api(`/api/analysis/outliers?${params}`);
    renderChartImage(out, data.image);
    renderMetrics(document.getElementById('outMetrics'), [
      { value: data.n_outliers, label: 'Outliers Found', sub: `${data.pct_outliers}%` },
      { value: data.n_normal, label: 'Normal Points' },
      { value: data.mean_excl_outliers ?? '-', label: 'Mean (excl outliers)' },
    ]);
    renderTable(document.getElementById('outRowsTable'), data.outlier_rows);
  } catch (e) { out.innerHTML = `<div class="placeholder">${e.message}</div>`; }
}

async function loadDataProfile() {
  try {
    const rows = await api('/api/analysis/profile');
    renderTable(document.getElementById('profileTable'), rows);
  } catch (e) { toast(e.message, false); }
}

async function renderValueCounts() {
  const out = document.getElementById('vcChartOut');
  out.innerHTML = '<div class="placeholder">Rendering…</div>';
  const params = new URLSearchParams({ col: document.getElementById('vcCol').value, top_n: document.getElementById('vcTopN').value });
  try {
    const data = await api(`/api/analysis/value-counts?${params}`);
    renderChartImage(out, data.image);
  } catch (e) { out.innerHTML = `<div class="placeholder">${e.message}</div>`; }
}

async function onKpiFilterColChange() {
  const col = document.getElementById('kpiFilterCol').value;
  const valSelect = document.getElementById('kpiFilterVal');
  if (!col || col === 'None') { valSelect.style.display = 'none'; return; }
  const data = await api('/api/data');
  const uniqueVals = [...new Set(data.rows.map(r => r[col]))].filter(v => v !== null && v !== undefined);
  populateSelect(valSelect, uniqueVals);
  valSelect.style.display = 'inline-block';
}

async function renderKpi() {
  const cols = getMultiselectValues(document.getElementById('kpiColsWrap'));
  if (!cols.length) { toast('Select at least one KPI column.', false); return; }
  const filterCol = document.getElementById('kpiFilterCol').value;
  const filterVal = document.getElementById('kpiFilterVal').value;
  const params = new URLSearchParams({ cols: cols.join(',') });
  if (filterCol && filterCol !== 'None') { params.set('filter_col', filterCol); params.set('filter_val', filterVal); }
  const out = document.getElementById('kpiChartOut');
  out.innerHTML = '<div class="placeholder">Rendering…</div>';
  try {
    const data = await api(`/api/analysis/kpi?${params}`);
    renderMetrics(document.getElementById('kpiCards'), data.cards.map(c => ({ value: c.total.toLocaleString(), label: c.column, sub: `avg: ${c.avg.toLocaleString()}` })));
    renderChartImage(out, data.image);
  } catch (e) { out.innerHTML = `<div class="placeholder">${e.message}</div>`; }
}

let chatInitialized = false;
async function initChatPage() {
  const status = await api('/api/chat/status');
  const banner = document.getElementById('chatStatus');
  banner.textContent = status.available ? `✅ ${status.message}` : `⚠️ ${status.message}`;
  banner.className = status.available ? 'success-banner' : 'error-banner';

  if (!chatInitialized) {
    document.querySelectorAll('.chat-side button[data-action]').forEach(b => {
      b.addEventListener('click', () => runQuickAction(b.dataset.action));
    });

    document.getElementById('chatSendBtn').addEventListener('click', () => {
      const input = document.getElementById('chatInput');
      if (input.value.trim()) { sendChatMessage(input.value.trim()); input.value = ''; }
    });
    document.getElementById('chatInput').addEventListener('keydown', (e) => {
      if (e.key === 'Enter') document.getElementById('chatSendBtn').click();
    });

    document.getElementById('staticInsightsBtn').addEventListener('click', async () => {
      const box = document.getElementById('staticInsightsBox');
      const data = await api('/api/chat/insights');
      box.innerHTML = `<div class="info-banner" style="white-space:pre-wrap;">${data.insights}</div>`;
      box.style.display = 'block';
    });

    document.getElementById('clearChatBtn').addEventListener('click', async () => {
      await api('/api/chat', { method: 'DELETE' });
      renderChatMessages([]);
    });

    document.getElementById('exportChatBtn').addEventListener('click', async () => {
      const history = await api('/api/chat');
      const text = history.map(m => `${m.role === 'user' ? 'You' : 'AI'}: ${m.content}`).join('\n\n');
      const blob = new Blob([text], { type: 'text/plain' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'chat_history.txt';
      a.click();
    });

    chatInitialized = true;
  }

  const history = await api('/api/chat');
  renderChatMessages(history);
}

let chatHistoryCache = [];

function renderChatMessages(messages, isTyping = false) {
  chatHistoryCache = messages;
  const box = document.getElementById('chatMessages');
  box.innerHTML = '';
  if (!messages.length && !isTyping) {
    box.appendChild(el('div', { class: 'chat-empty' }, [
      el('div', { style: 'font-size:2.5rem;margin-bottom:8px;' }, '🤖'),
      'Ask me anything about your dataset!',
      el('br'),
      el('span', { class: 'muted' }, 'Or use the Quick Actions on the right →'),
    ]));
    return;
  }
  messages.forEach(m => {
    box.appendChild(el('div', { class: `chat-msg ${m.role}` }, [
      el('div', { class: 'role' }, m.role === 'user' ? 'You' : 'AI'),
      m.content,
    ]));
  });
  if (isTyping) {
    box.appendChild(el('div', { class: 'chat-msg assistant chat-typing' }, [
      el('div', { class: 'role' }, 'AI'),
      el('div', { class: 'typing-dots' }, [el('span'), el('span'), el('span')]),
    ]));
  }
  box.scrollTop = box.scrollHeight;
}

function setChatBusy(busy) {
  document.getElementById('chatInput').disabled = busy;
  document.getElementById('chatSendBtn').disabled = busy;
  document.getElementById('chatSendBtn').textContent = busy ? 'Thinking…' : 'Send';
  document.querySelectorAll('.chat-side button[data-action]').forEach(b => b.disabled = busy);
}

async function sendChatMessage(message) {
  setChatBusy(true);
  renderChatMessages([...chatHistoryCache, { role: 'user', content: message }], true);
  try {
    const data = await api('/api/chat', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message }),
    });
    renderChatMessages(data.history);
  } catch (e) {
    renderChatMessages(chatHistoryCache);
    toast(e.message, false);
  } finally {
    setChatBusy(false);
  }
}

async function runQuickAction(action) {
  setChatBusy(true);
  renderChatMessages(chatHistoryCache, true);
  try {
    const data = await api('/api/chat/quick-action', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action }),
    });
    renderChatMessages(data.history);
  } catch (e) {
    renderChatMessages(chatHistoryCache);
    toast(e.message, false);
  } finally {
    setChatBusy(false);
  }
}

const appShell = document.getElementById('appShell');
const mobileNavToggle = document.getElementById('mobileNavToggle');
const sidebarOverlay = document.getElementById('sidebarOverlay');
function closeSidebar() { appShell.classList.remove('sidebar-open'); }
mobileNavToggle.addEventListener('click', () => appShell.classList.toggle('sidebar-open'));
sidebarOverlay.addEventListener('click', closeSidebar);
document.getElementById('nav').addEventListener('click', () => { if (window.innerWidth <= 768) closeSidebar(); });
updateNavLocks();
