import { useState, useRef, useEffect, type FormEvent, type KeyboardEvent } from "react";
import type { ChatMessage, ActiveRun } from "./types";

interface ChatPanelProps {
  messages: ChatMessage[];
  activeRun: ActiveRun | null;
  selectedSkillName: string | null;
  selectedToolName: string | null;
  modelNotConfigured: boolean;
  onSend: (content: string) => void;
  onStop: () => void;
  disabled: boolean;
}

function renderContent(content: string) {
  const lines = content.split("\n");
  return lines.map((line, i) => (
    <span key={i}>
      {line}
      {i < lines.length - 1 && <br />}
    </span>
  ));
}

export default function ChatPanel({
  messages,
  activeRun,
  selectedSkillName,
  selectedToolName,
  modelNotConfigured,
  onSend,
  onStop,
  disabled,
}: ChatPanelProps) {
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, activeRun?.assistantContent]);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || disabled || activeRun?.status === "running") return;
    onSend(trimmed);
    setInput("");
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const isRunning = activeRun?.status === "running";
  const canSend =
    !disabled && !isRunning && input.trim().length > 0;

  return (
    <div className="chat-panel">
      <div className="chat-messages" role="log" aria-label="聊天消息" aria-live="polite">
        {messages.length === 0 && !isRunning && (
          <div className="chat-empty">
            <div className="chat-empty-icon" aria-hidden="true" />
            <h2 className="chat-empty-title">招聘智能体工作台</h2>
            <p className="chat-empty-text">
              从技能市场安装技能，选择模型，创建对话，然后描述你的招聘任务。
            </p>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`chat-message chat-message--${msg.role} ${msg.status === "streaming" ? "chat-message--streaming" : ""}`}
          >
            <div className="chat-message-avatar" aria-hidden="true">
              {msg.role === "user" ? "U" : "AI"}
            </div>
            <div className="chat-message-body">
              <div className="chat-message-role">
                {msg.role === "user" ? "你" : "智能体"}
              </div>
              <div className="chat-message-content">
                {renderContent(msg.content)}
                {msg.status === "streaming" && (
                  <span className="chat-cursor" aria-hidden="true">&#9611;</span>
                )}
              </div>
            </div>
          </div>
        ))}

        {isRunning && !activeRun?.assistantContent && (
          <div className="chat-message chat-message--assistant">
            <div className="chat-message-avatar" aria-hidden="true">AI</div>
            <div className="chat-message-body">
              <div className="chat-message-role">Agent</div>
              <div className="chat-typing">
                <span className="chat-typing-dot" />
                <span className="chat-typing-dot" />
                <span className="chat-typing-dot" />
                <span className="chat-typing-label">思考中...</span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="chat-footer">
        {isRunning && (
          <div className="chat-status-bar" role="status">
            <span className="chat-status-spinner" />
            <span className="chat-status-text">
              智能体处理中
              {selectedSkillName ? ` (${selectedSkillName})` : ""}...
            </span>
            <button
              type="button"
              className="chat-stop-btn"
              onClick={onStop}
            >
              停止
            </button>
          </div>
        )}
        {modelNotConfigured && !isRunning && (
          <div className="chat-warning" role="alert">
            所选模型服务商未配置，请先设置 API 密钥。
          </div>
        )}
        <div className="chat-skill-context" aria-live="polite">
          <span>当前技能：{selectedSkillName ?? "无"}</span>
          <span>工具：{selectedToolName ?? "未绑定"}</span>
        </div>
        <form className="chat-form" onSubmit={handleSubmit}>
          <textarea
            ref={textareaRef}
            className="chat-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="描述你的招聘任务...（Shift+Enter 换行）"
            rows={1}
            disabled={disabled || isRunning}
            aria-label="消息输入框"
          />
          <button
            type="submit"
            className="chat-send-btn"
            disabled={!canSend}
            aria-label="发送消息"
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 16 16"
              fill="none"
              aria-hidden="true"
            >
              <path
                d="M1 8L15 1L8 15L6 9L1 8Z"
                fill="currentColor"
                stroke="currentColor"
                strokeWidth="1"
                strokeLinejoin="round"
              />
            </svg>
          </button>
        </form>
      </div>
    </div>
  );
}
