# 错题本页面样式统一说明

## 更新日期
2025-11-04

## 更新目的
将错题本页面的样式风格与首页完全统一，提供一致的用户体验。

## 样式变量对比

### 之前（不一致）

```css
:root {
  --primary: #2563eb;
  --primary-hover: #1d4ed8;
  --success: #16a34a;
  --danger: #dc2626;          /* ❌ 不一致 */
  --warning: #f59e0b;
  --muted: #6b7280;
  --border: #e5e7eb;
  --background: #f9fafb;      /* ❌ 命名不一致 */
  --card-bg: #ffffff;         /* ❌ 命名不一致 */
  --text-primary: #111827;    /* ❌ 命名不一致 */
  --text-secondary: #6b7280;  /* ❌ 命名不一致 */
}
```

### 现在（统一）

```css
:root {
  --bg: #f5f7fb;              /* ✓ 与首页一致 */
  --white: #ffffff;           /* ✓ 与首页一致 */
  --primary: #2563eb;         /* ✓ 与首页一致 */
  --primary-light: #e0e7ff;   /* ✓ 与首页一致 */
  --danger: #f97316;          /* ✓ 与首页一致 */
  --text-title: #111827;      /* ✓ 与首页一致 */
  --text-body: #4b5563;       /* ✓ 与首页一致 */
  --border: #e5e7eb;          /* ✓ 与首页一致 */
  --success: #16a34a;         /* ✓ 与首页一致 */
  --muted: #9ca3af;           /* ✓ 与首页一致 */
  font-family: "Segoe UI", "PingFang SC", "Hiragino Sans GB", Arial, sans-serif;
}
```

## 设计元素统一

### 1. 字体系统

**统一后：**
```
主字体：Segoe UI, PingFang SC, Hiragino Sans GB, Arial, sans-serif
标题大小：18px - 24px
正文大小：14px
次要文字：13px
```

### 2. 圆角系统

**统一后：**
```
卡片圆角：12px
按钮圆角：8px
输入框圆角：8px
标签圆角：999px (全圆角)
```

### 3. 间距系统

**统一后：**
```
组件间距：16px
区块间距：28px
内边距（卡片）：20px
内边距（按钮）：8px 20px
```

### 4. 阴影系统

**统一后：**
```css
/* 默认阴影 */
box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);

/* hover 阴影 */
box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);

/* 模态框阴影 */
box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.2);
```

### 5. 颜色使用规范

| 元素 | 颜色变量 | 十六进制 | 用途 |
|------|---------|---------|------|
| 页面背景 | `--bg` | #f5f7fb | 主背景色 |
| 卡片背景 | `--white` | #ffffff | 卡片、模态框 |
| 主色调 | `--primary` | #2563eb | 按钮、链接、强调 |
| 浅主色 | `--primary-light` | #e0e7ff | hover 背景 |
| 危险操作 | `--danger` | #f97316 | 删除按钮 |
| 成功状态 | `--success` | #16a34a | 成功提示 |
| 标题文字 | `--text-title` | #111827 | 标题、重要文字 |
| 正文文字 | `--text-body` | #4b5563 | 正文内容 |
| 次要文字 | `--muted` | #9ca3af | 辅助信息 |
| 边框 | `--border` | #e5e7eb | 分割线、边框 |

## 交互效果统一

### 1. 卡片 Hover 效果

```css
.stat-card:hover,
.question-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}
```

### 2. 按钮 Hover 效果

```css
.btn-primary:hover {
  background: #1d4ed8;
  box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.3);
}

.btn-secondary:hover {
  background: var(--bg);
  border-color: var(--primary);
  color: var(--primary);
}
```

### 3. 输入框 Focus 效果

```css
.input-field:focus,
.select-field:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}
```

### 4. 模态框动画

```css
@keyframes modalSlideIn {
  from {
    opacity: 0;
    transform: translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
```

## 响应式设计

### 断点统一

```css
@media (max-width: 768px) {
  /* 移动端适配 */
  .stats-section {
    grid-template-columns: 1fr;
  }

  .toolbar {
    flex-direction: column;
  }
}
```

## 视觉一致性检查清单

- [x] CSS 变量名称与首页一致
- [x] 颜色值与首页一致
- [x] 字体系统与首页一致
- [x] 圆角尺寸与首页一致
- [x] 间距系统与首页一致
- [x] 阴影效果与首页一致
- [x] Hover 动画与首页一致
- [x] Focus 效果与首页一致
- [x] 响应式断点与首页一致

## 主要改进

### 1. 颜色调整

- ✅ 危险色从 `#dc2626` 改为 `#f97316`（更温和的橙红色）
- ✅ 背景色从 `#f9fafb` 改为 `#f5f7fb`（更统一的灰蓝色）
- ✅ 次要文字从 `#6b7280` 改为 `#9ca3af`（更浅的灰色）

### 2. 字体调整

- ✅ 统一使用 Segoe UI 作为优先字体
- ✅ 中文字体优先使用 PingFang SC
- ✅ 备用中文字体为 Hiragino Sans GB

### 3. 间距优化

- ✅ 组件间距统一为 16px
- ✅ 区块间距统一为 28px
- ✅ 卡片内边距统一为 20px

### 4. 圆角统一

- ✅ 所有卡片使用 12px 圆角
- ✅ 所有按钮和输入框使用 8px 圆角
- ✅ 标签使用 999px 全圆角

### 5. 阴影细化

- ✅ 默认阴影更轻更自然
- ✅ Hover 阴影增强层次感
- ✅ 模态框阴影营造浮起效果

## 用户体验提升

1. **视觉一致性** - 错题本与首页风格完全一致，降低学习成本
2. **交互流畅性** - 统一的动画效果，提供连贯的体验
3. **信息层次** - 清晰的颜色系统，突出重要信息
4. **可访问性** - 合理的对比度，易于阅读
5. **响应式** - 移动端和桌面端都有良好体验

## 维护建议

1. **使用 CSS 变量** - 所有颜色、字体、间距都使用变量定义
2. **保持一致性** - 新增功能时参考现有样式规范
3. **避免硬编码** - 不要直接写十六进制颜色值
4. **遵循命名规范** - 使用语义化的类名

## 文件变更

```
修改文件：
  web/wrong-questions/styles.css (624 行)

变更内容：
  - 更新 CSS 变量定义（10 个变量）
  - 统一圆角尺寸（3 处）
  - 统一间距系统（多处）
  - 统一阴影效果（5 处）
  - 优化按钮样式（3 种按钮）
  - 优化交互动画（4 种效果）
```

## 效果对比

### 之前
- 独立的设计系统
- 不同的颜色值
- 不一致的间距
- 简单的阴影效果

### 现在
- 统一的设计系统
- 一致的颜色变量
- 规范的间距系统
- 精致的阴影效果
- 流畅的交互动画
- 响应式适配

## 总结

通过这次样式统一，错题本页面现在：
- ✅ 与首页完全一致的视觉风格
- ✅ 统一的设计语言
- ✅ 更好的用户体验
- ✅ 更易于维护的代码

---

**更新时间**：2025-11-04
**影响范围**：错题本页面（web/wrong-questions/）
**兼容性**：无破坏性更改，完全向后兼容
