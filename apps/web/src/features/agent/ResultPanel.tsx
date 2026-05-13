import { useState, useCallback, useEffect, useRef } from "react";
import AgentTimeline from "./AgentTimeline";
import ToolInvocationEvidence from "./ToolInvocationEvidence";
import type {
  AgentStatus,
  AgentTimelineItem,
  StructuredResult,
  ToolInvocationEvidence as ToolInvocationEvidenceData,
} from "./types";

interface ResultPanelProps {
  results: StructuredResult[];
  activeSkillName: string | null;
  activeSkillId: string | null;
  runStatus: AgentStatus;
  timelineItems: AgentTimelineItem[];
  evidence: ToolInvocationEvidenceData | null;
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (timerRef.current !== null) {
        clearTimeout(timerRef.current);
      }
    };
  }, []);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      if (timerRef.current !== null) {
        clearTimeout(timerRef.current);
      }
      timerRef.current = setTimeout(() => setCopied(false), 2000);
    } catch {
      //
    }
  }, [text]);

  return (
    <button
      type="button"
      className="result-copy-btn"
      onClick={handleCopy}
      aria-label={copied ? "已复制" : "复制到剪贴板"}
    >
      {copied ? "已复制" : "复制"}
    </button>
  );
}

function formatValue(value: unknown): string {
  if (typeof value === "string") return value;
  if (Array.isArray(value)) {
    return value.map((v) => formatValue(v)).join("\n");
  }
  if (typeof value === "object" && value !== null) {
    return JSON.stringify(value, null, 2);
  }
  return String(value ?? "");
}

function renderField(label: string, value: unknown) {
  if (value === null || value === undefined || value === "") return null;
  return (
    <div className="result-field" key={label}>
      <div className="result-field-label">{label}</div>
      <div className="result-field-value">{formatValue(value)}</div>
    </div>
  );
}

function getResultTitle(toolName: string, skillId: string): string {
  const titles: Record<string, string> = {
    generate_jd: "职位描述",
    screen_resume: "简历筛选",
    generate_interview_questions: "面试问题",
    summarize_interview_feedback: "面试反馈总结",
  };
  return titles[toolName] ?? titles[skillId] ?? skillId;
}

function ResultCard({ result }: { result: StructuredResult }) {
  const output = result.output ?? {};
  const title = getResultTitle(result.tool_name, result.skill_id);
  const flatText = Object.entries(output)
    .map(([k, v]) => `${k}: ${formatValue(v)}`)
    .join("\n\n");

  return (
    <div className="result-card">
      <div className="result-card-header">
        <h3 className="result-card-title">{title}</h3>
        <CopyButton text={flatText} />
      </div>
      <div className="result-card-body">
        {Object.entries(output).map(([key, value]) =>
          renderField(formatLabel(key), value),
        )}
      </div>
      <div className="result-card-footer">
        <span className="result-card-tool">{result.tool_name}</span>
        <span className="result-card-time">
          {new Date(result.timestamp).toLocaleTimeString()}
        </span>
      </div>
    </div>
  );
}

function formatLabel(key: string): string {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function ResultPanel({
  results,
  activeSkillName,
  activeSkillId,
  runStatus,
  timelineItems,
  evidence,
}: ResultPanelProps) {
  return (
    <div className="result-panel" role="complementary" aria-label="结构化结果">
      <div className="result-panel-header">
        <h2 className="result-panel-title">结果</h2>
      </div>
      <div className="result-panel-body">
        <AgentTimeline
          activeSkillName={activeSkillName}
          activeSkillId={activeSkillId}
          runStatus={runStatus}
          items={timelineItems}
        />
        <ToolInvocationEvidence evidence={evidence} />
        {results.length === 0 ? (
          <div className="result-empty">
            <div className="result-empty-icon" aria-hidden="true" />
            <p className="result-empty-text">
              智能体运行的结构化输出将在此显示。
            </p>
          </div>
        ) : (
          results.map((r) => <ResultCard key={r.id} result={r} />)
        )}
      </div>
    </div>
  );
}
