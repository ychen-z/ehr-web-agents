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
            Retry
          </button>
        </div>
      )}

      {loading ? (
        <div className="sidebar-loading" role="status" aria-label="Loading sidebar data">
          <span className="sidebar-spinner" />
          Loading...
        </div>
      ) : (
        <>
          <div className="sidebar-section">
            <h3 className="sidebar-heading">Installed Skills</h3>
            <div className="sidebar-subtitle">
              Installed skills are available for agent runs.
            </div>
            {installedSkills.length === 0 ? (
              <div className="sidebar-empty">
                <p>No skills installed.</p>
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
                        <span className="sidebar-item-badge">active</span>
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
              Browse Skills
            </button>
          </div>

          <div className="sidebar-section">
            <h3 className="sidebar-heading">Model Provider</h3>
            {models.length === 0 ? (
              <div className="sidebar-empty">
                <p>No models available.</p>
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
                    {!m.configured ? " (not configured)" : ""}
                  </option>
                ))}
              </select>
            )}
            {selectedModel && !selectedModel.configured && (
              <div className="sidebar-warning" role="alert">
                Provider not configured. Set API key to enable.
              </div>
            )}
          </div>

          <div className="sidebar-section sidebar-section--conversations">
            <div className="sidebar-section-header">
              <h3 className="sidebar-heading">Conversations</h3>
              <button
                type="button"
                className="sidebar-new-btn"
                onClick={handleNewConversation}
                aria-label="New conversation"
              >
                <span
                  className="sidebar-action-icon new-icon"
                  aria-hidden="true"
                />
                New
              </button>
            </div>
            {conversations.length === 0 ? (
              <div className="sidebar-empty">
                <p>No conversations yet.</p>
                <p className="sidebar-empty-hint">
                  Click "New" to start one.
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
                        {conv.title ?? `Conversation ${conv.id.slice(0, 8)}`}
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
