import { useState, useEffect, useCallback } from "react";
import {
  fetchSkills,
  installSkill,
  uninstallSkill,
  type SkillResponse,
} from "@/features/skills/skillsApi";
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
  const [skills, setSkills] = useState<SkillResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toggling, setToggling] = useState<Set<string>>(new Set());
  const [toggleError, setToggleError] = useState<string | null>(null);

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
