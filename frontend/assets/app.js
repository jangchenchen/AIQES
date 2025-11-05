/**
 * 答题考试系统（AI版）前端逻辑
 */

const API_BASE = 'http://localhost:5001/api';

const STORAGE_KEYS = {
  KNOWLEDGE: 'currentKnowledge',
  SESSION: 'currentSessionId',
};

let uploadLocked = false;

// 全局状态
let currentFilepath = null;
let currentSessionId = null;
let currentQuestion = null;
let selectedOptions = new Set();
let answeredCount = 0;
let correctCount = 0;
let totalCount = 0;

const questionHistory = [];
let historyIndex = -1;
let currentEntry = null;
let isLoadingQuestion = false;

const historyState = {
  entries: [],
  sessions: [],
  loading: false,
  page: 1,
  totalPages: 0,
  pageSize: 10,
  filters: {
    sessionId: '',
    questionType: '',
    isCorrect: '',
    dateFrom: '',
    dateTo: '',
  },
};

let activeView = 'upload';
let previousPracticeView = 'upload';

function resetQuestionHistory() {
  questionHistory.length = 0;
  historyIndex = -1;
  currentEntry = null;
}

function getStoredKnowledge() {
  const raw = localStorage.getItem(STORAGE_KEYS.KNOWLEDGE);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw);
    if (!parsed || !parsed.filepath) {
      localStorage.removeItem(STORAGE_KEYS.KNOWLEDGE);
      return null;
    }
    return parsed;
  } catch (error) {
    console.warn('知识文件状态读取失败，已清除缓存。', error);
    localStorage.removeItem(STORAGE_KEYS.KNOWLEDGE);
    return null;
  }
}

function persistKnowledge(info) {
  try {
    localStorage.setItem(STORAGE_KEYS.KNOWLEDGE, JSON.stringify(info));
  } catch (error) {
    console.warn('知识文件状态写入失败：', error);
  }
}

function applyKnowledgeLock(info) {
  if (!info) return;
  uploadLocked = true;
  currentFilepath = info.filepath;
  if (uploadZone) {
    uploadZone.classList.add('is-locked');
    uploadZone.setAttribute('aria-disabled', 'true');
  }
  if (uploadIndicator) {
    uploadIndicator.classList.remove('hidden');
    if (uploadIndicatorText) {
      uploadIndicatorText.textContent = info.filename || '已上传文件';
    }
  }
  if (fileInfo) {
    fileInfo.classList.remove('hidden');
  }
  const nameEl = document.getElementById('filename');
  const countEl = document.getElementById('entry-count');
  if (nameEl) nameEl.textContent = info.filename || '已保存的知识文件';
  if (countEl) countEl.textContent = info.entryCount ?? '—';
  if (btnGenerate) {
    btnGenerate.disabled = false;
    btnGenerate.textContent = '生成题目';
  }
  if (fileInput) fileInput.value = '';
}

function clearKnowledgeLock() {
  uploadLocked = false;
  currentFilepath = null;
  if (uploadZone) {
    uploadZone.classList.remove('is-locked');
    uploadZone.removeAttribute('aria-disabled');
  }
  if (uploadIndicator) {
    uploadIndicator.classList.add('hidden');
    if (uploadIndicatorText) {
      uploadIndicatorText.textContent = '';
    }
  }
  if (fileInfo) {
    fileInfo.classList.add('hidden');
  }
  if (btnGenerate) {
    btnGenerate.disabled = true;
    btnGenerate.textContent = '生成题目';
  }
}

function restoreKnowledgeState() {
  const info = getStoredKnowledge();
  if (info) {
    applyKnowledgeLock(info);
  } else {
    clearKnowledgeLock();
  }
}

function mapQuestionTypeLabel(type) {
  const map = {
    SINGLE_CHOICE: '单选题',
    MULTI_CHOICE: '多选题',
    CLOZE: '填空题',
    QA: '问答题',
  };
  return map[type] || type || '未知题型';
}

function formatTimestamp(value) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const pad = (n) => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function letterFromIndex(index) {
  if (index == null || index < 0) return '';
  return String.fromCharCode(65 + index);
}

// DOM 元素
const uploadZone = document.getElementById('upload-zone');
const fileInput = document.getElementById('file-input');
const fileInfo = document.getElementById('file-info');
const uploadIndicator = document.getElementById('upload-session-indicator');
const uploadIndicatorText = document.getElementById('upload-session-text');
const btnGenerate = document.getElementById('btn-generate');
const uploadView = document.getElementById('upload-view');
const quizView = document.getElementById('quiz-view');
const resultView = document.getElementById('result-view');
const questionContainer = document.getElementById('question-container');
const historyView = document.getElementById('history-view');
const historyList = document.getElementById('history-list');
const historyEmpty = document.getElementById('history-empty');
const historyLoading = document.getElementById('history-loading');
const historyPageInfo = document.getElementById('history-page-info');
const historyStatus = document.getElementById('history-status');
const historyFilterSession = document.getElementById('history-filter-session');
const historyFilterType = document.getElementById('history-filter-type');
const historyFilterResult = document.getElementById('history-filter-result');
const historyFilterFrom = document.getElementById('history-filter-from');
const historyFilterTo = document.getElementById('history-filter-to');
const btnOpenHistory = document.getElementById('btn-open-history');
const btnHistoryBack = document.getElementById('btn-history-back');
const btnHistoryRefresh = document.getElementById('btn-history-refresh');
const btnHistoryPrev = document.getElementById('btn-history-prev');
const btnHistoryNext = document.getElementById('btn-history-next');
const btnHistoryApply = document.getElementById('btn-history-apply');
const btnHistoryReset = document.getElementById('btn-history-reset');

// 初始化
document.addEventListener('DOMContentLoaded', () => {
  if (!uploadZone || !fileInput || !btnGenerate || !uploadView || !quizView) {
    return;
  }
  initUploadZone();
  initGenerateButton();
  initRestartButton();
  initJumpModal();
  initResetButton();
  initHistoryView();
  showUploadView();
  restoreKnowledgeState();
  restoreSession(); // 恢复之前的会话
});

