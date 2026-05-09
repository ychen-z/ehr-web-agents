import type { AgentStatus, AgentTimelineItem } from "./types";

interface AgentTimelineProps {
  activeSkillName: string | null;
  activeSkillId: string | null;
  runStatus: AgentStatus;
  items: AgentTimelineItem[];
}

function formatTime(timestamp: number): string {
  return new Date(timestamp).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function skillStatusLabel(status: AgentStatus): string {
  if (status === "running") return "Running";
  if (status === "completed") return "Completed";
  if (status === "failed") return "Failed";
  return "Ready";
}

export default function AgentTimeline({
  activeSkillName,
  activeSkillId,
  runStatus,
  items,
}: AgentTimelineProps) {
  const hasSkill = Boolean(activeSkillName || activeSkillId);

  return (
    <section className="agent-timeline" aria-label="Agent runtime timeline">
      <div className="agent-timeline-active">
        <div>
          <div className="agent-timeline-kicker">Active Skill</div>
          <h3 className="agent-timeline-skill">
            {activeSkillName ?? activeSkillId ?? "No skill selected"}
          </h3>
        </div>
        <span className={`agent-timeline-status agent-timeline-status--${runStatus}`}>
          {hasSkill ? skillStatusLabel(runStatus) : "Not selected"}
        </span>
      </div>

      <div className="agent-timeline-header">
        <h3 className="agent-timeline-title">Agent Timeline</h3>
        <span className="agent-timeline-count">{items.length} events</span>
      </div>

      {items.length === 0 ? (
        <p className="agent-timeline-empty">
          Run events will appear here as the agent selects skills, invokes tools,
          and streams model output.
        </p>
      ) : (
        <ol className="agent-timeline-list">
          {items.map((item) => (
            <li
              key={item.id}
              className={`agent-timeline-item agent-timeline-item--${item.status}`}
            >
              <span className="agent-timeline-dot" aria-hidden="true" />
              <div className="agent-timeline-body">
                <div className="agent-timeline-row">
                  <span className="agent-timeline-label">{item.label}</span>
                  <time className="agent-timeline-time" dateTime={new Date(item.timestamp).toISOString()}>
                    {formatTime(item.timestamp)}
                  </time>
                </div>
                <p className="agent-timeline-description">{item.description}</p>
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
