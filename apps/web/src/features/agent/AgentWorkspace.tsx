import {
  useState,
  useCallback,
  useRef,
  useEffect,
  useMemo,
} from "react";
import { useAuth } from "@/features/auth/useAuth";
import { fetchSkills, type SkillResponse } from "@/features/skills/skillsApi";
import {
  fetchModels,
  type ModelConfigResponse,
} from "@/features/models/modelApi";
import {
  fetchConversations,
  fetchMessages,
  type ConversationResponse,
  type MessageResponse,
} from "@/features/conversations/conversationApi";
import {
  createRun,
  type RunCreate,
} from "@/features/agent/agentApi";
import {
  subscribeToRunEvents,
  type RunEventHandlers,
} from "@/lib/sse";
import { useMediaQuery } from "@/lib/useMediaQuery";
import Sidebar from "./Sidebar";
import ChatPanel from "./ChatPanel";
import ResultPanel from "./ResultPanel";
import SkillsMarketplace from "@/features/skills/SkillsMarketplace";
import type {
  ChatMessage,
  StructuredResult,
  ActiveRun,
  AgentTimelineItem,
  PanelView,
  SSEEventType,
  ToolInvocationEvidence,
} from "./types";

const TIMELINE_LABELS: Record<SSEEventType, string> = {
  run_started: "运行已启动",
  skill_selected: "技能已选择",
  tool_started: "工具调用开始",
  tool_completed: "工具调用完成",
  model_delta: "模型响应",
  structured_result: "结构化结果",
  run_completed: "运行已完成",
  run_failed: "运行失败",
  stream_closed: "流已关闭",
};

function timelineDescription(eventType: SSEEventType, data: Record<string, unknown>): string {
  if (eventType === "skill_selected") {
    return `已激活 ${(data.name as string) || (data.skill_id as string) || "所选技能"}。`;
  }
  if (eventType === "tool_started") {
    return `正在调用 ${(data.tool_name as string) || "工具"}。`;
  }
  if (eventType === "tool_completed") {
    return `${(data.tool_name as string) || "工具"} 调用完成。`;
  }
  if (eventType === "model_delta") return "模型返回响应内容。";
  if (eventType === "structured_result") return "结构化输出已就绪。";
  if (eventType === "run_failed") return (data.error as string) || "运行失败。";
  if (eventType === "run_completed") return "智能体运行成功完成。";
  if (eventType === "stream_closed") return "事件流已关闭。";
  return "智能体运行已初始化。";
}

function messageResponseToChatAction(
  m: MessageResponse,
): ChatMessage {
  return {
    id: m.id,
    role: m.role as ChatMessage["role"],
    content: m.content,
    timestamp: new Date(m.created_at).getTime(),
    status: "complete",
  };
}