/**
 * 初始化上传区域
 */
function initUploadZone() {
  if (!uploadZone || !fileInput) return;
  // 点击上传
  uploadZone.addEventListener('click', () => {
    if (uploadLocked) {
      showMessage('upload-error', '当前已锁定知识文件，如需更换请先点击“重置数据”。', 'error');
      setTimeout(() => {
        const msg = document.getElementById('upload-error');
        if (msg) msg.classList.add('hidden');
      }, 2000);
      return;
    }
    fileInput.click();
  });

  // 文件选择
  fileInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (file) {
      await uploadFile(file);
    }
  });

  // 拖拽上传
  uploadZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    if (uploadLocked) return;
    uploadZone.classList.add('dragging');
  });

  uploadZone.addEventListener('dragleave', () => {
    if (uploadLocked) return;
    uploadZone.classList.remove('dragging');
  });

  uploadZone.addEventListener('drop', async (e) => {
    e.preventDefault();
    if (uploadLocked) {
      uploadZone.classList.remove('dragging');
      showMessage('upload-error', '知识文件已锁定，若需重新上传请重置数据。', 'error');
      setTimeout(() => {
        const msg = document.getElementById('upload-error');
        if (msg) msg.classList.add('hidden');
      }, 2000);
      return;
    }
    uploadZone.classList.remove('dragging');

    const file = e.dataTransfer.files[0];
    if (file) {
      await uploadFile(file);
    }
  });
}

/**
 * 上传文件
 */
async function uploadFile(file) {
  if (uploadLocked) {
    showMessage('upload-error', '当前已锁定知识文件，如需更换请先点击“重置数据”。', 'error');
    return;
  }
  // 显示加载状态
  showMessage('upload-error', '正在上传...', 'info');
  btnGenerate.disabled = true;

  try {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE}/upload-knowledge`, {
      method: 'POST',
      body: formData,
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || '上传失败');
    }

    // 保存文件路径
    currentFilepath = data.filepath;
    persistKnowledge({
      filepath: data.filepath,
      filename: file.name,
      entryCount: data.entry_count,
      uploadedAt: Date.now(),
    });
    applyKnowledgeLock({
      filepath: data.filepath,
      filename: file.name,
      entryCount: data.entry_count,
    });

    // 显示文件信息
    const filenameEl = document.getElementById('filename');
    const entryCountEl = document.getElementById('entry-count');
    if (filenameEl) filenameEl.textContent = file.name;
    if (entryCountEl) entryCountEl.textContent = data.entry_count;
    fileInfo.classList.remove('hidden');

    // 启用生成按钮
    if (btnGenerate) btnGenerate.disabled = false;

    showMessage('upload-error', '上传成功！', 'success');
    setTimeout(() => {
      document.getElementById('upload-error').classList.add('hidden');
    }, 2000);

  } catch (error) {
    showMessage('upload-error', `上传失败：${error.message}`, 'error');
    btnGenerate.disabled = true;
  }
}

/**
 * 初始化生成按钮
 */
function initGenerateButton() {
  if (!btnGenerate) return;
  btnGenerate.addEventListener('click', async () => {
    if (!currentFilepath) {
      showMessage('upload-error', '请先上传知识文件', 'error');
      return;
    }

    // 获取配置
    const types = Array.from(document.querySelectorAll('input[name="question-type"]:checked'))
      .map(cb => cb.value);

    if (types.length === 0) {
      showMessage('upload-error', '请至少选择一种题型', 'error');
      return;
    }

    const count = parseInt(document.getElementById('question-count').value);
    const mode = document.getElementById('question-mode').value;

    // 显示加载
    btnGenerate.disabled = true;
    btnGenerate.textContent = '正在生成...';

    try {
      const response = await fetch(`${API_BASE}/generate-questions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          filepath: currentFilepath,
          types,
          count,
          mode,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || '生成失败');
      }

      // 保存会话ID（内存 + localStorage）
      currentSessionId = data.session_id;
      localStorage.setItem(STORAGE_KEYS.SESSION, currentSessionId);
      totalCount = data.total_count;

      // 重置计数
      answeredCount = 0;
      correctCount = 0;
      updateStats();

      // 切换到答题界面
      showQuizView();

      // 初始化历史并加载第一题
      resetQuestionHistory();
      await loadNextQuestion();

    } catch (error) {
      showMessage('upload-error', `生成失败：${error.message}`, 'error');
      if (String(error.message).includes('知识文件不存在')) {
        localStorage.removeItem(STORAGE_KEYS.KNOWLEDGE);
        clearKnowledgeLock();
      }
      const knowledge = getStoredKnowledge();
      btnGenerate.disabled = !knowledge;
      btnGenerate.textContent = '生成题目';
    }
  });
}

/**
 * 显示消息
 */
function showMessage(elementId, message, type = 'error') {
  const element = document.getElementById(elementId);
  element.textContent = message;
  element.className = type === 'error' ? 'error-message' : 'success-message';
  element.classList.remove('hidden');
}

/**
 * 切换到答题界面
 */
function showUploadView() {
  if (!uploadView || !quizView || !resultView) return;
  uploadView.classList.remove('hidden');
  quizView.classList.add('hidden');
  resultView.classList.add('hidden');
  if (historyView) historyView.classList.add('hidden');
  activeView = 'upload';
  previousPracticeView = 'upload';
}

function showQuizView() {
  if (!uploadView || !quizView || !resultView) return;
  uploadView.classList.add('hidden');
  quizView.classList.remove('hidden');
  resultView.classList.add('hidden');
  if (historyView) historyView.classList.add('hidden');
  activeView = 'quiz';
  previousPracticeView = 'quiz';
}

/**
 * 切换到结果界面
 */
