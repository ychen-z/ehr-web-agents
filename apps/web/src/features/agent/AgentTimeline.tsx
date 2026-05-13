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
  if (status === "running") return "运行中";
  if (status === "completed") return "已完成";
  if (status === "failed") return "失败";
  return "就绪";
}

export default function AgentTimeline({
  activeSkillName,
  activeSkillId,
  runStatus,
  items,
}: AgentTimelineProps) {
  const hasSkill = Boolean(activeSkillName || activeSkillId);

  return (
    <section className="agent-timeline" aria-label="智能体运行时间线">
      <div className="agent-timeline-active">
        <div>
          <div className="agent-timeline-kicker">当前技能</div>
          <h3 className="agent-timeline-skill">
            {activeSkillName ?? activeSkillId ?? "未选择技能"}
          </h3>
        </div>
        <span className={`agent-timeline-status agent-timeline-status--${runStatus}`}>
          {hasSkill ? skillStatusLabel(runStatus) : "未选择"}
        </span>
      </div>

      <div className="agent-timeline-header">
        <h3 className="agent-timeline-title">智能体时间线</h3>
        <span className="agent-timeline-count">{items.length} 个事件</span>
      </div>

      {items.length === 0 ? (
        <p className="agent-timeline-empty">
          智能体选择技能、调用工具和流式输出模型响应时，运行事件将在此显示。
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
