import type { ToolInvocationEvidence as ToolInvocationEvidenceData } from "./types";

interface ToolInvocationEvidenceProps {
  evidence: ToolInvocationEvidenceData | null;
}

function formatTimestamp(timestamp: number | null): string {
  if (!timestamp) return "未记录";
  return new Date(timestamp).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function ShortValue({ value }: { value: string | null }) {
  return <span className="tool-evidence-value">{value || "暂无"}</span>;
}

export default function ToolInvocationEvidence({ evidence }: ToolInvocationEvidenceProps) {
  const hasEvidence = Boolean(evidence?.toolName || evidence?.skillId || evidence?.runId);
  const proof = evidence?.toolName
    ? `${evidence.activeSkillName ?? evidence.skillId ?? "所选技能"} 激活了 ${evidence.toolName} 并生成了结构化输出。`
    : "运行一个技能以捕获工具调用证据。";

  return (
    <section className="tool-evidence" aria-label="工具调用证据">
      <div className="tool-evidence-header">
        <div>
          <div className="tool-evidence-kicker">调用证据</div>
          <h3 className="tool-evidence-title">工具调用证据</h3>
        </div>
        <span className={`tool-evidence-badge ${hasEvidence ? "tool-evidence-badge--ready" : ""}`}>
          {hasEvidence ? "已捕获" : "等待中"}
        </span>
      </div>

      <dl className="tool-evidence-grid">
        <div className="tool-evidence-row">
          <dt>运行 ID</dt>
          <dd><ShortValue value={evidence?.runId ?? null} /></dd>
        </div>
        <div className="tool-evidence-row">
          <dt>当前技能</dt>
          <dd><ShortValue value={evidence?.activeSkillName ?? evidence?.skillId ?? null} /></dd>
        </div>
        <div className="tool-evidence-row">
          <dt>技能 ID</dt>
          <dd><ShortValue value={evidence?.skillId ?? null} /></dd>
        </div>
        <div className="tool-evidence-row">
          <dt>工具名称</dt>
          <dd><ShortValue value={evidence?.toolName ?? null} /></dd>
        </div>
        <div className="tool-evidence-row">
          <dt>开始时间</dt>
          <dd>{formatTimestamp(evidence?.startedAt ?? null)}</dd>
        </div>
        <div className="tool-evidence-row">
          <dt>完成时间</dt>
          <dd>{formatTimestamp(evidence?.completedAt ?? null)}</dd>
        </div>
      </dl>

      <div className="tool-evidence-output">
        <div className="tool-evidence-label">输出字段</div>
        {evidence?.outputKeys.length ? (
          <div className="tool-evidence-chips">
            {evidence.outputKeys.map((key) => (
              <span className="tool-evidence-chip" key={key}>{key}</span>
            ))}
          </div>
        ) : (
          <p className="tool-evidence-empty">尚未捕获结构化输出。</p>
        )}
      </div>

      <p className="tool-evidence-proof">{proof}</p>
    </section>
  );
}
