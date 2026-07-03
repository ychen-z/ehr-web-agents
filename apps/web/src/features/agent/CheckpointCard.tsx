import { useState } from "react";
import { api } from "../../lib/api";

interface CheckpointOption {
  label: string;
  value: string;
  description?: string;
}

interface CheckpointCardProps {
  runId: string;
  prompt: string;
  options: CheckpointOption[];
  onResumed: () => void;
}

export default function CheckpointCard({
  runId,
  prompt,
  options,
  onResumed,
}: CheckpointCardProps) {
  const [selected, setSelected] = useState<string | null>(null);
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleResume = async () => {
    if (!selected) return;
    setSubmitting(true);
    setError(null);
    try {
      await api.post(`/api/agent/runs/${runId}/resume`, {
        choice: selected,
        comment: comment || undefined,
      });
      onResumed();
    } catch (err) {
      setError(err instanceof Error ? err.message : "恢复执行失败");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="checkpoint-card">
      <div className="checkpoint-header">
        <span className="checkpoint-icon">&#128276;</span>
        <span className="checkpoint-title">需要您的确认</span>
      </div>
      <p className="checkpoint-prompt">{prompt}</p>
      <div className="checkpoint-options">
        {options.map((opt) => (
          <button
            key={opt.value}
            className={`checkpoint-option ${selected === opt.value ? "selected" : ""}`}
            onClick={() => setSelected(opt.value)}
            disabled={submitting}
          >
            <span className="option-label">{opt.label}</span>
            {opt.description && (
              <span className="option-desc">{opt.description}</span>
            )}
          </button>
        ))}
      </div>
      <div className="checkpoint-comment">
        <input
          type="text"
          placeholder="备注（可选）"
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          disabled={submitting}
        />
      </div>
      {error && <p className="checkpoint-error">{error}</p>}
      <button
        className="checkpoint-submit"
        onClick={handleResume}
        disabled={!selected || submitting}
      >
        {submitting ? "提交中..." : "确认并继续"}
      </button>
    </div>
  );
}
