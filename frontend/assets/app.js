/**
 * 答题考试系统（AI版）前端逻辑
 */

const API_BASE = 'http://localhost:5001/api';

// 全局状态
let currentFilepath = null;
let currentSessionId = null;
let currentQuestion = null;
let selectedOptions = new Set();
let answeredCount = 0;
let correctCount = 0;
let totalCount = 0;

// DOM 元素
const uploadZone = document.getElementById('upload-zone');
const fileInput = document.getElementById('file-input');
const fileInfo = document.getElementById('file-info');
const btnGenerate = document.getElementById('btn-generate');
const uploadView = document.getElementById('upload-view');
const quizView = document.getElementById('quiz-view');
const resultView = document.getElementById('result-view');
const questionContainer = document.getElementById('question-container');

// 初始化
document.addEventListener('DOMContentLoaded', () => {
  initUploadZone();
  initGenerateButton();
  initRestartButton();
});

/**
 * 初始化上传区域
 */
function initUploadZone() {
  // 点击上传
  uploadZone.addEventListener('click', () => {
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
    uploadZone.classList.add('dragging');
  });

  uploadZone.addEventListener('dragleave', () => {
    uploadZone.classList.remove('dragging');
  });

  uploadZone.addEventListener('drop', async (e) => {
    e.preventDefault();
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

    // 显示文件信息
    document.getElementById('filename').textContent = file.name;
    document.getElementById('entry-count').textContent = data.entry_count;
    fileInfo.classList.remove('hidden');

    // 启用生成按钮
    btnGenerate.disabled = false;

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
    const aiCount = parseInt(document.getElementById('ai-count').value);
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
          ai_count: aiCount,
          mode,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || '生成失败');
      }

      // 保存会话ID
      currentSessionId = data.session_id;
      totalCount = data.total_count;

      // 重置计数
      answeredCount = 0;
      correctCount = 0;
      updateStats();

      // 切换到答题界面
      showQuizView();

      // 加载第一题
      await loadNextQuestion();

    } catch (error) {
      showMessage('upload-error', `生成失败：${error.message}`, 'error');
      btnGenerate.disabled = false;
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
function showQuizView() {
  uploadView.classList.add('hidden');
  quizView.classList.remove('hidden');
  resultView.classList.add('hidden');
}

/**
 * 切换到结果界面
 */
function showResultView() {
  uploadView.classList.add('hidden');
  quizView.classList.add('hidden');
  resultView.classList.remove('hidden');

  // 显示结果
  const score = totalCount > 0 ? Math.round((correctCount / totalCount) * 100) : 0;
  document.getElementById('final-score').textContent = `${score}%`;
  document.getElementById('correct-count').textContent = correctCount;
  document.getElementById('result-total').textContent = totalCount;
}

/**
 * 加载下一题
 */
async function loadNextQuestion() {
  try {
    const response = await fetch(`${API_BASE}/get-question`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        session_id: currentSessionId,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || '加载失败');
    }

    if (data.finished) {
      // 所有题目完成
      showResultView();
      return;
    }

    // 保存当前题目
    currentQuestion = data.question;
    selectedOptions.clear();

    // 渲染题目
    renderQuestion(data.question, data.current_index, data.total_count);

  } catch (error) {
    questionContainer.innerHTML = `<div class="error-message">加载失败：${error.message}</div>`;
  }
}

/**
 * 渲染题目
 */
function renderQuestion(question, currentIndex, total) {
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
      <button class="btn-submit" id="btn-submit">提交答案</button>
      <div class="feedback-box" id="feedback-box"></div>
    </div>
  `;

  questionContainer.innerHTML = html;

  // 绑定事件
  if (question.question_type === 'SINGLE_CHOICE') {
    bindSingleChoiceEvents();
  } else if (question.question_type === 'MULTI_CHOICE') {
    bindMultiChoiceEvents();
  }

  bindSubmitEvent();
}

/**
 * 绑定单选题事件
 */
function bindSingleChoiceEvents() {
  const options = document.querySelectorAll('.option-item');
  options.forEach(option => {
    option.addEventListener('click', () => {
      // 清除其他选项
      options.forEach(opt => opt.classList.remove('selected'));
      // 选中当前选项
      option.classList.add('selected');
      selectedOptions.clear();
      selectedOptions.add(parseInt(option.dataset.index));
    });
  });
}

/**
 * 绑定多选题事件
 */
function bindMultiChoiceEvents() {
  const options = document.querySelectorAll('.option-item');
  options.forEach(option => {
    option.addEventListener('click', () => {
      const index = parseInt(option.dataset.index);
      if (selectedOptions.has(index)) {
        selectedOptions.delete(index);
        option.classList.remove('selected');
      } else {
        selectedOptions.add(index);
        option.classList.add('selected');
      }
    });
  });
}

/**
 * 绑定提交事件
 */
function bindSubmitEvent() {
  const btnSubmit = document.getElementById('btn-submit');
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

    // 显示反馈
    showFeedback(data.is_correct, data.explanation, data.correct_answer);

    // 添加"下一题"按钮
    btnSubmit.style.display = 'none';
    const feedbackBox = document.getElementById('feedback-box');

    if (data.next_available) {
      const btnNext = document.createElement('button');
      btnNext.className = 'btn-next';
      btnNext.textContent = '下一题';
      btnNext.addEventListener('click', () => {
        loadNextQuestion();
      });
      feedbackBox.appendChild(btnNext);
    } else {
      const btnFinish = document.createElement('button');
      btnFinish.className = 'btn-next';
      btnFinish.textContent = '查看结果';
      btnFinish.addEventListener('click', () => {
        showResultView();
      });
      feedbackBox.appendChild(btnFinish);
    }

  } catch (error) {
    alert(`提交失败：${error.message}`);
    btnSubmit.disabled = false;
    btnSubmit.textContent = '提交答案';
  }
}

/**
 * 显示反馈
 */
function showFeedback(isCorrect, explanation, correctAnswer) {
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
 * 初始化重新开始按钮
 */
function initRestartButton() {
  document.getElementById('btn-restart').addEventListener('click', () => {
    // 重置状态
    currentFilepath = null;
    currentSessionId = null;
    currentQuestion = null;
    selectedOptions.clear();
    answeredCount = 0;
    correctCount = 0;
    totalCount = 0;

    // 重置UI
    fileInput.value = '';
    fileInfo.classList.add('hidden');
    btnGenerate.disabled = true;
    btnGenerate.textContent = '生成题目';
    updateStats();

    // 切换到上传界面
    uploadView.classList.remove('hidden');
    quizView.classList.add('hidden');
    resultView.classList.add('hidden');
  });
}
