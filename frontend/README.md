# 前端原型使用说明

该目录提供电梯安全问答系统的桌面端界面样板，用于预览未来前端集成的布局和视觉样式。

## 目录结构
```
frontend/
├── index.html              # 桌面端样板（更新品牌：答题考试系统）
├── mobile.html             # 移动端样板（模拟手机练习体验）
├── assets/                 # 静态样式与交互脚本
├── shadcn-app/             # 基于 React + shadcn/ui 的现代化演示
└── README.md               # 本说明文件
```

## 预览方式
- 桌面端：直接在浏览器中打开 `index.html`（推荐 Chrome / Edge）。
- 移动端：
  - 桌面浏览器中打开 `mobile.html`，调整开发者工具至 375px 宽度预览；或
  - 将目录托管至本地服务器后用手机浏览器访问 `mobile.html`。
- 所有页面均使用静态示例数据，尚未对接后端。

## 功能亮点
- 桌面端：侧边栏呈现训练概况及错题本，主体为题卡 + 解析面板，适合大屏使用。
- 移动端：顶部品牌与进度条、居中题卡、底部操作条的结构贴合答题 App 使用习惯。
- 两个样板均提供“解析”折叠、高亮选项等交互，方便对接真实状态。
- 设置入口：桌面端为弹窗、移动端为底部抽屉，可录入 AI URL、Key、模型并模拟连通性测试/保存/删除操作。

## shadcn/ui React Demo
`frontend/shadcn-app/` 提供了一个采用 Vite + React + Tailwind + shadcn/ui 打造的新版控制台。新版 UI 由顶部导航统筹“首页/答题中心/AI 配置/错题本/历史记录”五大分区，保持现有接口但视觉全面焕新。主要特性：
- 夜/昼双主题：内建 Day/Night 切换，白天偏简洁、夜晚偏霓虹，按钮/卡片/进度条风格同步切换。
- modern UI：使用 shadcn/ui + `lucide-react`，配合深色渐变与玻璃卡片风格，突出数据驾驶舱体验。
- 真实数据联动：知识上传（支持文件/文本粘贴）、题目生成、答题、错题统计、历史摘要、AI 配置均直接连到 `web_server.py` 的 `/api`。
- 可扩展性：封装 `apiRequest/apiJson` 帮助函数、`@/components` 路径别名，方便在后续页签里继续拓展功能。

运行方式：
```bash
cd frontend/shadcn-app
npm install         # 初始化依赖
npm run dev         # 本地开发（默认 http://localhost:5173）
npm run build       # 产出静态资源，可部署到任意静态托管
```
构建完成后，可通过 `npm run preview` 验证产物，再将 `dist/` 交由后端静态目录或 CDN 托管。通过 `VITE_API_BASE_URL`（参见 `.env.example`）指定后端地址，默认指向 `http://localhost:5001` 并直接消费 `web_server.py` 暴露的 `/api` 接口；如需自定义数据流，可在 `src/App.tsx` 中调整 `fetch` / `apiRequest` 实现或替换状态管理方案。想单独审查配色，可直接访问 `http://localhost:5173/theme-preview.html` 查看日/夜主题示例。

## 后续集成建议
1. 将 `app.js`、`mobile.js` 的示例逻辑替换为真实 API/Socket 交互（获取题目、提交答案、复练提醒）。
2. 后端可提供 RESTful 接口，或构建统一的 WebSocket 管道用于实时同步答题进度与解析。
3. 若要共享组件，可使用前端框架（Vue/React）抽象题卡、解析、进度条组件，再利用 CSS 变量实现主题切换。
4. 增强响应式：桌面端 `styles.css` 已内置媒体查询，可在联调阶段进一步优化 768px 以下的折叠策略。
