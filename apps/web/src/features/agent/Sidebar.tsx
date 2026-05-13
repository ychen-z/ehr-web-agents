import { createConversation } from "@/features/conversations/conversationApi";
import type { SkillResponse } from "@/features/skills/skillsApi";
import type { ModelConfigResponse } from "@/features/models/modelApi";
import type { ConversationResponse } from "@/features/conversations/conversationApi";

interface SidebarProps {
  skills: SkillResponse[];
  models: ModelConfigResponse[];
  conversations: ConversationResponse[];
  loading: boolean;
  error: string | null;
  onRefresh: () => void;
  activeSkillId: string | null;
  onSkillSelect: (skillId: string | null) => void;
  activeModelProviderId: string | null;
  onModelSelect: (providerId: string) => void;
  activeConversationId: string | null;
  onConversationSelect: (conversationId: string) => void;
  onOpenMarketplace: () => void;
  onNewConversation: (id: string) => void;
}

export default function Sidebar({
  skills,
  models,
  conversations,
  loading,
  error,
  onRefresh,
  activeSkillId,
  onSkillSelect,
  activeModelProviderId,
  onModelSelect,
  activeConversationId,
  onConversationSelect,
  onOpenMarketplace,
  onNewConversation,
}: SidebarProps) {
  const handleNewConversation = async () => {
    try {
      const conv = await createConversation({});
      onNewConversation(conv.id);
    } catch {
      //
    }
  };

  const installedSkills = skills.filter((s) => s.installed);
  const selectedModel = models.find(
    (m) => m.provider_id === activeModelProviderId,
  );

  return (
    <div className="sidebar">
      {error && (
        <div className="sidebar-error" role="alert">
          <p className="sidebar-error-text">{error}</p>
          <button
            type="button"
            className="sidebar-error-retry"
            onClick={onRefresh}
          >
            重试
          </button>
        </div>
      )}

      {loading ? (
        <div className="sidebar-loading" role="status" aria-label="正在加载侧边栏数据">
          <span className="sidebar-spinner" />
          加载中...
        </div>
      ) : (
        <>
          <div className="sidebar-section">
            <h3 className="sidebar-heading">已安装技能</h3>
            <div className="sidebar-subtitle">
              已安装的技能可用于智能体运行。
            </div>
            {installedSkills.length === 0 ? (
              <div className="sidebar-empty">
                <p>暂无已安装技能。</p>
              </div>
            ) : (
              <ul
                className="sidebar-list"
                role="listbox"
                aria-label="Installed skills"
              >
                {installedSkills.map((skill) => (
                  <li key={skill.skill_id}>
                    <button
                      type="button"
                      className={`sidebar-item ${activeSkillId === skill.skill_id ? "sidebar-item--active" : ""}`}
                      onClick={() =>
                        onSkillSelect(
                          activeSkillId === skill.skill_id
                            ? null
                            : skill.skill_id,
                        )
                      }
                      role="option"
                      aria-selected={activeSkillId === skill.skill_id}
                    >
                      <span
                        className="sidebar-item-icon skill-icon"
                        aria-hidden="true"
                      />
                      <span className="sidebar-item-text">{skill.name}</span>
                      {activeSkillId === skill.skill_id && (
                        <span className="sidebar-item-badge">使用中</span>
                      )}
                    </button>
                  </li>
                ))}
              </ul>
            )}
            <button
              type="button"
              className="sidebar-action-btn"
              onClick={onOpenMarketplace}
            >
              <span
                className="sidebar-action-icon marketplace-icon"
                aria-hidden="true"
              />
              浏览技能
            </button>
          </div>

          <div className="sidebar-section">
            <h3 className="sidebar-heading">模型服务商</h3>
            {models.length === 0 ? (
              <div className="sidebar-empty">
                <p>暂无可用模型。</p>
              </div>
            ) : (
              <select
                className="sidebar-select"
                value={activeModelProviderId ?? ""}
                onChange={(e) => onModelSelect(e.target.value)}
                aria-label="Select model provider"
              >
                {models.map((m) => (
                  <option key={m.provider_id} value={m.provider_id}>
                    {m.display_name}
                    {!m.configured ? "（未配置）" : ""}
                  </option>
                ))}
              </select>
            )}
            {selectedModel && !selectedModel.configured && (
              <div className="sidebar-warning" role="alert">
                服务商未配置，请设置 API 密钥以启用。
              </div>
            )}
          </div>

          <div className="sidebar-section sidebar-section--conversations">
            <div className="sidebar-section-header">
              <h3 className="sidebar-heading">对话</h3>
              <button
                type="button"
                className="sidebar-new-btn"
                onClick={handleNewConversation}
                aria-label="新建对话"
              >
                <span
                  className="sidebar-action-icon new-icon"
                  aria-hidden="true"
                />
                新建
              </button>
            </div>
            {conversations.length === 0 ? (
              <div className="sidebar-empty">
                <p>暂无对话。</p>
                <p className="sidebar-empty-hint">
                  点击"新建"开始一段对话。
                </p>
              </div>
            ) : (
              <ul
                className="sidebar-list"
                role="listbox"
                aria-label="Conversations"
              >
                {conversations.map((conv) => (
                  <li key={conv.id}>
                    <button
                      type="button"
                      className={`sidebar-item ${activeConversationId === conv.id ? "sidebar-item--active" : ""}`}
                      onClick={() => onConversationSelect(conv.id)}
                      role="option"
                      aria-selected={activeConversationId === conv.id}
                    >
                      <span
                        className="sidebar-item-icon conversation-icon"
                        aria-hidden="true"
                      />
                      <span className="sidebar-item-text">
                        {conv.title ?? `对话 ${conv.id.slice(0, 8)}`}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </>
      )}
    </div>
  );
}