export default function AgentWorkspace() {
  const { token, user } = useAuth();

  const [skills, setSkills] = useState<SkillResponse[]>([]);
  const [models, setModels] = useState<ModelConfigResponse[]>([]);
  const [conversations, setConversations] = useState<ConversationResponse[]>(
    [],
  );
  const [sidebarLoading, setSidebarLoading] = useState(true);
  const [sidebarError, setSidebarError] = useState<string | null>(null);

  const [activeSkillId, setActiveSkillId] = useState<string | null>(null);
  const [activeModelProviderId, setActiveModelProviderId] = useState<
    string | null
  >(null);
  const [activeConversationId, setActiveConversationId] = useState<
    string | null
  >(null);

  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [results, setResults] = useState<StructuredResult[]>([]);
  const [timelineItems, setTimelineItems] = useState<AgentTimelineItem[]>([]);
  const [toolEvidence, setToolEvidence] = useState<ToolInvocationEvidence | null>(null);
  const [activeRun, setActiveRun] = useState<ActiveRun | null>(null);

  const [marketplaceOpen, setMarketplaceOpen] = useState(false);
  const [mobilePanel, setMobilePanel] = useState<PanelView>(null);
  const [messagesLoading, setMessagesLoading] = useState(false);
  const [, setIsSubmitting] = useState(false);

  const sseRef = useRef<ReturnType<typeof subscribeToRunEvents> | null>(null);
  const resultCounterRef = useRef(0);
  const msgCounterRef = useRef(0);
  const timelineCounterRef = useRef(0);
  const submittingRef = useRef(false);
  const initialModelSelectRef = useRef(false);

  const sidebarCloseRef = useRef<HTMLButtonElement>(null);
  const resultsCloseRef = useRef<HTMLButtonElement>(null);

  const isWide = useMediaQuery("(min-width: 900px)");
  const isMedium = useMediaQuery("(min-width: 700px)");

  const visibleSidebar = isWide || mobilePanel === "sidebar";
  const visibleResults = isMedium || mobilePanel === "results";

  const activeSkill = useMemo(
    () => skills.find((s) => s.skill_id === activeSkillId),
    [skills, activeSkillId],
  );

  const selectedSkillName = activeSkill?.name ?? null;
  const selectedToolName = activeSkill?.mock_tool_name ?? null;

  const runStatus = activeRun?.status ?? "idle";

  const modelNotConfigured = useMemo(() => {
    const mc = models.find((m) => m.provider_id === activeModelProviderId);
    return mc ? !mc.configured : false;
  }, [models, activeModelProviderId]);

  const loadSidebarData = useCallback(async () => {
    try {
      setSidebarLoading(true);
      setSidebarError(null);
      const [s, m, c] = await Promise.all([
        fetchSkills(),
        fetchModels(),
        fetchConversations({ limit: 50 }),
      ]);
      setSkills(s);
      setModels(m);
      setConversations(c);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "加载工作区数据失败。";
      setSidebarError(message);
    } finally {
      setSidebarLoading(false);
    }
  }, []);

  const loadMessagesForConversation = useCallback(
    async (convId: string) => {
      setMessagesLoading(true);
      try {
        const msgs = await fetchMessages(convId, { limit: 100 });
        setChatMessages(msgs.map(messageResponseToChatAction));
      } catch {
        setChatMessages([]);
      } finally {
        setMessagesLoading(false);
      }
    },
    [],
  );

  useEffect(() => {
    if (token) {
      loadSidebarData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  useEffect(() => {
    if (
      !initialModelSelectRef.current &&
      models.length > 0 &&
      !activeModelProviderId
    ) {
      initialModelSelectRef.current = true;
      setActiveModelProviderId(models[0].provider_id);
    }
  }, [models, activeModelProviderId]);

  useEffect(() => {
    if (activeConversationId && token) {
      loadMessagesForConversation(activeConversationId);
    } else {
      setChatMessages([]);
    }
    setResults([]);
    setTimelineItems([]);
    setToolEvidence(null);
    setActiveRun(null);
  }, [activeConversationId, token, loadMessagesForConversation]);

  useEffect(() => {
    const panel = mobilePanel;
    if (panel === "sidebar" && sidebarCloseRef.current) {
      sidebarCloseRef.current.focus();
    } else if (panel === "results" && resultsCloseRef.current) {
      resultsCloseRef.current.focus();
    }
  }, [mobilePanel]);

  useEffect(() => {
    initialModelSelectRef.current = false;
  }, [token]);

  const cleanupSSE = useCallback(() => {
    if (sseRef.current) {
      sseRef.current.close();
      sseRef.current = null;
    }
  }, []);

  const addTimelineItem = useCallback(
    (eventType: SSEEventType, data: Record<string, unknown>, status: AgentTimelineItem["status"] = "completed") => {
      timelineCounterRef.current += 1;
      setTimelineItems((prev) => [
        ...prev,
        {
          id: `timeline-${Date.now()}-${timelineCounterRef.current}`,
          eventType,
          label: TIMELINE_LABELS[eventType],
          description: timelineDescription(eventType, data),
          timestamp: Date.now(),
          status,
        },
      ]);
    },
    [],
  );

  useEffect(() => {
    return () => cleanupSSE();
  }, [cleanupSSE]);

  const handleSend = useCallback(
    async (content: string) => {
      if (!activeSkillId || !token || submittingRef.current) return;

      submittingRef.current = true;
      setIsSubmitting(true);

      const run: RunCreate = {
        skill_id: activeSkillId,
        user_message: content,
        conversation_id: activeConversationId,
        model_provider_id: activeModelProviderId,
      };

      try {
        setTimelineItems([]);
        setToolEvidence({
          runId: null,
          activeSkillName: selectedSkillName,
          skillId: activeSkillId,
          toolName: null,
          startedAt: null,
          completedAt: null,
          outputKeys: [],
        });
        const runResp = await createRun(run);
        const runId = runResp.id;

        setToolEvidence((prev) => ({
          runId,
          activeSkillName: prev?.activeSkillName ?? selectedSkillName,
          skillId: prev?.skillId ?? activeSkillId,
          toolName: prev?.toolName ?? null,
          startedAt: prev?.startedAt ?? null,
          completedAt: prev?.completedAt ?? null,
          outputKeys: prev?.outputKeys ?? [],
        }));

        setActiveRun({
          runId,
          status: "running",
          assistantContent: "",
        });

        msgCounterRef.current += 1;
        const userMsg: ChatMessage = {
          id: `local-${Date.now()}-${msgCounterRef.current}`,
          role: "user",
          content,
          timestamp: Date.now(),
          status: "complete",
        };
        setChatMessages((prev) => [...prev, userMsg]);

        msgCounterRef.current += 1;
        const assistantMsgId = `local-${Date.now()}-${msgCounterRef.current}`;
        const assistantMsg: ChatMessage = {
          id: assistantMsgId,
          role: "assistant",
          content: "",
          timestamp: Date.now(),
          status: "streaming",
        };
        setChatMessages((prev) => [...prev, assistantMsg]);

        if (!activeConversationId && runResp.conversation_id) {
          setActiveConversationId(runResp.conversation_id);
          setConversations((prev) => [
            ...prev,
            {
              id: runResp.conversation_id!,
              user_id: user!.id,
              title: content.slice(0, 60),
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
            },
          ]);
        }

        cleanupSSE();

        const handlers: RunEventHandlers = {
          onRunStarted: (data) => {
            addTimelineItem("run_started", data, "running");
          },
          onSkillSelected: (data) => {
            addTimelineItem("skill_selected", data, "completed");
            setToolEvidence((prev) => ({
              runId,
              activeSkillName: (data.name as string) || prev?.activeSkillName || selectedSkillName,
              skillId: (data.skill_id as string) || prev?.skillId || activeSkillId,
              toolName: prev?.toolName ?? null,
              startedAt: prev?.startedAt ?? null,
              completedAt: prev?.completedAt ?? null,
              outputKeys: prev?.outputKeys ?? [],
            }));
          },
          onToolStarted: (data) => {
            addTimelineItem("tool_started", data, "running");
            setToolEvidence((prev) => ({
              runId,
              activeSkillName: prev?.activeSkillName ?? selectedSkillName,
              skillId: prev?.skillId ?? activeSkillId,
              toolName: (data.tool_name as string) || prev?.toolName || null,
              startedAt: Date.now(),
              completedAt: prev?.completedAt ?? null,
              outputKeys: prev?.outputKeys ?? [],
            }));
          },
          onToolCompleted: (data) => {
            addTimelineItem("tool_completed", data, "completed");
            setToolEvidence((prev) => ({
              runId,
              activeSkillName: prev?.activeSkillName ?? selectedSkillName,
              skillId: prev?.skillId ?? activeSkillId,
              toolName: (data.tool_name as string) || prev?.toolName || null,
              startedAt: prev?.startedAt ?? null,
              completedAt: Date.now(),
              outputKeys: prev?.outputKeys ?? [],
            }));
          },
          onModelDelta: (data) => {
            addTimelineItem("model_delta", data, "running");
            if (data.content) {
              setChatMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantMsgId
                    ? { ...m, content: m.content + data.content }
                    : m,
                ),
              );
            }
          },
          onStructuredResult: (data) => {
            addTimelineItem("structured_result", data, "completed");
            const output = (data.output as Record<string, unknown>) ?? data;
            setToolEvidence((prev) => ({
              runId,
              activeSkillName: prev?.activeSkillName ?? selectedSkillName,
              skillId: (data.skill_id as string) || prev?.skillId || activeSkillId,
              toolName: (data.tool_name as string) || prev?.toolName || null,
              startedAt: prev?.startedAt ?? null,
              completedAt: prev?.completedAt ?? Date.now(),
              outputKeys: Object.keys(output),
            }));
            resultCounterRef.current += 1;
            const sr: StructuredResult = {
              id: `result-${resultCounterRef.current}`,
              skill_id: (data.skill_id as string) ?? activeSkillId,
              tool_name: (data.tool_name as string) ?? "unknown",
              output:
                (data.output as Record<string, unknown>) ?? data,
              timestamp: Date.now(),
            };
            setResults((prev) => [...prev, sr]);
          },
          onRunCompleted: (data) => {
            addTimelineItem("run_completed", data, "completed");
            setActiveRun(null);
            setChatMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsgId
                  ? { ...m, status: "complete" as const }
                  : m,
              ),
            );
            if (activeConversationId && token) {
              loadMessagesForConversation(activeConversationId);
            }
            submittingRef.current = false;
            setIsSubmitting(false);
          },
          onRunFailed: (data) => {
            addTimelineItem("run_failed", data, "failed");
            const errorText = data.error ?? "智能体运行失败。";
            setChatMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsgId
                  ? {
                      ...m,
                      content: m.content
                        ? `${m.content}\n\nError: ${errorText}`
                        : `Error: ${errorText}`,
                      status: "complete",
                    }
                  : m,
              ),
            );
            setActiveRun(null);
            submittingRef.current = false;
            setIsSubmitting(false);
          },
          onStreamClosed: (data) => {
            addTimelineItem("stream_closed", data, "completed");
            setActiveRun(null);
            setChatMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsgId
                  ? { ...m, status: "complete" as const }
                  : m,
              ),
            );
            submittingRef.current = false;
            setIsSubmitting(false);
          },
        };

        sseRef.current = subscribeToRunEvents(runId, token, handlers);
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "启动智能体运行失败。";
        msgCounterRef.current += 1;
        setChatMessages((prev) => [
          ...prev,
          {
            id: `local-${Date.now()}-${msgCounterRef.current}`,
            role: "assistant",
            content: `Error: ${message}`,
            timestamp: Date.now(),
            status: "complete",
          },
        ]);
        setActiveRun(null);
        submittingRef.current = false;
        setIsSubmitting(false);
      }
    },
    [
      activeSkillId,
      token,
      activeConversationId,
      activeModelProviderId,
      selectedSkillName,
      user,
      loadMessagesForConversation,
      cleanupSSE,
      addTimelineItem,
    ],
  );

  const handleStop = useCallback(() => {
    cleanupSSE();
    setActiveRun(null);
    setChatMessages((prev) =>
      prev.map((m) =>
        m.status === "streaming" ? { ...m, status: "complete" as const } : m,
      ),
    );
    submittingRef.current = false;
    setIsSubmitting(false);
  }, [cleanupSSE]);

  const handleConversationSelect = useCallback((convId: string) => {
    setActiveConversationId(convId);
  }, []);

  const handleSidebarRefresh = useCallback(() => {
    loadSidebarData();
  }, [loadSidebarData]);

  return (
    <div className="workspace">
      <div
        className={`workspace-sidebar ${visibleSidebar ? "workspace-sidebar--open" : "workspace-sidebar--closed"}`}
      >
        <Sidebar
          skills={skills}
          models={models}
          conversations={conversations}
          loading={sidebarLoading}
          error={sidebarError}
          onRefresh={handleSidebarRefresh}
          activeSkillId={activeSkillId}
          onSkillSelect={setActiveSkillId}
          activeModelProviderId={activeModelProviderId}
          onModelSelect={setActiveModelProviderId}
          activeConversationId={activeConversationId}
          onConversationSelect={handleConversationSelect}
          onOpenMarketplace={() => setMarketplaceOpen(true)}
          onNewConversation={(id) => {
            setActiveConversationId(id);
            setConversations((prev) => [
              { id, user_id: user!.id, title: null, created_at: "", updated_at: "" },
              ...prev,
            ]);
          }}
        />
        {!isWide && visibleSidebar && (
          <button
            ref={sidebarCloseRef}
            type="button"
            className="workspace-panel-close"
            onClick={() => setMobilePanel(null)}
            aria-label="关闭侧边栏"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <path d="M4 4L12 12M12 4L4 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          </button>
        )}
      </div>

      <div className="workspace-chat">
        <div className="workspace-mobile-bar">
          <button
            type="button"
            className="workspace-mobile-btn"
            onClick={() =>
              setMobilePanel(mobilePanel === "sidebar" ? null : "sidebar")
            }
            aria-label="切换侧边栏"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <rect x="1" y="2" width="14" height="1.5" rx="0.75" fill="currentColor" />
              <rect x="1" y="7" width="14" height="1.5" rx="0.75" fill="currentColor" />
              <rect x="1" y="12" width="14" height="1.5" rx="0.75" fill="currentColor" />
            </svg>
            <span>菜单</span>
          </button>
          <button
            type="button"
            className="workspace-mobile-btn"
            onClick={() =>
              setMobilePanel(mobilePanel === "results" ? null : "results")
            }
            aria-label="切换结果面板"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <rect x="2" y="2" width="12" height="12" rx="1.5" stroke="currentColor" strokeWidth="1.5" />
              <path d="M6 6L10 10M10 6L6 10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
            <span>结果</span>
          </button>
        </div>
        {messagesLoading ? (
          <div className="workspace-loading" role="status" aria-label="加载消息中">
            <span className="app-loading-spinner" />
            正在加载消息...
          </div>
        ) : (
          <ChatPanel
            messages={chatMessages}
            activeRun={activeRun}
            selectedSkillName={selectedSkillName}
            selectedToolName={selectedToolName}
            modelNotConfigured={modelNotConfigured}
            onSend={handleSend}
            onStop={handleStop}
            disabled={submittingRef.current}
          />
        )}
      </div>

      <div
        className={`workspace-results ${visibleResults ? "workspace-results--open" : "workspace-results--closed"}`}
      >
        <ResultPanel
          results={results}
          activeSkillName={selectedSkillName}
          activeSkillId={activeSkillId}
          runStatus={runStatus}
          timelineItems={timelineItems}
          evidence={toolEvidence}
        />
        {!isMedium && visibleResults && (
          <button
            ref={resultsCloseRef}
            type="button"
            className="workspace-panel-close"
            onClick={() => setMobilePanel(null)}
            aria-label="关闭结果面板"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <path d="M4 4L12 12M12 4L4 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          </button>
        )}
      </div>

      <SkillsMarketplace
        open={marketplaceOpen}
        onClose={() => setMarketplaceOpen(false)}
        onSkillChange={loadSidebarData}
      />
    </div>
  );
}