function showResultView() {
  if (!uploadView || !quizView || !resultView) return;
  uploadView.classList.add('hidden');
  quizView.classList.add('hidden');
  resultView.classList.remove('hidden');
  if (historyView) historyView.classList.add('hidden');
  activeView = 'result';
  previousPracticeView = 'result';
  resetQuestionHistory();

  // 显示结果
  const score = totalCount > 0 ? Math.round((correctCount / totalCount) * 100) : 0;
  document.getElementById('final-score').textContent = `${score}%`;
  document.getElementById('correct-count').textContent = correctCount;
  document.getElementById('result-total').textContent = totalCount;
}

function showHistoryView() {
  if (!historyView) return;
  if (activeView !== 'history' && ['upload', 'quiz', 'result'].includes(activeView)) {
    previousPracticeView = activeView;
  }
  if (uploadView) uploadView.classList.add('hidden');
  if (quizView) quizView.classList.add('hidden');
  if (resultView) resultView.classList.add('hidden');
  historyView.classList.remove('hidden');
  activeView = 'history';
  setHistoryStatus('', 'info');
  if (!historyState.sessions.length) {
    loadHistorySessions();
  }
  loadHistoryEntries({ resetPage: historyState.entries.length === 0 });
}

function returnToPracticeView() {
  if (previousPracticeView === 'quiz' && currentSessionId) {
    showQuizView();
  } else if (previousPracticeView === 'result') {
    showResultView();
  } else {
    showUploadView();
  }
}

function toggleHistoryLoading(isLoading) {
  historyState.loading = isLoading;
  if (!historyLoading) return;
  historyLoading.classList.toggle('hidden', !isLoading);
}

function setHistoryStatus(message, intent = 'info') {
  if (!historyStatus) return;
  historyStatus.textContent = message || '';
  historyStatus.dataset.intent = intent;
}

function renderHistorySessionOptions() {
  if (!historyFilterSession) return;
  const currentValue = historyState.filters.sessionId;
  historyFilterSession.innerHTML = '<option value="">全部会话</option>';
  historyState.sessions.forEach((session) => {
    const option = document.createElement('option');
    option.value = session.session_id;
    const shortId = session.session_id ? session.session_id.slice(0, 8) : '未命名';
    const knowledgeSource = session.knowledge_file || session.filepath;
    const knowledgeName = typeof knowledgeSource === 'string' && knowledgeSource
      ? knowledgeSource.split('/').slice(-1)[0]
      : '默认知识库';
    option.textContent = `${shortId} · ${knowledgeName}`;
    historyFilterSession.appendChild(option);
  });
  if (currentValue) {
    historyFilterSession.value = currentValue;
  }
}

function deriveSelectedIndices(entry, question) {
  const optionCount = Array.isArray(question.options) ? question.options.length : 0;
  if (entry.extra && Array.isArray(entry.extra.selected_indices)) {
    return entry.extra.selected_indices.filter((idx) => Number.isInteger(idx) && idx >= 0 && idx < optionCount);
  }
  const rawAnswer = (entry.user_answer || '').toString().trim();
  if (!rawAnswer) return [];
  if (question.question_type === 'SINGLE_CHOICE') {
    const letter = rawAnswer[0]?.toUpperCase();
    if (letter && letter >= 'A' && letter <= 'Z') {
      const idx = letter.charCodeAt(0) - 65;
      return idx >= 0 && idx < optionCount ? [idx] : [];
    }
    return [];
  }
  if (question.question_type === 'MULTI_CHOICE') {
    const normalized = rawAnswer.replace(/，/g, ',').replace(/\s+/g, '').toUpperCase();
    const indices = new Set();
    for (const char of normalized) {
      if (char >= 'A' && char <= 'Z') {
        const idx = char.charCodeAt(0) - 65;
        if (idx >= 0 && idx < optionCount) {
          indices.add(idx);
        }
      }
    }
    return Array.from(indices).sort((a, b) => a - b);
  }
  return [];
}

function formatOptionSelection(indices, question, fallback = '未作答') {
  if (!Array.isArray(indices) || !indices.length || !Array.isArray(question.options)) {
    return fallback || '未作答';
  }
  return indices
    .filter((idx) => idx >= 0 && idx < question.options.length)
    .map((idx) => `${letterFromIndex(idx)}. ${question.options[idx]}`)
    .join(' / ');
}

function formatCorrectAnswer(question) {
  if (!question) return '—';
  if (['SINGLE_CHOICE', 'MULTI_CHOICE'].includes(question.question_type)) {
    const indices = Array.isArray(question.correct_options) ? question.correct_options : [];
    const text = formatOptionSelection(indices, question, '—');
    return text || (question.answer_text || '—');
  }
  return question.answer_text || '—';
}

function renderHistoryOptions(entry, container) {
  if (!container) return;
  const question = entry.question || {};
  if (!Array.isArray(question.options) || !question.options.length) {
    container.innerHTML = '<p class="history-card__value">该题不包含选项。</p>';
    return;
  }
  const correctSet = new Set((question.correct_options || []).filter(Number.isInteger));
  const selectedIndices = deriveSelectedIndices(entry, question);
  const selectedSet = new Set(selectedIndices);
  const list = document.createElement('ul');
  list.className = 'history-options';
  question.options.forEach((optionText, index) => {
    const item = document.createElement('li');
    item.className = 'history-option';
    const key = document.createElement('span');
    key.className = 'history-option__key';
    key.textContent = letterFromIndex(index);
    const body = document.createElement('span');
    body.textContent = optionText;
    item.appendChild(key);
    item.appendChild(body);
    const isCorrect = correctSet.has(index);
    const isSelected = selectedSet.has(index);
    if (isCorrect) item.classList.add('is-correct');
    if (isSelected) {
      if (isCorrect) {
        item.classList.add('is-selected-correct');
      } else {
        item.classList.add('is-selected-wrong');
      }
    }
    list.appendChild(item);
  });
  container.innerHTML = '';
  container.appendChild(list);
}

