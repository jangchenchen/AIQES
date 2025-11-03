const API_BASE = (window.location.protocol.startsWith('http')
  ? window.location.origin
  : 'http://localhost:5001'
).replace(/\/$/, '');
const STATUS_TIMEOUT = 4000;

const selectors = {
  form: '#config-form',
  url: '#field-url',
  key: '#field-key',
  model: '#field-model',
  timeout: '#field-timeout',
  devdoc: '#field-devdoc',
  status: '#status',
  btnLoad: '#btn-load',
  btnSave: '#btn-save',
  btnTest: '#btn-test',
  btnDelete: '#btn-delete',
};

const state = {
  timer: null,
};

function showStatus(message, type = 'neutral') {
  const statusEl = document.querySelector(selectors.status);
  if (!statusEl) return;
  statusEl.textContent = message;
  statusEl.classList.remove('status--success', 'status--error');
  if (type === 'success') statusEl.classList.add('status--success');
  if (type === 'error') statusEl.classList.add('status--error');
  if (state.timer) window.clearTimeout(state.timer);
  if (message) {
    state.timer = window.setTimeout(() => {
      statusEl.textContent = '';
      statusEl.classList.remove('status--success', 'status--error');
    }, STATUS_TIMEOUT);
  }
}

function getFormData() {
  const form = document.querySelector(selectors.form);
  if (!form) return null;
  const payload = {
    url: form.url.value.trim(),
    key: form.key.value.trim(),
    model: form.model.value.trim(),
  };
  if (form.timeout.value) payload.timeout = Number(form.timeout.value);
  if (form.dev_document.value.trim()) payload.dev_document = form.dev_document.value.trim();
  return payload;
}

function fillForm(data) {
  const form = document.querySelector(selectors.form);
  if (!form || !data) return;
  form.url.value = data.url || '';
  form.key.value = data.key || '';
  form.model.value = data.model || '';
  form.timeout.value = data.timeout ?? '';
  form.dev_document.value = data.dev_document || '';
}

async function fetchConfig() {
  try {
    const response = await fetch(`${API_BASE}/api/ai-config`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload = await response.json();
    if (!payload) {
      showStatus('当前未保存配置。');
      fillForm({});
      return;
    }
    fillForm(payload);
    showStatus('已读取当前配置。', 'success');
  } catch (error) {
    showStatus(`读取失败：${error}`, 'error');
  }
}

async function saveConfig() {
  const payload = getFormData();
  if (!payload?.url || !payload.key || !payload.model) {
    showStatus('请填写完整的 URL、Key 和模型名称。', 'error');
    return;
  }
  try {
    const response = await fetch(`${API_BASE}/api/ai-config`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    showStatus('配置已保存。', 'success');
  } catch (error) {
    showStatus(`保存失败：${error}`, 'error');
  }
}

async function testConfig() {
  const payload = getFormData();
  if (!payload?.url || !payload.key || !payload.model) {
    showStatus('测试前请填写完整信息。', 'error');
    return;
  }
  showStatus('正在测试连通性...', 'neutral');
  try {
    const response = await fetch(`${API_BASE}/api/ai-config/test`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    showStatus(result.message, result.ok ? 'success' : 'error');
  } catch (error) {
    showStatus(`测试失败：${error}`, 'error');
  }
}

async function deleteConfig() {
  if (!window.confirm('确定删除当前配置吗？')) return;
  try {
    const response = await fetch(`${API_BASE}/api/ai-config`, { method: 'DELETE' });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    fillForm({});
    showStatus('已删除配置。', 'success');
  } catch (error) {
    showStatus(`删除失败：${error}`, 'error');
  }
}

function initEvents() {
  document.querySelector(selectors.btnLoad)?.addEventListener('click', fetchConfig);
  document.querySelector(selectors.btnSave)?.addEventListener('click', saveConfig);
  document.querySelector(selectors.btnTest)?.addEventListener('click', testConfig);
  document.querySelector(selectors.btnDelete)?.addEventListener('click', deleteConfig);
}

window.addEventListener('DOMContentLoaded', () => {
  initEvents();
  fetchConfig();
});
