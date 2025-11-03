const mobileState = {
  explainVisible: false,
  sheetOpen: false,
};

const CONFIG_STORAGE_KEY = 'ai-config';

function loadConfig() {
  try {
    const raw = window.localStorage.getItem(CONFIG_STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (error) {
    return null;
  }
}

function saveConfig(config) {
  window.localStorage.setItem(CONFIG_STORAGE_KEY, JSON.stringify(config));
}

function deleteConfig() {
  window.localStorage.removeItem(CONFIG_STORAGE_KEY);
}

function updateStatus(message, type = 'neutral') {
  const statusEl = document.getElementById('mobile-settings-status');
  if (!statusEl) return;
  statusEl.textContent = message;
  statusEl.classList.remove('mobile-sheet__status--ok', 'mobile-sheet__status--error');
  if (type === 'success') statusEl.classList.add('mobile-sheet__status--ok');
  if (type === 'error') statusEl.classList.add('mobile-sheet__status--error');
}

function openSheet() {
  const sheet = document.getElementById('mobile-sheet');
  const form = document.getElementById('mobile-settings-form');
  if (!sheet || !form) return;
  const config = loadConfig();
  form.reset();
  if (config) {
    form.url.value = config.url || '';
    form.key.value = config.key || '';
    form.model.value = config.model || '';
  }
  updateStatus('');
  sheet.classList.add('mobile-sheet--active');
  sheet.setAttribute('aria-hidden', 'false');
  mobileState.sheetOpen = true;
}

function closeSheet() {
  const sheet = document.getElementById('mobile-sheet');
  if (!sheet) return;
  sheet.classList.remove('mobile-sheet--active');
  sheet.setAttribute('aria-hidden', 'true');
  mobileState.sheetOpen = false;
}

function getFormConfig() {
  const form = document.getElementById('mobile-settings-form');
  if (!form) return null;
  return {
    url: form.url.value.trim(),
    key: form.key.value.trim(),
    model: form.model.value.trim(),
  };
}

function handleTest() {
  const config = getFormConfig();
  if (!config) return;
  if (!config.url || !config.key || !config.model) {
    updateStatus('请先填写完整信息。', 'error');
    return;
  }
  updateStatus('测试中（示例）...');
  window.setTimeout(() => {
    const ok = /^https?:\/\//.test(config.url) && config.key.length >= 6;
    updateStatus(ok ? '测试成功（模拟结果）。' : '测试失败，请检查连接。', ok ? 'success' : 'error');
  }, 600);
}

document.addEventListener('DOMContentLoaded', () => {
  const optionCards = document.querySelectorAll('.option-card');
  optionCards.forEach((card) => {
    card.addEventListener('click', () => {
      optionCards.forEach((node) => node.classList.remove('option-card--selected'));
      card.classList.add('option-card--selected');
    });
  });

  const toggleBtn = document.getElementById('toggle-explain');
  const explain = document.getElementById('mobile-explain');
  if (toggleBtn && explain) {
    toggleBtn.addEventListener('click', () => {
      mobileState.explainVisible = !mobileState.explainVisible;
      explain.classList.toggle('visible', mobileState.explainVisible);
      toggleBtn.textContent = mobileState.explainVisible ? '收起' : '解析';
    });
  }

  const menuBtn = document.getElementById('btn-mobile-menu');
  if (menuBtn) menuBtn.addEventListener('click', openSheet);
  const closeBtn = document.getElementById('btn-close-sheet');
  if (closeBtn) closeBtn.addEventListener('click', closeSheet);

  const testBtn = document.getElementById('btn-mobile-test');
  if (testBtn) testBtn.addEventListener('click', handleTest);

  const saveBtn = document.getElementById('btn-mobile-save');
  if (saveBtn)
    saveBtn.addEventListener('click', () => {
      const config = getFormConfig();
      if (!config) return;
      if (!config.url || !config.key || !config.model) {
        updateStatus('请完整填写必填项。', 'error');
        return;
      }
      saveConfig(config);
      updateStatus('配置已保存（示例存储）。', 'success');
    });

  const deleteBtn = document.getElementById('btn-mobile-delete');
  if (deleteBtn)
    deleteBtn.addEventListener('click', () => {
      deleteConfig();
      const form = document.getElementById('mobile-settings-form');
      if (form) form.reset();
      updateStatus('已删除配置。', 'success');
    });
});