function renderHistoryEntries() {
  if (!historyList) return;
  historyList.innerHTML = '';
  const template = document.getElementById('history-card-template');
  if (!historyState.entries.length) {
    if (historyEmpty) historyEmpty.classList.remove('hidden');
    if (historyPageInfo) historyPageInfo.textContent = '第 0 / 0 页';
    if (btnHistoryPrev) btnHistoryPrev.disabled = true;
    if (btnHistoryNext) btnHistoryNext.disabled = true;
    return;
  }
  if (historyEmpty) historyEmpty.classList.add('hidden');
  historyState.entries.forEach((entry) => {
    const question = entry.question || {};
    const clone = template ? template.content.cloneNode(true) : document.createDocumentFragment();
    const card = clone.querySelector ? clone.querySelector('.history-card') : null;
    if (card) {
      card.classList.add(entry.is_correct ? 'history-card--correct' : 'history-card--incorrect');
    }
    const typeEl = clone.querySelector('[data-type-chip]');
    if (typeEl) typeEl.textContent = mapQuestionTypeLabel(question.question_type);
    const timeEl = clone.querySelector('[data-time]');
    if (timeEl) timeEl.textContent = formatTimestamp(entry.timestamp);
    const sessionEl = clone.querySelector('[data-session]');
    const sessionId = entry.session_id ? entry.session_id.slice(0, 8) : '无会话ID';
    if (sessionEl) sessionEl.textContent = `会话 ${sessionId}`;
    const resultEl = clone.querySelector('[data-result]');
    if (resultEl) {
      resultEl.textContent = entry.is_correct ? '回答正确' : '回答错误';
      resultEl.classList.toggle('is-correct', Boolean(entry.is_correct));
      resultEl.classList.toggle('is-wrong', !entry.is_correct);
    }
    const modeEl = clone.querySelector('[data-mode]');
    const sessionContext = entry.session_context || {};
    if (modeEl) modeEl.textContent = sessionContext.mode ? `模式 · ${sessionContext.mode}` : '模式 · 未知';
    const knowledgeEl = clone.querySelector('[data-knowledge]');
    if (knowledgeEl) {
      const knowledgeSource = sessionContext.knowledge_file || sessionContext.filepath || '默认知识库';
      const knowledgeName = typeof knowledgeSource === 'string'
        ? knowledgeSource.split('/').slice(-1)[0]
        : '默认知识库';
      knowledgeEl.textContent = `知识库 · ${knowledgeName}`;
    }
    const promptEl = clone.querySelector('[data-prompt]');
    if (promptEl) promptEl.textContent = question.prompt || '（题干缺失）';
    const optionsEl = clone.querySelector('[data-options]');
    renderHistoryOptions(entry, optionsEl);

    const selectedIndices = deriveSelectedIndices(entry, question);
    const userAnswerEl = clone.querySelector('[data-user-answer]');
    if (userAnswerEl) {
      if (['SINGLE_CHOICE', 'MULTI_CHOICE'].includes(question.question_type)) {
        userAnswerEl.textContent = formatOptionSelection(selectedIndices, question, entry.user_answer || '未作答');
      } else {
        userAnswerEl.textContent = entry.user_answer ? entry.user_answer : '未作答';
      }
    }
    const correctAnswerEl = clone.querySelector('[data-correct-answer]');
    if (correctAnswerEl) {
      correctAnswerEl.textContent = formatCorrectAnswer(question);
    }
    const explanationEl = clone.querySelector('[data-explanation]');
    if (explanationEl) {
      const explanation = entry.plain_explanation || question.explanation || '暂无解析。';
      explanationEl.textContent = explanation;
    }

    historyList.appendChild(clone);
  });

  if (historyPageInfo) {
    historyPageInfo.textContent = `第 ${historyState.page} / ${historyState.totalPages || 1} 页`;
  }
  if (btnHistoryPrev) btnHistoryPrev.disabled = historyState.page <= 1;
  if (btnHistoryNext) btnHistoryNext.disabled = historyState.page >= (historyState.totalPages || 1);
}

async function loadHistorySessions() {
  if (!historyView) return;
  try {
    const response = await fetch(`${API_BASE}/answer-history/sessions`);
    if (!response.ok) throw new Error(`${response.status}`);
    const payload = await response.json();
    historyState.sessions = Array.isArray(payload.data) ? payload.data : [];
    renderHistorySessionOptions();
  } catch (error) {
    console.warn('加载历史会话失败：', error);
  }
}

async function loadHistoryEntries(options = {}) {
  if (!historyView) return;
  if (historyState.loading) return;
  const { resetPage = false } = options;
  if (resetPage) {
    historyState.page = 1;
  }
  const params = new URLSearchParams({
    page: String(historyState.page),
    page_size: String(historyState.pageSize),
  });
  const { filters } = historyState;
  if (filters.sessionId) params.set('session_id', filters.sessionId);
  if (filters.questionType) params.set('question_type', filters.questionType);
  if (filters.isCorrect) params.set('is_correct', filters.isCorrect);
  if (filters.dateFrom) params.set('date_from', filters.dateFrom);
  if (filters.dateTo) params.set('date_to', filters.dateTo);

  toggleHistoryLoading(true);
  setHistoryStatus('', 'info');
  try {
    const response = await fetch(`${API_BASE}/answer-history?${params.toString()}`);
    if (!response.ok) {
      const text = await response.text();
      throw new Error(text || `HTTP ${response.status}`);
    }
    const payload = await response.json();
    const data = payload.data || {};
    historyState.entries = Array.isArray(data.entries) ? data.entries : [];
    const pagination = data.pagination || {};
    const totalPages = pagination.total_pages || 0;
    historyState.totalPages = totalPages || (historyState.entries.length ? 1 : 0);
    historyState.page = pagination.page || historyState.page;
    if (historyState.totalPages && historyState.page > historyState.totalPages) {
      historyState.page = historyState.totalPages;
    }
    renderHistoryEntries();
    if (!historyState.entries.length) {
      setHistoryStatus('尚无符合条件的历史记录。', 'info');
    }
  } catch (error) {
    console.error('加载历史记录失败：', error);
    historyState.entries = [];
    renderHistoryEntries();
    setHistoryStatus(`加载历史记录失败：${error.message}`, 'error');
  } finally {
    toggleHistoryLoading(false);
  }
}

