import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  Brain,
  CheckCircle2,
  FileBarChart2,
  FileCheck,
  FilePlus2,
  Gauge,
  History,
  Layers,
  Loader2,
  Moon,
  Notebook,
  ShieldCheck,
  Sparkles,
  Sun,
  UploadCloud,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { apiJson, apiRequest } from "@/lib/api";
import { cn } from "@/lib/utils";

type QuestionPayload = {
  identifier: string;
  question_type: "SINGLE_CHOICE" | "MULTI_CHOICE" | "CLOZE" | "QA";
  prompt: string;
  options?: string[];
  correct_options?: number[];
  answer_text?: string;
  explanation?: string;
  keywords?: string[];
};

type WrongQuestionEntry = {
  question: QuestionPayload;
  last_wrong_at?: string;
  last_plain_explanation?: string;
};

type WrongStats = {
  total_wrong: number;
  by_type: Record<string, number>;
  weakest_topics: { topic: string; count: number }[];
};

type HistorySummary = {
  session_id: string;
  latest_at?: string;
  started_at?: string;
  total_answers: number;
  correct_answers: number;
  accuracy: number;
  knowledge_file?: string;
  mode?: string;
};

type AiConfig = {
  url: string;
  key: string;
  model: string;
  timeout: number;
  dev_document?: string | null;
};

const QUESTION_TYPE_LABEL: Record<QuestionPayload["question_type"], string> = {
  SINGLE_CHOICE: "单选题",
  MULTI_CHOICE: "多选题",
  CLOZE: "填空题",
  QA: "问答题",
};

const QUESTION_FILTERS = [
  { value: "single", label: "单选" },
  { value: "multi", label: "多选" },
  { value: "cloze", label: "填空" },
  { value: "qa", label: "问答" },
] as const;

const DEFAULT_KNOWLEDGE_PATH = "docs/Knowledge/电梯安全装置维护程序.md";

type SectionKey = "dashboard" | "practice" | "ai" | "wrong" | "history";

const SECTION_NAV: { key: SectionKey; label: string; icon: React.ReactNode }[] = [
  { key: "dashboard", label: "首页", icon: <Gauge className="h-4 w-4" /> },
  { key: "practice", label: "答题中心", icon: <Notebook className="h-4 w-4" /> },
  { key: "ai", label: "AI 配置", icon: <Brain className="h-4 w-4" /> },
  { key: "wrong", label: "错题本", icon: <ShieldCheck className="h-4 w-4" /> },
  { key: "history", label: "历史记录", icon: <History className="h-4 w-4" /> },
];

const getPreferredTheme = (): "light" | "dark" => {
  if (typeof window === "undefined") {
    return "dark";
  }
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
};

