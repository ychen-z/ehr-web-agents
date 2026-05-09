import type { ToolInvocationEvidence as ToolInvocationEvidenceData } from "./types";

interface ToolInvocationEvidenceProps {
  evidence: ToolInvocationEvidenceData | null;
}

function formatTimestamp(timestamp: number | null): string {
  if (!timestamp) return "Not recorded";
  return new Date(timestamp).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function ShortValue({ value }: { value: string | null }) {
  return <span className="tool-evidence-value">{value || "Not available"}</span>;
}

export default function ToolInvocationEvidence({ evidence }: ToolInvocationEvidenceProps) {
  const hasEvidence = Boolean(evidence?.toolName || evidence?.skillId || evidence?.runId);
  const proof = evidence?.toolName
    ? `${evidence.activeSkillName ?? evidence.skillId ?? "Selected skill"} activated ${evidence.toolName} and produced structured output.`
    : "Run a skill to capture tool invocation evidence.";

  return (
    <section className="tool-evidence" aria-label="Tool invocation evidence">
      <div className="tool-evidence-header">
        <div>
          <div className="tool-evidence-kicker">Invocation Evidence</div>
          <h3 className="tool-evidence-title">Tool Invocation Evidence</h3>
        </div>
        <span className={`tool-evidence-badge ${hasEvidence ? "tool-evidence-badge--ready" : ""}`}>
          {hasEvidence ? "Captured" : "Waiting"}
        </span>
      </div>

      <dl className="tool-evidence-grid">
        <div className="tool-evidence-row">
          <dt>Run ID</dt>
          <dd><ShortValue value={evidence?.runId ?? null} /></dd>
        </div>
        <div className="tool-evidence-row">
          <dt>Active Skill</dt>
          <dd><ShortValue value={evidence?.activeSkillName ?? evidence?.skillId ?? null} /></dd>
        </div>
        <div className="tool-evidence-row">
          <dt>Skill ID</dt>
          <dd><ShortValue value={evidence?.skillId ?? null} /></dd>
        </div>
        <div className="tool-evidence-row">
          <dt>Tool Name</dt>
          <dd><ShortValue value={evidence?.toolName ?? null} /></dd>
        </div>
        <div className="tool-evidence-row">
          <dt>Started At</dt>
          <dd>{formatTimestamp(evidence?.startedAt ?? null)}</dd>
        </div>
        <div className="tool-evidence-row">
          <dt>Completed At</dt>
          <dd>{formatTimestamp(evidence?.completedAt ?? null)}</dd>
        </div>
      </dl>

      <div className="tool-evidence-output">
        <div className="tool-evidence-label">Output Keys</div>
        {evidence?.outputKeys.length ? (
          <div className="tool-evidence-chips">
            {evidence.outputKeys.map((key) => (
              <span className="tool-evidence-chip" key={key}>{key}</span>
            ))}
          </div>
        ) : (
          <p className="tool-evidence-empty">No structured output captured yet.</p>
        )}
      </div>

      <p className="tool-evidence-proof">{proof}</p>
    </section>
  );
}