function applyHistoryFiltersFromUI() {
  historyState.filters.sessionId = historyFilterSession?.value || '';
  historyState.filters.questionType = historyFilterType?.value || '';
  historyState.filters.isCorrect = historyFilterResult?.value || '';
  historyState.filters.dateFrom = historyFilterFrom?.value || '';
  historyState.filters.dateTo = historyFilterTo?.value || '';
}

function resetHistoryFiltersUI() {
  if (historyFilterSession) historyFilterSession.value = '';
  if (historyFilterType) historyFilterType.value = '';
  if (historyFilterResult) historyFilterResult.value = '';
  if (historyFilterFrom) historyFilterFrom.value = '';
  if (historyFilterTo) historyFilterTo.value = '';
  historyState.filters = {
    sessionId: '',
    questionType: '',
    isCorrect: '',
    dateFrom: '',
    dateTo: '',
  };
}

function initHistoryView() {
  if (!historyView) return;
  if (btnOpenHistory) {
    btnOpenHistory.addEventListener('click', () => {
      showHistoryView();
    });
  }
  if (btnHistoryBack) {
    btnHistoryBack.addEventListener('click', () => {
      returnToPracticeView();
    });
  }
  if (btnHistoryRefresh) {
    btnHistoryRefresh.addEventListener('click', () => {
      loadHistorySessions();
      loadHistoryEntries({ resetPage: false });
    });
  }
  if (btnHistoryPrev) {
    btnHistoryPrev.addEventListener('click', () => {
      if (historyState.page > 1) {
        historyState.page -= 1;
        loadHistoryEntries();
      }
    });
  }
  if (btnHistoryNext) {
    btnHistoryNext.addEventListener('click', () => {
      if (historyState.page < historyState.totalPages) {
        historyState.page += 1;
        loadHistoryEntries();
      }
    });
  }
  if (btnHistoryApply) {
    btnHistoryApply.addEventListener('click', () => {
      applyHistoryFiltersFromUI();
      loadHistoryEntries({ resetPage: true });
    });
  }
  if (btnHistoryReset) {
    btnHistoryReset.addEventListener('click', () => {
      resetHistoryFiltersUI();
      loadHistoryEntries({ resetPage: true });
    });
  }

  resetHistoryFiltersUI();
}

/**
 * 加载下一题
 */
async function loadNextQuestion(options = {}) {
  const { action = 'next', fromHistory = false } = options;

  if (fromHistory) {
    const entry = questionHistory[historyIndex];
    if (!entry) return;
    currentEntry = entry;
    currentQuestion = entry.question;
    selectedOptions = new Set(entry.selectedOptions || []);
    renderQuestion(entry);
    restoreAnswerState(entry);
    updateNavigationState();
    return;
  }

  if (isLoadingQuestion) return;
  isLoadingQuestion = true;

  try {
    const payload = {
      session_id: currentSessionId,
    };
    if (action === 'skip') {
      payload.skip = true;
    }

    const response = await fetch(`${API_BASE}/get-question`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || '加载失败');
    }

    if (data.finished) {
      showResultView();
      return;
    }

    totalCount = data.total_count ?? totalCount;
    currentQuestion = data.question;
    selectedOptions.clear();

    const entry = {
      question: data.question,
      currentIndex: data.current_index,
      total: data.total_count,
      answered: false,
      userAnswer: null,
      selectedOptions: [],
      isCorrect: null,
      feedback: null,
      nextAvailable: data.next_available ?? true,
    };

    if (historyIndex < questionHistory.length - 1) {
      questionHistory.splice(historyIndex + 1);
    }
    questionHistory.push(entry);
    historyIndex = questionHistory.length - 1;
    currentEntry = entry;

    renderQuestion(entry);
    updateNavigationState();

  } catch (error) {
    questionContainer.innerHTML = `<div class="error-message">加载失败：${error.message}</div>`;
  } finally {
    isLoadingQuestion = false;
  }
}

/**
 * 渲染题目
 */
function renderQuestion(entry) {
  if (!entry) return;
  const { question, currentIndex, total } = entry;
  const typeNames = {
    'SINGLE_CHOICE': '单选题',
    'MULTI_CHOICE': '多选题',
    'CLOZE': '填空题',
    'QA': '问答题',
  };

  let html = `
    <div class="question-card">
      <div class="question-header">
        <span class="question-type-badge">${typeNames[question.question_type] || question.question_type}</span>
        <span class="question-progress">第 ${currentIndex} 题 / 共 ${total} 题</span>
      </div>

      <div class="question-prompt">${question.prompt}</div>
  `;

  if (question.question_type === 'SINGLE_CHOICE' || question.question_type === 'MULTI_CHOICE') {
    // 选择题
    html += '<ul class="options-list">';
    question.options.forEach((option, index) => {
      const label = String.fromCharCode(65 + index); // A, B, C, D
      html += `
        <li class="option-item" data-index="${index}">
          <span class="option-label">${label}</span>
          <span>${option}</span>
        </li>
      `;
    });
    html += '</ul>';

    if (question.question_type === 'MULTI_CHOICE') {
      html += '<div style="font-size: 14px; color: var(--muted); margin-bottom: 16px;">多选题：可以选择多个答案</div>';
    }

  } else {
    // 填空题或问答题
    const placeholder = question.question_type === 'CLOZE' ? '请输入答案...' : '请输入详细回答...';
    html += `<textarea class="answer-input" id="answer-input" rows="4" placeholder="${placeholder}"></textarea>`;
  }

  html += `
    </div>
    <div class="question-controls">
      <div class="question-controls__left">
        <button class="btn btn-outline" id="btn-overview" type="button">题目概览</button>
      </div>
      <div class="question-controls__right">
        <button class="btn btn-secondary" id="btn-prev-question" type="button">上一题</button>
        <button class="btn btn-primary" id="btn-submit" type="button">提交答案</button>
        <button class="btn btn-secondary hidden" id="btn-next-question" type="button">下一题</button>
        <button class="btn btn-primary hidden" id="btn-finish" type="button">查看结果</button>
      </div>
    </div>
    <div class="feedback-box" id="feedback-box"></div>
  `;

  questionContainer.innerHTML = html;
  selectedOptions = new Set(entry.selectedOptions || []);

  if (question.question_type === 'CLOZE' || question.question_type === 'QA') {
    const input = document.getElementById('answer-input');
    if (input) {
      if (entry.userAnswer) input.value = entry.userAnswer;
      input.addEventListener('input', () => {
        if (currentEntry?.answered) return;
        currentEntry.userAnswer = input.value;
      });
    }
  }

  // 绑定事件
  if (question.question_type === 'SINGLE_CHOICE') {
    bindSingleChoiceEvents();
  } else if (question.question_type === 'MULTI_CHOICE') {
    bindMultiChoiceEvents();
  }

  bindSubmitEvent();
  bindNavigationEvents();
  restoreAnswerState(entry);
  updateNavigationState();
}