export default function App() {
  const [theme, setTheme] = useState<"light" | "dark">(() => getPreferredTheme());
  const [activeSection, setActiveSection] = useState<SectionKey>("dashboard");
  const [knowledgePath, setKnowledgePath] = useState(DEFAULT_KNOWLEDGE_PATH);
  const [uploading, setUploading] = useState(false);
  const [uploadPreview, setUploadPreview] = useState<string | null>(null);
  const [practiceTypes, setPracticeTypes] = useState<string[]>(QUESTION_FILTERS.map((item) => item.value));
  const [useAi, setUseAi] = useState(true);
  const [questionCount, setQuestionCount] = useState(10);
  const [questionMode, setQuestionMode] = useState<"sequential" | "random">("sequential");
  const [seed, setSeed] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [questionState, setQuestionState] = useState<QuestionPayload | null>(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [totalCount, setTotalCount] = useState(0);
  const [selectedOptions, setSelectedOptions] = useState<string[]>([]);
  const [textAnswer, setTextAnswer] = useState("");
  const [submissionResult, setSubmissionResult] = useState<{
    is_correct: boolean;
    explanation: string;
    correct_answer: string;
  } | null>(null);
  const [practiceSummary, setPracticeSummary] = useState<{ correct_count: number; total_count: number } | null>(null);
  const [practiceLoading, setPracticeLoading] = useState(false);
  const [questionLoading, setQuestionLoading] = useState(false);
  const [practiceMessage, setPracticeMessage] = useState<string | null>(null);

  const [aiConfig, setAiConfig] = useState<AiConfig>({
    url: "",
    key: "",
    model: "",
    timeout: 10,
    dev_document: "",
  });
  const [aiStatus, setAiStatus] = useState<{ state: "idle" | "loading" | "saved" | "error"; message?: string }>({
    state: "idle",
  });

  const [wrongList, setWrongList] = useState<WrongQuestionEntry[]>([]);
  const [wrongStats, setWrongStats] = useState<WrongStats | null>(null);
  const [historySummaries, setHistorySummaries] = useState<HistorySummary[]>([]);
  const [asideLoading, setAsideLoading] = useState(false);

  useEffect(() => {
    if (typeof document === "undefined") return;
    document.documentElement.classList.toggle("dark", theme === "dark");
  }, [theme]);

  const themeTokens = useMemo(() => {
    if (theme === "dark") {
      return {
        shell: "bg-[#050816] text-slate-50",
        hero: "bg-gradient-to-br from-slate-900 via-slate-900/80 to-slate-800 text-white border border-white/10",
        nav: "bg-slate-900/60 border border-white/10 text-slate-100",
        card: "bg-slate-900/60 border border-white/10 text-slate-100",
        muted: "text-slate-400",
        badgePrimary: "bg-sky-400/20 text-sky-100",
        badgeGhost: "border border-white/20 text-slate-200",
        primaryButton: "bg-gradient-to-r from-sky-400 via-indigo-500 to-indigo-600 text-white shadow-[0_20px_40px_rgba(56,189,248,0.35)]",
        ghostButton: "border border-white/20 text-slate-100 hover:bg-white/10",
        progressTrack: "bg-white/10",
        progressFill: "bg-gradient-to-r from-sky-400 to-indigo-400",
      };
    }
    return {
      shell: "bg-slate-50 text-slate-900",
      hero: "bg-gradient-to-br from-white via-slate-50 to-slate-100 text-slate-900 border border-white",
      nav: "bg-white/80 border border-slate-200 text-slate-600",
      card: "bg-white border border-slate-200 text-slate-900",
      muted: "text-slate-500",
      badgePrimary: "bg-blue-500/15 text-blue-700",
      badgeGhost: "border border-slate-300 text-slate-600",
      primaryButton: "bg-gradient-to-r from-blue-500 via-indigo-500 to-indigo-600 text-white shadow-[0_15px_30px_rgba(79,70,229,0.25)]",
      ghostButton: "border border-slate-200 text-slate-600 hover:bg-slate-100",
      progressTrack: "bg-slate-200",
      progressFill: "bg-gradient-to-r from-blue-500 to-cyan-400",
    };
  }, [theme]);

  const cardClass = (...classes: string[]) => cn("shadow-lg transition-colors duration-300", themeTokens.card, ...classes);
  const heroClass = cn("rounded-3xl p-6 shadow-2xl transition-colors duration-300", themeTokens.hero);
  const navClass = cn("mt-8 rounded-2xl p-2 shadow-lg transition-colors duration-300", themeTokens.nav);
  const mutedText = themeTokens.muted;
  const badgePrimaryClass = (...classes: string[]) => cn("rounded-md px-3 py-1 text-xs font-semibold", themeTokens.badgePrimary, ...classes);
  const badgeGhostClass = (...classes: string[]) => cn("rounded-md px-3 py-1 text-xs font-semibold", themeTokens.badgeGhost, ...classes);
  const primaryButtonClass = (...classes: string[]) => cn("transition-colors duration-300", themeTokens.primaryButton, ...classes);
  const ghostButtonClass = (...classes: string[]) => cn("transition-colors duration-300", themeTokens.ghostButton, ...classes);
  const progressTrackClass = cn("h-2 w-full overflow-hidden rounded-full", themeTokens.progressTrack);
  const progressFillClass = cn("h-full rounded-full transition-all", themeTokens.progressFill);
  const tabTriggerClass =
    theme === "dark"
      ? "text-slate-200 data-[state=active]:bg-white data-[state=active]:text-slate-900"
      : "text-slate-600 data-[state=active]:bg-slate-900 data-[state=active]:text-white";
  const footerClass = theme === "dark" ? "border-white/10 text-slate-400" : "border-slate-200 text-slate-500";
  const heroOverlayClass = theme === "dark" ? "bg-white/10" : "bg-black/5";

  const progressPercent = useMemo(() => {
    if (!totalCount) return 0;
    const completed = Math.min(currentIndex - 1, totalCount);
    return Math.round((completed / totalCount) * 100);
  }, [currentIndex, totalCount]);

  const toggleQuestionType = (value: string) => {
    setPracticeTypes((prev) => {
      const set = new Set(prev);
      if (set.has(value)) set.delete(value);
      else set.add(value);
      return Array.from(set);
    });
  };

  const resetAnswerState = () => {
    setSelectedOptions([]);
    setTextAnswer("");
    setSubmissionResult(null);
  };

  const loadQuestion = useCallback(
    async (overrideSessionId?: string) => {
      const sid = overrideSessionId ?? sessionId;
      if (!sid) return;
      setQuestionLoading(true);
      setPracticeMessage(null);
      try {
        const data = await apiJson<{
          finished: boolean;
          question?: QuestionPayload;
          current_index?: number;
          total_count?: number;
          correct_count?: number;
        }>("/api/get-question", { session_id: sid });
        if (data.finished) {
          setQuestionState(null);
          setPracticeSummary({
            correct_count: data.correct_count ?? 0,
            total_count: totalCount || data.total_count || 0,
          });
          return;
        }
        setQuestionState(data.question ?? null);
        setCurrentIndex(data.current_index ?? 0);
        setTotalCount(data.total_count ?? 0);
        resetAnswerState();
        setPracticeSummary(null);
      } catch (error) {
        setPracticeMessage((error as Error).message);
      } finally {
        setQuestionLoading(false);
      }
    },
    [sessionId, totalCount]
  );

  const handleUpload = async (file: File) => {
    setUploading(true);
    setPracticeMessage(null);
    const formData = new FormData();
    formData.append("file", file);
    try {
      const data = await apiRequest<{
        success: boolean;
        filepath: string;
        entry_count: number;
        entries_preview: { component: string; text: string }[];
      }>("/api/upload-knowledge", {
        method: "POST",
        body: formData,
      });
      if (!data.success) {
        throw new Error("上传失败，请重试");
      }
      setKnowledgePath(data.filepath);
      setUploadPreview(`解析成功：${data.entry_count} 条知识点`);
    } catch (error) {
      setPracticeMessage((error as Error).message);
    } finally {
      setUploading(false);
    }
  };
  const [textUpload, setTextUpload] = useState("");
  const uploadTextSnippet = async () => {
    if (!textUpload.trim()) {
      setPracticeMessage("请粘贴需要解析的文本内容");
      return;
    }
    const blob = new Blob([textUpload], { type: "text/markdown" });
    const virtualFile = new File([blob], "pasted-knowledge.md", { type: "text/markdown" });
    await handleUpload(virtualFile);
    setTextUpload("");
  };

  const startPractice = async () => {
    if (!knowledgePath) {
      setPracticeMessage("请先选择或上传知识文件");
      return;
    }
    if (practiceTypes.length === 0) {
      setPracticeMessage("请至少选择一个题型");
      return;
    }
    setPracticeLoading(true);
    setPracticeMessage(null);
    try {
      const payload: Record<string, unknown> = {
        filepath: knowledgePath,
        types: practiceTypes,
        count: questionCount,
        use_ai: useAi,
        mode: questionMode,
      };
      if (seed.trim()) {
        payload.seed = Number(seed) || seed.trim();
      }
      const data = await apiJson<{
        success: boolean;
        session_id: string;
        total_count: number;
      }>("/api/generate-questions", payload);
      if (!data.success) {
        throw new Error("题目生成失败");
      }
      setSessionId(data.session_id);
      setTotalCount(data.total_count);
      setCurrentIndex(0);
      setPracticeSummary(null);
      await loadQuestion(data.session_id);
      setActiveSection("practice");
    } catch (error) {
      setPracticeMessage((error as Error).message);
    } finally {
      setPracticeLoading(false);
    }
  };

  const handleSubmitAnswer = async () => {
    if (!sessionId || !questionState) return;
    let answer = "";
    if (questionState.question_type === "SINGLE_CHOICE") {
      answer = selectedOptions[0] ?? "";
    } else if (questionState.question_type === "MULTI_CHOICE") {
      answer = [...selectedOptions].sort().join("");
    } else {
      answer = textAnswer.trim();
    }
    if (!answer) {
      setPracticeMessage("请先作答，再提交。");
      return;
    }
    setPracticeMessage(null);
    try {
      const data = await apiJson<{
        success: boolean;
        is_correct: boolean;
        explanation: string;
        correct_answer: string;
        next_available: boolean;
      }>("/api/submit-answer", {
        session_id: sessionId,
        answer,
      });
      if (!data.success) {
        throw new Error("提交失败");
      }
      setSubmissionResult({
        is_correct: data.is_correct,
        explanation: data.explanation,
        correct_answer: data.correct_answer,
      });
      await Promise.all([loadWrongData(), loadHistory()]);
      if (!data.next_available) {
        await loadQuestion(sessionId);
      }
    } catch (error) {
      setPracticeMessage((error as Error).message);
    }
  };

  const loadWrongData = useCallback(async () => {
    try {
      const listResp = await apiRequest<{ success: boolean; data: { questions: WrongQuestionEntry[] } }>(
        "/api/wrong-questions?page=1&page_size=5"
      );
      if (listResp.success) {
        setWrongList(listResp.data.questions ?? []);
      }
      const statsResp = await apiRequest<{ success: boolean; data: WrongStats }>("/api/wrong-questions/stats");
      if (statsResp.success) {
        setWrongStats(statsResp.data);
      }
    } catch (error) {
      console.warn("加载错题数据失败", error);
    }
  }, []);

  const loadHistory = useCallback(async () => {
    try {
      const resp = await apiRequest<{ success: boolean; data: HistorySummary[] }>(
        "/api/answer-history/sessions?limit=5"
      );
      if (resp.success) {
        setHistorySummaries(resp.data);
      }
    } catch (error) {
      console.warn("加载历史失败", error);
    }
  }, []);

  const loadAiConfig = useCallback(async () => {
    setAiStatus({ state: "loading" });
    try {
      const data = await apiRequest<AiConfig | null>("/api/ai-config");
      if (data) {
        setAiConfig(data);
      }
      setAiStatus({ state: "idle" });
    } catch (error) {
      setAiStatus({ state: "error", message: (error as Error).message });
    }
  }, []);

  const saveAiConfig = async () => {
    setAiStatus({ state: "loading" });
    try {
      const payload = { ...aiConfig };
      const data = await apiRequest<AiConfig>("/api/ai-config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      setAiConfig(data);
      setAiStatus({ state: "saved", message: "配置已保存" });
    } catch (error) {
      setAiStatus({ state: "error", message: (error as Error).message });
    }
  };

  const testAiConfig = async () => {
    setAiStatus({ state: "loading" });
    try {
      const { ok, message } = await apiJson<{ ok: boolean; message: string }>("/api/ai-config/test", aiConfig);
      setAiStatus({ state: ok ? "saved" : "error", message });
    } catch (error) {
      setAiStatus({ state: "error", message: (error as Error).message });
    }
  };

  useEffect(() => {
    setAsideLoading(true);
    Promise.all([loadAiConfig(), loadWrongData(), loadHistory()]).finally(() => setAsideLoading(false));
  }, [loadAiConfig, loadWrongData, loadHistory]);

  const heroStats = [
    {
      label: "答题进度",
      value: totalCount ? `${Math.min(currentIndex, totalCount)} / ${totalCount}` : "—",
      description: "使用当前会话实时更新",
    },
    {
      label: "错题数量",
      value: wrongStats ? `${wrongStats.total_wrong}` : "—",
      description: "来自错题本统计",
    },
    {
      label: "最新正确率",
      value: historySummaries[0] ? `${Math.round(historySummaries[0].accuracy * 100)}%` : "—",
      description: historySummaries[0] ? historySummaries[0].session_id.slice(0, 8) : "暂无历史记录",
    },
  ];

  const renderDashboard = () => (
    <div className="space-y-6">
      <section className={heroClass}>
        <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.3em] opacity-80">QA SYSTEM</p>
            <h1 className="mt-3 text-3xl font-semibold">知识练习驾驶舱</h1>
            <p className="text-sm opacity-80">
              统一管理题目生成、AI 配置、错题复练与答题历史。
            </p>
          </div>
          <div className={cn("rounded-3xl p-4 text-right shadow-lg backdrop-blur", heroOverlayClass)}>
            <p className="text-xs uppercase opacity-80">当前进度</p>
            <p className="text-4xl font-semibold">{progressPercent}%</p>
            <div className={progressTrackClass}>
              <div className={progressFillClass} style={{ width: `${progressPercent}%` }} />
            </div>
          </div>
        </div>
        <div className="mt-6 grid gap-4 md:grid-cols-3">
          {heroStats.map((stat) => (
            <div key={stat.label} className={cn("rounded-2xl p-4 backdrop-blur", heroOverlayClass)}>
              <p className="text-sm opacity-80">{stat.label}</p>
              <p className="mt-2 text-2xl font-semibold">{stat.value}</p>
              <p className="text-xs opacity-80">{stat.description}</p>
            </div>
          ))}
        </div>
      </section>

      <div className="grid gap-6 md:grid-cols-3">
        <Card className={cardClass()}>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Notebook className="h-4 w-4" />
              开始答题
            </CardTitle>
            <CardDescription>进入答题中心，配置知识库并发起练习。</CardDescription>
          </CardHeader>
          <CardFooter>
            <Button className={cn("w-full", primaryButtonClass())} onClick={() => setActiveSection("practice")}>
              前往答题中心
            </Button>
          </CardFooter>
        </Card>
        <Card className={cardClass()}>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Brain className="h-4 w-4" />
              AI 接入状态
            </CardTitle>
            <CardDescription>{aiConfig.url ? "已配置模型接口" : "待配置"}</CardDescription>
          </CardHeader>
          <CardFooter>
            <Button className={cn("w-full", ghostButtonClass())} onClick={() => setActiveSection("ai")}>
              查看配置详情
            </Button>
          </CardFooter>
        </Card>
        <Card className={cardClass()}>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <ShieldCheck className="h-4 w-4" />
              错题本
            </CardTitle>
            <CardDescription>
              {wrongStats ? `累计 ${wrongStats.total_wrong} 道错题` : "尚未产生错题"}
            </CardDescription>
          </CardHeader>
          <CardFooter>
            <Button className={cn("w-full", ghostButtonClass())} onClick={() => setActiveSection("wrong")}>
              打开错题本
            </Button>
          </CardFooter>
        </Card>
      </div>
    </div>
  );

  const renderPractice = () => (
    <div className="space-y-6">
      <div className="grid gap-6 lg:grid-cols-[360px,1fr]">
        <div className="space-y-6">
          <Card className={cardClass()}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Layers className="h-4 w-4" />
                知识来源
              </CardTitle>
              <CardDescription>上传自定义文档或切换至内置知识库。</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 text-sm">
              <div className="rounded-2xl border p-4">
                <p className="text-xs uppercase text-muted-foreground">当前文件</p>
                <p className="mt-1 font-medium break-words">{knowledgePath || "未选择"}</p>
                {uploadPreview && <p className="mt-2 text-xs text-emerald-700">{uploadPreview}</p>}
              </div>
              <div className="flex flex-col gap-3">
                <Button
                  variant="outline"
                  className={cn("justify-center", ghostButtonClass())}
                  onClick={() => {
                    setKnowledgePath(DEFAULT_KNOWLEDGE_PATH);
                    setUploadPreview("已切换到内置知识库");
                  }}
                >
                  <FileCheck className="mr-2 h-4 w-4" />
                  使用内置知识库
                </Button>
                <label className="flex cursor-pointer flex-col items-center justify-center rounded-2xl border border-dashed p-6 text-center text-sm text-muted-foreground hover:border-primary">
                  <UploadCloud className="mb-2 h-6 w-6" />
                  将 .md/.txt/.pdf 拖拽到此，或点击选择文件
                  <Input
                    type="file"
                    accept=".md,.txt,.pdf"
                    className="sr-only"
                    onChange={(event) => {
                      const file = event.target.files?.[0];
                      if (file) void handleUpload(file);
                    }}
                    disabled={uploading}
                  />
                </label>
                <div className="rounded-2xl border p-4 space-y-3">
                  <div className="flex items-center gap-2 text-sm font-medium text-foreground">
                    <Layers className="h-4 w-4" />
                    直接粘贴文本
                  </div>
                  <Textarea
                    rows={4}
                    placeholder="粘贴一段 Markdown/文本，点击上传即可生成知识条目"
                    value={textUpload}
                    onChange={(event) => setTextUpload(event.target.value)}
                  />
                  <Button
                    size="sm"
                    onClick={uploadTextSnippet}
                    disabled={uploading}
                    className={cn("w-full sm:w-auto", primaryButtonClass())}
                  >
                    上传文本
                  </Button>
                </div>
                {uploading && (
                  <p className="flex items-center gap-2 text-xs text-muted-foreground">
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    正在解析文档...
                  </p>
                )}
              </div>
            </CardContent>
          </Card>

          <Card className={cardClass()}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <FilePlus2 className="h-4 w-4" />
                出题参数
              </CardTitle>
              <CardDescription>用于 `/api/generate-questions` 请求。</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <p className="text-sm font-medium">题型筛选</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {QUESTION_FILTERS.map((filter) => {
                    const active = practiceTypes.includes(filter.value);
                    return (
                      <Button
                        key={filter.value}
                        size="sm"
                        variant={active ? "default" : "outline"}
                        onClick={() => toggleQuestionType(filter.value)}
                      >
                        {filter.label}
                      </Button>
                    );
                  })}
                </div>
              </div>
              <div className="grid gap-4">
                <div className="space-y-2">
                  <Label>题目数量</Label>
                  <Input
                    type="number"
                    min={1}
                    value={questionCount}
                    onChange={(event) => setQuestionCount(Number(event.target.value))}
                  />
                </div>
                <div className="space-y-2">
                  <Label>模式</Label>
                  <Select value={questionMode} onValueChange={(value) => setQuestionMode(value as "sequential" | "random")}>
                    <SelectTrigger>
                      <SelectValue placeholder="顺序出题" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="sequential">顺序</SelectItem>
                      <SelectItem value="random">随机</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>随机种子（可选）</Label>
                  <Input value={seed} placeholder="42" onChange={(event) => setSeed(event.target.value)} />
                </div>
              </div>
              <div className="flex items-center justify-between rounded-2xl border p-3 text-sm">
                <div>
                  <p className="font-medium">AI 生成</p>
                  <p className="text-xs text-muted-foreground">优先调用模型生成，失败后回退本地题库。</p>
                </div>
                <Switch checked={useAi} onCheckedChange={(checked) => setUseAi(checked)} />
              </div>
            </CardContent>
            <CardFooter>
              <Button className={cn("w-full", primaryButtonClass())} onClick={startPractice} disabled={practiceLoading}>
                {practiceLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {practiceLoading ? "生成中..." : "开始练习"}
              </Button>
            </CardFooter>
          </Card>
        </div>
        <div className="space-y-6">
          <Card className={cardClass()}>
            <CardHeader>
              <CardTitle className="text-lg">练习题</CardTitle>
              <CardDescription>
                {questionState ? questionState.identifier : practiceSummary ? "本次练习已完成" : "等待开始"}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {questionLoading && (
                <p className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  正在加载题目...
                </p>
              )}
              {questionState ? (
                <>
                  <div className="flex flex-wrap gap-2">
                    <Badge className={badgePrimaryClass()}>{QUESTION_TYPE_LABEL[questionState.question_type]}</Badge>
                    {questionState.keywords?.length ? (
                      <Badge className={badgeGhostClass()}>关键词 {questionState.keywords.length}</Badge>
                    ) : null}
                  </div>
                  <p className="text-lg font-semibold">{questionState.prompt}</p>
                  {renderAnswerInput()}
                </>
              ) : (
                <p className="text-sm text-muted-foreground">
                  点击“开始练习”后，题目将显示在这里。
                </p>
              )}
              {practiceMessage && <p className="text-sm text-amber-600">{practiceMessage}</p>}
              {renderFeedback()}
              {practiceSummary && (
                <div className="rounded-2xl border border-primary/40 bg-primary/5 p-4 text-sm">
                  <p className="font-semibold">会话完成</p>
                  <p className="text-2xl font-bold">{practiceSummary.correct_count} / {practiceSummary.total_count}</p>
                  <p className="text-muted-foreground">数据已写入 `data/answer_history.jsonl`。</p>
                </div>
              )}
            </CardContent>
            <CardFooter className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <p className="text-sm text-muted-foreground">
                当前第 {Math.min(currentIndex, totalCount) || 0} / {totalCount || 0} 题
              </p>
              <div className="flex gap-3 w-full md:w-auto">
                <Button
                  variant="ghost"
                  className={cn("flex-1", ghostButtonClass())}
                  onClick={() => loadQuestion()}
                  disabled={questionLoading || !sessionId}
                >
                  下一题
                </Button>
                <Button
                  className={cn("flex-1", primaryButtonClass())}
                  onClick={handleSubmitAnswer}
                  disabled={!sessionId || questionLoading}
                >
                  提交答案
                </Button>
              </div>
            </CardFooter>
          </Card>
        </div>
      </div>
    </div>
  );

  const renderAnswerInput = () => {
    if (!questionState) return null;
    if (questionState.question_type === "CLOZE") {
      return (
        <div className="space-y-2">
          <Label>请输入答案</Label>
          <Input
            placeholder="例如：110% 触发声光报警"
            value={textAnswer}
            onChange={(event) => setTextAnswer(event.target.value)}
          />
        </div>
      );
    }
    if (questionState.question_type === "QA") {
      return (
        <div className="space-y-2">
          <Label>回答内容</Label>
          <Textarea
            rows={4}
            placeholder="描述检查要点或处理步骤"
            value={textAnswer}
            onChange={(event) => setTextAnswer(event.target.value)}
          />
        </div>
      );
    }
    return (
      <div className="space-y-3">
        {questionState.options?.map((option, index) => {
          const key = String.fromCharCode(65 + index);
          const active = selectedOptions.includes(key);
          return (
            <button
              key={key}
              type="button"
              onClick={() => {
                if (questionState.question_type === "SINGLE_CHOICE") {
                  setSelectedOptions([key]);
                } else {
                  setSelectedOptions((prev) => {
                    const set = new Set(prev);
                    if (set.has(key)) set.delete(key);
                    else set.add(key);
                    return Array.from(set);
                  });
                }
              }}
              className={cn(
                "flex w-full items-center justify-between rounded-2xl border p-4 text-left transition",
                active ? "border-primary bg-primary/10" : "hover:border-primary/40"
              )}
            >
              <div className="flex items-center gap-3">
                <span className="flex h-9 w-9 items-center justify-center rounded-full bg-muted font-semibold">
                  {key}
                </span>
                <p className="text-sm text-foreground">{option}</p>
              </div>
              {active && <CheckCircle2 className="h-5 w-5 text-primary" />}
            </button>
          );
        })}
      </div>
    );
  };

  const renderFeedback = () => {
    if (!submissionResult) return null;
    const success = submissionResult.is_correct;
    return (
      <div
        className={cn(
          "rounded-2xl border p-4",
          success ? "border-emerald-200 bg-emerald-50" : "border-amber-200 bg-amber-50"
        )}
      >
        <div className="flex items-center gap-2 text-sm font-medium">
          {success ? (
            <>
              <CheckCircle2 className="h-4 w-4 text-emerald-600" />
              回答正确
            </>
          ) : (
            <>
              <AlertCircle className="h-4 w-4 text-amber-600" />
              回答不正确
            </>
          )}
        </div>
        <p className="mt-1 text-sm text-muted-foreground whitespace-pre-line">{submissionResult.explanation}</p>
        {submissionResult.correct_answer && (
          <p className="mt-2 text-xs text-muted-foreground">参考答案：{submissionResult.correct_answer}</p>
        )}
      </div>
    );
  };

  const renderAiConfig = () => (
    <div className="grid gap-6 lg:grid-cols-2">
      <Card className={cardClass()}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Brain className="h-4 w-4" />
            模型配置
          </CardTitle>
          <CardDescription>对接 `/api/ai-config` 读写接口。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>请求 URL</Label>
            <Input
              value={aiConfig.url}
              onChange={(event) => setAiConfig((prev) => ({ ...prev, url: event.target.value }))}
              placeholder="https://api.openai.com/v1/chat/completions"
            />
          </div>
          <div className="space-y-2">
            <Label>模型</Label>
            <Input
              value={aiConfig.model}
              onChange={(event) => setAiConfig((prev) => ({ ...prev, model: event.target.value }))}
              placeholder="gpt-4o-mini"
            />
          </div>
          <div className="space-y-2">
            <Label>API Key</Label>
            <Input
              type="password"
              value={aiConfig.key}
              onChange={(event) => setAiConfig((prev) => ({ ...prev, key: event.target.value }))}
              placeholder="sk-..."
            />
          </div>
          <div className="space-y-2">
            <Label>超时时间（秒）</Label>
            <Input
              type="number"
              min={5}
              value={aiConfig.timeout}
              onChange={(event) => setAiConfig((prev) => ({ ...prev, timeout: Number(event.target.value) }))}
            />
          </div>
          <div className="space-y-2">
            <Label>开发文档链接（可选）</Label>
            <Input
              value={aiConfig.dev_document ?? ""}
              onChange={(event) => setAiConfig((prev) => ({ ...prev, dev_document: event.target.value }))}
              placeholder="https://..."
            />
          </div>
        </CardContent>
        <CardFooter className="flex flex-col gap-2">
          <Button onClick={testAiConfig} disabled={aiStatus.state === "loading"} className={primaryButtonClass()}>
            <Sparkles className="mr-2 h-4 w-4" />
            测试连通性
          </Button>
          <Button className={ghostButtonClass()} onClick={saveAiConfig} disabled={aiStatus.state === "loading"}>
            保存配置
          </Button>
          {aiStatus.message && (
            <p
              className={cn(
                "w-full rounded-lg border px-3 py-2 text-sm",
                aiStatus.state === "error"
                  ? "border-destructive bg-destructive/10 text-destructive"
                  : "border-emerald-200 bg-emerald-50 text-emerald-700"
              )}
            >
              {aiStatus.message}
            </p>
          )}
        </CardFooter>
      </Card>
      <Card className={cardClass()}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <FileBarChart2 className="h-4 w-4" />
            使用指南
          </CardTitle>
          <CardDescription>帮助运维人员快速验证模型接入。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 text-sm text-muted-foreground">
          <div>
            <p className="font-semibold text-foreground">1. 配置存储</p>
            <p>所有配置写入 `AI_cf/cf.json`，后端 CLI (`manage_ai_config.py`) 与 Web 前端共享同一套数据。</p>
          </div>
          <div>
            <p className="font-semibold text-foreground">2. 调用链路</p>
            <p>题目生成先调用 AI；如果失败自动降级本地题库，过程无需人工介入。</p>
          </div>
          <div>
            <p className="font-semibold text-foreground">3. 安全提醒</p>
            <p>请勿上传真实密钥到远端仓库，`.gitignore` 已屏蔽 `AI_cf/` 与 `.env`。</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );

  const renderWrongBook = () => (
    <div className="grid gap-6 lg:grid-cols-[360px,1fr]">
      <Card className={cardClass()}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <ShieldCheck className="h-4 w-4" />
            错题统计
          </CardTitle>
          <CardDescription>来自 `/api/wrong-questions/stats`</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {wrongStats ? (
            <>
              <div className="rounded-2xl border p-4 text-sm">
                <p className="text-muted-foreground">错题总数</p>
                <p className="text-3xl font-semibold">{wrongStats.total_wrong}</p>
              </div>
              <div>
                <p className="text-xs uppercase text-muted-foreground">薄弱知识点</p>
                <div className="mt-2 space-y-1 text-sm">
                  {wrongStats.weakest_topics.map((topic) => (
                    <p key={topic.topic}>
                      {topic.topic} · {topic.count} 题
                    </p>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">暂无数据，完成答题后自动生成。</p>
          )}
        </CardContent>
      </Card>
      <Card className={cardClass()}>
        <CardHeader>
          <CardTitle className="text-base">错题列表</CardTitle>
          <CardDescription>最近 5 条错题，数据来源 `data/wrong_questions.json`。</CardDescription>
        </CardHeader>
        <CardContent>
          <ScrollArea className="h-96">
            <div className="space-y-3 pr-3">
              {wrongList.length === 0 && (
                <p className="text-sm text-muted-foreground">暂无错题记录。</p>
              )}
              {wrongList.map((item) => (
                <div key={item.question.identifier} className="rounded-2xl border p-4 text-sm">
                  <div className="flex items-center justify-between">
                    <p className="font-medium">{item.question.prompt.slice(0, 22)}...</p>
                    <Badge className={badgeGhostClass()}>{QUESTION_TYPE_LABEL[item.question.question_type]}</Badge>
                  </div>
                  <p className="text-xs text-muted-foreground">最近答错：{item.last_wrong_at ?? "—"}</p>
                  {item.last_plain_explanation && (
                    <p className="mt-2 text-xs text-muted-foreground line-clamp-2">
                      {item.last_plain_explanation}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  );

  const renderHistory = () => (
    <Card className={cardClass()}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <History className="h-4 w-4" />
          最近会话
        </CardTitle>
        <CardDescription>调用 `/api/answer-history/sessions`，列出最近 5 次练习。</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {historySummaries.length === 0 && (
          <p className="text-sm text-muted-foreground">尚无历史纪录，完成一次练习后即可查看。</p>
        )}
        {historySummaries.map((item) => (
          <div key={item.session_id} className="rounded-2xl border p-4">
            <div className="flex items-center justify-between text-sm">
              <p className="font-semibold">会话 {item.session_id.slice(0, 8)}</p>
              <p className="text-muted-foreground">{item.latest_at}</p>
            </div>
            <Progress value={Math.round((item.accuracy ?? 0) * 100)} className="my-3" />
            <div className="text-xs text-muted-foreground">
              正确率 {(item.accuracy * 100).toFixed(1)}%，共 {item.total_answers} 题，模式 {item.mode ?? "CLI/Web"}
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );

  const sectionContent: Record<SectionKey, JSX.Element> = {
    dashboard: renderDashboard(),
    practice: renderPractice(),
    ai: renderAiConfig(),
    wrong: renderWrongBook(),
    history: renderHistory(),
  };

  return (
    <div className={cn("min-h-screen transition-colors duration-300", themeTokens.shell)}>
      <div className="mx-auto max-w-6xl px-4 py-10">
        <header>
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <p className={cn("text-xs uppercase tracking-[0.4em]", mutedText)}>QA SYSTEM</p>
              <h1 className="mt-2 text-3xl font-semibold">答题考试系统AI版</h1>
            </div>
            <div className="flex items-center gap-3 text-xs">
              <span className={cn("flex items-center gap-1", mutedText)}>
                <Sparkles className="h-3.5 w-3.5 text-emerald-400" />
                shadcn/ui
              </span>
              <span className={cn("flex items-center gap-1", mutedText)}>
                <UploadCloud className="h-3.5 w-3.5 text-blue-300" />
                Flask API
              </span>
              <Button
                variant="ghost"
                className={cn(
                  "h-11 w-11 rounded-full p-0",
                  ghostButtonClass("flex items-center justify-center")
                )}
                aria-label={theme === "dark" ? "切换到白天主题" : "切换到夜间主题"}
                onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
              >
                {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
              </Button>
            </div>
          </div>
          <nav className={navClass}>
            <Tabs value={activeSection} onValueChange={(value) => setActiveSection(value as SectionKey)}>
              <TabsList className="flex w-full flex-wrap gap-2 bg-transparent p-0">
                {SECTION_NAV.map((section) => (
                  <TabsTrigger
                    key={section.key}
                    value={section.key}
                    className={cn(
                      "flex-1 rounded-xl px-3 py-2 text-sm font-medium transition-colors",
                      tabTriggerClass
                    )}
                  >
                    <span className="flex items-center justify-center gap-2">
                      {section.icon}
                      {section.label}
                    </span>
                  </TabsTrigger>
                ))}
              </TabsList>
            </Tabs>
          </nav>
        </header>

        <section className="mt-8 space-y-6">
          {sectionContent[activeSection]}
        </section>

        <footer className={cn("mt-10 border-t pt-6 text-xs", footerClass)}>
          数据接口来自 `web_server.py`，若需自定义后端，调整 `frontend/shadcn-app/src/lib/api.ts` 即可。保持 `python web_server.py` 与 `npm run dev` 并行运行以获得最佳体验。
          {asideLoading && (
            <span className={cn("ml-2 inline-flex items-center gap-1", mutedText)}>
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              正在同步后端数据...
            </span>
          )}
        </footer>
      </div>
    </div>
  );
}
