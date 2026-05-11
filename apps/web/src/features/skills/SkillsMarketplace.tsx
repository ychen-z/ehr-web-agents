import { useState, useEffect, useCallback } from "react";
import {
  createSkill,
  deleteSkill,
  fetchSkills,
  installSkill,
  uninstallSkill,
  updateSkill,
  type SkillResponse,
} from "@/features/skills/skillsApi";
import { useAuth } from "@/features/auth/useAuth";
import { ApiError } from "@/lib/api";

interface SkillsMarketplaceProps {
  open: boolean;
  onClose: () => void;
  onSkillChange: () => void;
}

export default function SkillsMarketplace({
  open,
  onClose,
  onSkillChange,
}: SkillsMarketplaceProps) {
  const { user } = useAuth();
  const [skills, setSkills] = useState<SkillResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toggling, setToggling] = useState<Set<string>>(new Set());
  const [toggleError, setToggleError] = useState<string | null>(null);
  const [draftName, setDraftName] = useState("");
  const [draftVisibility, setDraftVisibility] = useState<"private" | "shared">("private");
  const [editingSkillId, setEditingSkillId] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchSkills();
      setSkills(data);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Failed to load skills.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (open) {
      load();
    }
  }, [open, load]);

  const handleToggle = useCallback(
    async (skill: SkillResponse) => {
      const skillId = skill.skill_id;
      setToggling((prev) => new Set(prev).add(skillId));
      setToggleError(null);

      try {
        if (skill.installed) {
          await uninstallSkill(skillId);
        } else {
          await installSkill(skillId);
        }
        setSkills((prev) =>
          prev.map((s) =>
            s.skill_id === skillId ? { ...s, installed: !s.installed } : s,
          ),
        );
        onSkillChange();
      } catch (err) {
        setToggleError(
          err instanceof ApiError ? err.message : "Failed to update skill.",
        );
      } finally {
        setToggling((prev) => {
          const next = new Set(prev);
          next.delete(skillId);
          return next;
        });
      }
    },
    [onSkillChange],
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    },
    [onClose],
  );

  const handleCreateOrUpdate = useCallback(async () => {
    const name = draftName.trim();
    if (!name) return;
    setToggleError(null);
    const generatedSkillId = name.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");
    try {
      if (editingSkillId) {
        await updateSkill(editingSkillId, {
          name,
          visibility: user?.role === "admin" ? draftVisibility : "private",
        });
      } else {
        await createSkill({
          skill_id: generatedSkillId || `skill_${Date.now()}`,
          name,
          description: "Custom recruitment skill",
          category: "recruitment",
          mock_tool_name: "generate_jd",
          visibility: user?.role === "admin" ? draftVisibility : "private",
        });
      }
      setDraftName("");
      setDraftVisibility("private");
      setEditingSkillId(null);
      await load();
      onSkillChange();
    } catch (err) {
      setToggleError(err instanceof ApiError ? err.message : "Failed to save skill.");
    }
  }, [draftName, draftVisibility, editingSkillId, load, onSkillChange, user?.role]);

  const handleEdit = useCallback((skill: SkillResponse) => {
    setEditingSkillId(skill.skill_id);
    setDraftName(skill.name);
    setDraftVisibility(skill.visibility);
  }, []);

  const handleDelete = useCallback(async (skill: SkillResponse) => {
    setToggleError(null);
    try {
      await deleteSkill(skill.skill_id);
      await load();
      onSkillChange();
    } catch (err) {
      setToggleError(err instanceof ApiError ? err.message : "Failed to delete skill.");
    }
  }, [load, onSkillChange]);

  if (!open) return null;

  return (
    <div
      className="marketplace-overlay"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Skills Marketplace"
    >
      <div
        className="marketplace-modal"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={handleKeyDown}
        tabIndex={-1}
      >
        <div className="marketplace-header">
          <h2 className="marketplace-title">Skills Marketplace</h2>
          <button
            type="button"
            className="marketplace-close-btn"
            onClick={onClose}
            aria-label="Close marketplace"
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 16 16"
              fill="none"
              aria-hidden="true"
            >
              <path
                d="M4 4L12 12M12 4L4 12"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
              />
            </svg>
          </button>
        </div>

        <div className="marketplace-body">
          {loading ? (
            <div className="marketplace-loading" role="status">
              <span className="marketplace-spinner" />
              Loading skills...
            </div>
          ) : error ? (
            <div className="marketplace-error" role="alert">
              <p>{error}</p>
              <button
                type="button"
                className="marketplace-retry-btn"
                onClick={load}
              >
                Retry
              </button>
            </div>
          ) : (
            <>
              {toggleError && (
                <div className="marketplace-toast" role="alert">
                  {toggleError}
                </div>
              )}
              <div className="marketplace-editor">
                <div>
                  <h3 className="marketplace-editor-title">
                    {editingSkillId ? "Edit Skill" : "Create Skill"}
                  </h3>
                  <p className="marketplace-editor-help">
                    Personal skills stay private. Admin shared skills are visible to everyone.
                  </p>
                </div>
                <label className="marketplace-editor-field">
                  <span>Skill name</span>
                  <input
                    value={draftName}
                    onChange={(e) => setDraftName(e.target.value)}
                    placeholder="e.g. Executive JD Writer"
                  />
                </label>
                {user?.role === "admin" && (
                  <label className="marketplace-editor-field">
                    <span>Visibility</span>
                    <select
                      value={draftVisibility}
                      onChange={(e) => setDraftVisibility(e.target.value as "private" | "shared")}
                    >
                      <option value="private">Private</option>
                      <option value="shared">Shared</option>
                    </select>
                  </label>
                )}
                <div className="marketplace-editor-actions">
                  {editingSkillId && (
                    <button
                      type="button"
                      className="marketplace-secondary-btn"
                      onClick={() => {
                        setEditingSkillId(null);
                        setDraftName("");
                        setDraftVisibility("private");
                      }}
                    >
                      Cancel
                    </button>
                  )}
                  <button
                    type="button"
                    className="marketplace-create-btn"
                    onClick={handleCreateOrUpdate}
                    disabled={!draftName.trim()}
                  >
                    {editingSkillId ? "Save Skill" : "Create Skill"}
                  </button>
                </div>
              </div>
              <div className="marketplace-grid">
                {skills.map((skill) => (
                  <div
                    key={skill.skill_id}
                    className={`marketplace-card ${skill.installed ? "marketplace-card--installed" : ""}`}
                  >
                    <div className="marketplace-card-icon" aria-hidden="true">
                      <svg
                        width="24"
                        height="24"
                        viewBox="0 0 24 24"
                        fill="none"
                      >
                        <rect
                          x="4"
                          y="4"
                          width="16"
                          height="16"
                          rx="3"
                          stroke="currentColor"
                          strokeWidth="1.5"
                        />
                        <path
                          d="M8 12L11 15L16 9"
                          stroke="currentColor"
                          strokeWidth="1.5"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                    </div>
                    <h3 className="marketplace-card-name">{skill.name}</h3>
                    <p className="marketplace-card-desc">
                      {skill.description ?? "No description available."}
                    </p>
                    {skill.category && (
                      <span className="marketplace-card-category">
                        {skill.category}
                      </span>
                    )}
                    <div className="marketplace-card-tags">
                      <span className="marketplace-card-tag">{skill.source}</span>
                      <span className="marketplace-card-tag">{skill.visibility}</span>
                    </div>
                    <button
                      type="button"
                      className={`marketplace-card-btn ${skill.installed ? "marketplace-card-btn--remove" : "marketplace-card-btn--install"}`}
                      onClick={() => handleToggle(skill)}
                      disabled={toggling.has(skill.skill_id)}
                    >
                      {toggling.has(skill.skill_id)
                        ? "Updating..."
                        : skill.installed
                          ? "Uninstall"
                          : "Install"}
                    </button>
                    {skill.source === "user" && (skill.owner_user_id === user?.id || user?.role === "admin") && (
                      <div className="marketplace-card-actions">
                        <button type="button" onClick={() => handleEdit(skill)}>Edit</button>
                        <button type="button" onClick={() => handleDelete(skill)}>Delete</button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