/**
 * 绑定单选题事件
 */
function bindSingleChoiceEvents() {
  if (!currentEntry) return;
  const options = document.querySelectorAll('.option-item');
  options.forEach(option => {
    option.addEventListener('click', () => {
      if (currentEntry.answered) return;
      // 清除其他选项
      options.forEach(opt => opt.classList.remove('selected'));
      // 选中当前选项
      option.classList.add('selected');
      selectedOptions.clear();
      selectedOptions.add(parseInt(option.dataset.index));
      currentEntry.selectedOptions = Array.from(selectedOptions);
    });
  });
}

/**
 * 绑定多选题事件
 */
function bindMultiChoiceEvents() {
  if (!currentEntry) return;
  const options = document.querySelectorAll('.option-item');
  options.forEach(option => {
    option.addEventListener('click', () => {
      if (currentEntry.answered) return;
      const index = parseInt(option.dataset.index);
      if (selectedOptions.has(index)) {
        selectedOptions.delete(index);
        option.classList.remove('selected');
      } else {
        selectedOptions.add(index);
        option.classList.add('selected');
      }
      currentEntry.selectedOptions = Array.from(selectedOptions);
    });
  });
}

/**
 * 绑定提交事件
 */
function bindSubmitEvent() {
  const btnSubmit = document.getElementById('btn-submit');
  if (!btnSubmit) return;
  if (currentEntry?.answered) {
    btnSubmit.style.display = 'none';
    return;
  }
  btnSubmit.addEventListener('click', async () => {
    let userAnswer = '';

    if (currentQuestion.question_type === 'SINGLE_CHOICE') {
      if (selectedOptions.size === 0) {
        alert('请先选择答案');
        return;
      }
      const index = Array.from(selectedOptions)[0];
      userAnswer = String.fromCharCode(65 + index); // A, B, C, D

    } else if (currentQuestion.question_type === 'MULTI_CHOICE') {
      if (selectedOptions.size === 0) {
        alert('请先选择答案');
        return;
      }
      const indices = Array.from(selectedOptions).sort((a, b) => a - b);
      userAnswer = indices.map(i => String.fromCharCode(65 + i)).join('');

    } else {
      const input = document.getElementById('answer-input');
      userAnswer = input.value.trim();
      if (!userAnswer) {
        alert('请先输入答案');
        return;
      }
    }

    // 提交答案
    await submitAnswer(userAnswer);
  });
}

function bindNavigationEvents() {
  const btnPrev = document.getElementById('btn-prev-question');
  const btnNext = document.getElementById('btn-next-question');
  const btnFinish = document.getElementById('btn-finish');
  const btnOverview = document.getElementById('btn-overview');
  if (btnPrev) {
    btnPrev.onclick = handlePrevious;
  }
  if (btnNext) {
    btnNext.onclick = goForward;
  }
  if (btnFinish) {
    btnFinish.onclick = showResultView;
  }
  if (btnOverview) {
    btnOverview.onclick = openJumpModal;
  }
}

/**
 * 提交答案
 */
async function submitAnswer(userAnswer) {
  const btnSubmit = document.getElementById('btn-submit');
  btnSubmit.disabled = true;
  btnSubmit.textContent = '提交中...';

  try {
    const response = await fetch(`${API_BASE}/submit-answer`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        session_id: currentSessionId,
        answer: userAnswer,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || '提交失败');
    }

    // 更新计数
    answeredCount++;
    if (data.is_correct) {
      correctCount++;
    }
    updateStats();

    if (currentEntry) {
      currentEntry.answered = true;
      currentEntry.userAnswer = userAnswer;
      currentEntry.selectedOptions = Array.from(selectedOptions);
      currentEntry.isCorrect = data.is_correct;
      currentEntry.feedback = {
        explanation: data.explanation,
        correctAnswer: data.correct_answer,
      };
      currentEntry.nextAvailable = data.next_available;
    }

    // 显示反馈
    showFeedback(data.is_correct, data.explanation, data.correct_answer, data.next_available);

    btnSubmit.style.display = 'none';

    updateNavigationState();

  } catch (error) {
    alert(`提交失败：${error.message}`);
    btnSubmit.disabled = false;
    btnSubmit.textContent = '提交答案';
  }
}

/**
 * 显示反馈
 */
