const state = {
  showExplain: false,
  configModalOpen: false,
  config: null,
  statusTimer: null,
};

const CONFIG_STORAGE_KEY = 'ai-config';

function toggleExplain() {
  state.showExplain = !state.showExplain;
  const details = document.querySelector('#feedback-details');
  const btn = document.querySelector('#btn-show-explain');
  if (!details || !btn) return;
  if (state.showExplain) {
    details.classList.add('feedback__body--visible');
    btn.textContent = '收起解析';
  } else {
    details.classList.remove('feedback__body--visible');
    btn.textContent = '查看解析';
  }
}

function loadConfigFromStorage() {
  try {
    const raw = window.localStorage.getItem(CONFIG_STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch (error) {
    return null;
  }
}

function saveConfigToStorage(config) {
  window.localStorage.setItem(CONFIG_STORAGE_KEY, JSON.stringify(config));
}

function deleteConfigFromStorage() {
  window.localStorage.removeItem(CONFIG_STORAGE_KEY);
}

function openSettingsModal() {
  const modal = document.querySelector('#settings-modal');
  if (!modal) return;
  state.configModalOpen = true;
  modal.classList.add('modal--active');
  modal.setAttribute('aria-hidden', 'false');
  populateSettingsForm();
}

function closeSettingsModal() {
  const modal = document.querySelector('#settings-modal');
  if (!modal) return;
  state.configModalOpen = false;
  modal.classList.remove('modal--active');
  modal.setAttribute('aria-hidden', 'true');
  updateStatusMessage('');
}

function populateSettingsForm() {
  const config = loadConfigFromStorage();
  state.config = config;
  const form = document.querySelector('#settings-form');
  if (!form) return;
  form.reset();
  if (!config) return;
  form.url.value = config.url || '';
  form.key.value = config.key || '';
  form.model.value = config.model || '';
  form.timeout.value = config.timeout || '';
  form.dev_document.value = config.dev_document || '';
}

function getFormConfig() {
  const form = document.querySelector('#settings-form');
  if (!form) return null;
  return {
    url: form.url.value.trim(),
    key: form.key.value.trim(),
    model: form.model.value.trim(),
    timeout: form.timeout.value ? Number(form.timeout.value) : undefined,
    dev_document: form.dev_document.value.trim() || undefined,
  };
}

function updateStatusMessage(message, type = 'neutral') {
  const statusEl = document.querySelector('#settings-status');
  if (!statusEl) return;
  statusEl.textContent = message;
  statusEl.classList.remove('modal__status--ok', 'modal__status--error');
  if (type === 'success') {
    statusEl.classList.add('modal__status--ok');
  } else if (type === 'error') {
    statusEl.classList.add('modal__status--error');
  }
  if (state.statusTimer) {
    window.clearTimeout(state.statusTimer);
  }
  if (message) {
    state.statusTimer = window.setTimeout(() => {
      statusEl.textContent = '';
      statusEl.classList.remove('modal__status--ok', 'modal__status--error');
    }, 3600);
  }
}

function handleTestConfig() {
  const config = getFormConfig();
  if (!config) return;
  if (!config.url || !config.key || !config.model) {
    updateStatusMessage('请先填写完整的 URL、Key 和模型名称。', 'error');
    return;
  }
  updateStatusMessage('正在测试连通性...', 'neutral');
  window.setTimeout(() => {
    const looksValid = /^https?:\/\//.test(config.url) && config.key.length >= 6;
    if (looksValid) {
      updateStatusMessage('测试成功，接口可访问（模拟结果）。', 'success');
    } else {
      updateStatusMessage('测试失败，请检查 URL 或 Key 是否有效。', 'error');
    }
  }, 800);
}

function handleSaveConfig(evt) {
  evt?.preventDefault();
  const config = getFormConfig();
  if (!config) return;
  if (!config.url || !config.key || !config.model) {
    updateStatusMessage('请完整填写必填项再保存。', 'error');
    return;
  }
  saveConfigToStorage(config);
  updateStatusMessage('配置已保存（本地示例存储）。', 'success');
  state.config = config;
}

function handleDeleteConfig() {
  deleteConfigFromStorage();
  populateSettingsForm();
  updateStatusMessage('已删除配置。', 'success');
}

document.addEventListener('DOMContentLoaded', () => {
  const btnExplain = document.querySelector('#btn-show-explain');
  if (btnExplain) {
    btnExplain.addEventListener('click', toggleExplain);
  }
  const options = document.querySelectorAll('.option');
  options.forEach((option) => {
    if (option.classList.contains('option--disabled')) return;
    option.addEventListener('click', () => {
      options.forEach((node) => node.classList.remove('option--selected'));
      option.classList.add('option--selected');
    });
  });

  const openSettings = document.querySelector('#btn-open-settings');
  const closeSettings = document.querySelector('#btn-close-settings');
  const modal = document.querySelector('#settings-modal');
  if (openSettings) openSettings.addEventListener('click', openSettingsModal);
  if (closeSettings) closeSettings.addEventListener('click', closeSettingsModal);
  if (modal) {
    modal.addEventListener('click', (event) => {
      if (event.target === modal) {
        closeSettingsModal();
      }
    });
  }

  const btnTest = document.querySelector('#btn-test-config');
  if (btnTest) btnTest.addEventListener('click', handleTestConfig);
  const btnSave = document.querySelector('#btn-save-config');
  if (btnSave) btnSave.addEventListener('click', handleSaveConfig);
  const btnCancel = document.querySelector('#btn-cancel-config');
  if (btnCancel) btnCancel.addEventListener('click', closeSettingsModal);
  const btnDelete = document.querySelector('#btn-delete-config');
  if (btnDelete) btnDelete.addEventListener('click', handleDeleteConfig);

  state.config = loadConfigFromStorage();
});