function showFeedback(isCorrect, explanation, correctAnswer, nextAvailable = true) {
  const feedbackBox = document.getElementById('feedback-box');
  feedbackBox.className = `feedback-box ${isCorrect ? 'correct' : 'incorrect'}`;

  let html = `
    <div class="feedback-title">${isCorrect ? '✓ 回答正确' : '✗ 回答错误'}</div>
    <div>${explanation}</div>
  `;

  if (!isCorrect && correctAnswer) {
    html += `<div style="margin-top: 12px; font-weight: 600;">正确答案：${correctAnswer}</div>`;
  }

  if (currentQuestion.explanation) {
    html += `<div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--border);">
      <div style="font-weight: 600; margin-bottom: 4px;">解析：</div>
      <div>${currentQuestion.explanation}</div>
    </div>`;
  }

  feedbackBox.innerHTML = html;
}

function restoreAnswerState(entry) {
  if (!entry) return;
  const question = entry.question;
  if (!question) return;

  if (question.question_type === 'SINGLE_CHOICE') {
    const options = document.querySelectorAll('.option-item');
    options.forEach((opt) => opt.classList.remove('selected'));
    (entry.selectedOptions || []).forEach((index) => {
      const option = document.querySelector(`.option-item[data-index="${index}"]`);
      if (option) {
        option.classList.add('selected');
      }
    });
    selectedOptions = new Set(entry.selectedOptions || []);
    options.forEach((opt) => {
      if (entry.answered) {
        opt.classList.add('option-disabled');
        opt.style.pointerEvents = 'none';
      } else {
        opt.classList.remove('option-disabled');
        opt.style.pointerEvents = '';
      }
    });
  } else if (question.question_type === 'MULTI_CHOICE') {
    const options = document.querySelectorAll('.option-item');
    options.forEach((opt) => opt.classList.remove('selected'));
    (entry.selectedOptions || []).forEach((index) => {
      const option = document.querySelector(`.option-item[data-index="${index}"]`);
      if (option) option.classList.add('selected');
    });
    selectedOptions = new Set(entry.selectedOptions || []);
    options.forEach((opt) => {
      if (entry.answered) {
        opt.classList.add('option-disabled');
        opt.style.pointerEvents = 'none';
      } else {
        opt.classList.remove('option-disabled');
        opt.style.pointerEvents = '';
      }
    });
  } else {
    const input = document.getElementById('answer-input');
    if (input && entry.userAnswer) {
      input.value = entry.userAnswer;
    }
    if (input) {
      if (entry.answered) {
        input.setAttribute('readonly', 'readonly');
      } else {
        input.removeAttribute('readonly');
      }
    }
  }

  if (entry.answered) {
    showFeedback(
      entry.isCorrect,
      entry.feedback?.explanation,
      entry.feedback?.correctAnswer,
      entry.nextAvailable,
    );
    const btnSubmit = document.getElementById('btn-submit');
    if (btnSubmit) btnSubmit.style.display = 'none';
  } else {
    const btnSubmit = document.getElementById('btn-submit');
    if (btnSubmit) {
      btnSubmit.style.display = 'inline-block';
      btnSubmit.disabled = false;
      btnSubmit.textContent = '提交答案';
    }
  }

  updateNavigationState();
}

function handlePrevious() {
  if (historyIndex <= 0) return;
  historyIndex -= 1;
  loadNextQuestion({ fromHistory: true });
}

function handleSkip() {
  if (isLoadingQuestion) return;
  openJumpModal();
}

function goForward() {
  if (historyIndex < questionHistory.length - 1) {
    historyIndex += 1;
    loadNextQuestion({ fromHistory: true });
  } else {
    loadNextQuestion();
  }
}

function openJumpModal() {
  const modal = document.getElementById('jump-modal');
  if (!modal) return;
  renderJumpList();
  modal.classList.add('modal--active');
  modal.setAttribute('aria-hidden', 'false');
}

function closeJumpModal() {
  const modal = document.getElementById('jump-modal');
  if (!modal) return;
  modal.classList.remove('modal--active');
  modal.setAttribute('aria-hidden', 'true');
}

function renderJumpList() {
  const container = document.getElementById('jump-list');
  if (!container) return;
  container.innerHTML = '';
  const total = currentEntry?.total || totalCount || questionHistory[questionHistory.length - 1]?.total || 0;
  if (!total) {
    container.innerHTML = '<div class="empty">暂无题目</div>';
    return;
  }
  for (let i = 1; i <= total; i += 1) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'jump-item';
    button.textContent = i;
    button.dataset.index = i;
    const existingIndex = questionHistory.findIndex((entry) => entry.currentIndex === i);
    if (existingIndex !== -1) {
      button.dataset.historyIndex = existingIndex;
      if (existingIndex === historyIndex) {
        button.classList.add('is-current');
      }
    } else if (i === questionHistory.length + 1) {
      button.dataset.next = 'true';
    } else if (i > questionHistory.length + 1) {
      button.disabled = true;
      button.title = '未生成';
    }
    button.addEventListener('click', () => {
      jumpToQuestionNumber(i);
      closeJumpModal();
    });
    container.appendChild(button);
  }
  updateJumpModalState();
}

function initJumpModal() {
  const modal = document.getElementById('jump-modal');
  if (!modal) return;
  const closeBtn = document.getElementById('btn-close-jump');
  const cancelBtn = document.getElementById('btn-cancel-jump');
  if (closeBtn) closeBtn.addEventListener('click', closeJumpModal);
  if (cancelBtn) cancelBtn.addEventListener('click', closeJumpModal);
  modal.addEventListener('click', (event) => {
    if (event.target === modal) {
      closeJumpModal();
    }
  });
}

async function jumpToQuestionNumber(targetIndex) {
  const existingIndex = questionHistory.findIndex((entry) => entry.currentIndex === targetIndex);
  if (existingIndex !== -1) {
    historyIndex = existingIndex;
    loadNextQuestion({ fromHistory: true });
    return;
  }

  const total = currentEntry?.total || totalCount || 0;
  if (!total) {
    alert('题目总数未知，请先生成题目。');
    return;
  }

  if (targetIndex <= questionHistory.length) {
    historyIndex = targetIndex - 1;
    loadNextQuestion({ fromHistory: true });
    return;
  }

  if (targetIndex === questionHistory.length + 1) {
    await loadNextQuestion();
    return;
  }

  alert('该题尚未生成，请先按顺序练习至对应题号。');
}

function updateNavigationState() {
  const btnPrev = document.getElementById('btn-prev-question');
  const btnSubmit = document.getElementById('btn-submit');
  const btnNext = document.getElementById('btn-next-question');
  const btnFinish = document.getElementById('btn-finish');
  const btnOverview = document.getElementById('btn-overview');

  if (btnPrev) {
    const canBack = historyIndex > 0;
    btnPrev.disabled = !canBack;
    btnPrev.classList.toggle('hidden', !canBack);
  }
  if (btnSubmit) {
    const showSubmit = !currentEntry?.answered;
    btnSubmit.classList.toggle('hidden', !showSubmit);
    btnSubmit.disabled = !showSubmit;
  }
  if (btnNext) {
    const showNext = Boolean(currentEntry?.answered && currentEntry.nextAvailable);
    btnNext.classList.toggle('hidden', !showNext);
    btnNext.disabled = isLoadingQuestion;
  }
  if (btnFinish) {
    const showFinish = Boolean(currentEntry?.answered && !currentEntry.nextAvailable);
    btnFinish.classList.toggle('hidden', !showFinish);
  }
  if (btnOverview) {
    const total = currentEntry?.total || totalCount || 0;
    btnOverview.disabled = total <= 1 || isLoadingQuestion;
  }
  updateJumpModalState();
}

function updateJumpModalState() {
  const container = document.getElementById('jump-list');
  if (!container) return;
  const buttons = container.querySelectorAll('.jump-item');
  const currentIndex = currentEntry?.currentIndex;
  const availableMax = questionHistory.length + 1;
  buttons.forEach((btn) => {
    const idx = Number(btn.dataset.index);
    if (Number.isNaN(idx)) return;
    btn.classList.toggle('is-current', idx === currentIndex);
    if (idx > availableMax) {
      btn.disabled = true;
      btn.title = '未生成';
    } else {
      btn.disabled = false;
      btn.title = '';
    }
  });
}

/**
 * 更新统计
 */
function updateStats() {
  document.getElementById('answered-count').textContent = answeredCount;
  document.getElementById('total-count').textContent = totalCount;

  const accuracy = answeredCount > 0 ? Math.round((correctCount / answeredCount) * 100) : 0;
  document.getElementById('accuracy').textContent = `${accuracy}%`;
}

/**
 * 恢复之前的会话（页面刷新后）
 */
async function restoreSession() {
  const savedSessionId = localStorage.getItem(STORAGE_KEYS.SESSION);
  if (!savedSessionId) {
    return; // 没有保存的会话
  }

  try {
    // 检查会话是否仍然有效
    const response = await fetch(`${API_BASE}/session-status`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ session_id: savedSessionId }),
    });

    if (!response.ok) {
      // 会话无效，清除localStorage
      localStorage.removeItem(STORAGE_KEYS.SESSION);
      return;
    }

    const data = await response.json();

    // 恢复会话状态
    currentSessionId = savedSessionId;
    answeredCount = data.current_index;
    totalCount = data.total_count;
    correctCount = data.correct_count;

    // 更新统计信息
    updateStats();

    if (data.finished) {
      showResultView();
    } else {
      resetQuestionHistory();
      showQuizView();
      await loadNextQuestion();
    }

    console.log('✅ 会话已恢复:', savedSessionId.substring(0, 8) + '...');
  } catch (error) {
    console.error('恢复会话失败:', error);
    localStorage.removeItem(STORAGE_KEYS.SESSION);
  }
}

/**
 * 初始化重新开始按钮
 */
function initRestartButton() {
  document.getElementById('btn-restart').addEventListener('click', () => {
    // 重置状态
    currentSessionId = null;
    localStorage.removeItem(STORAGE_KEYS.SESSION); // 清除localStorage
    currentQuestion = null;
    selectedOptions.clear();
    answeredCount = 0;
    correctCount = 0;
    totalCount = 0;
    resetQuestionHistory();

    // 重置UI
    fileInput.value = '';
    const storedKnowledge = getStoredKnowledge();
    if (storedKnowledge) {
      applyKnowledgeLock(storedKnowledge);
    } else {
      clearKnowledgeLock();
    }
    btnGenerate.textContent = '生成题目';
    updateStats();

    // 切换到上传界面
    showUploadView();
  });
}

/**
 * 初始化重置数据按钮
 */
function initResetButton() {
  const btnReset = document.getElementById('btn-reset-data');
  if (!btnReset) return;

  btnReset.addEventListener('click', async () => {
    // 确认对话框
    const confirmed = confirm(
      '⚠️ 警告：此操作将清空所有数据（答题历史、错题本、会话记录、上传文件），但保留AI配置。\n\n确认要继续吗？'
    );

    if (!confirmed) return;

    try {
      btnReset.disabled = true;
      btnReset.textContent = '正在重置...';

      const response = await fetch(`${API_BASE}/reset-data`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || '重置失败');
      }

      // 重置前端状态
      currentFilepath = null;
      currentSessionId = null;
      localStorage.removeItem(STORAGE_KEYS.SESSION); // 清除localStorage
      localStorage.removeItem(STORAGE_KEYS.KNOWLEDGE);
      currentQuestion = null;
      selectedOptions.clear();
      answeredCount = 0;
      correctCount = 0;
      totalCount = 0;
      resetQuestionHistory();
      clearKnowledgeLock();

      // 重置UI
      fileInput.value = '';
      btnGenerate.textContent = '生成题目';
      updateStats();

      // 切换到上传界面
      showUploadView();

      alert('✅ 数据重置成功！（AI配置已保留）');
    } catch (error) {
      alert(`❌ 重置失败：${error.message}`);
    } finally {
      btnReset.disabled = false;
      btnReset.textContent = '重置数据';
    }
  });
}
