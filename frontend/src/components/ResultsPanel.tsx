import type { MatchResultItem } from "@/types/api";

interface ResultsPanelProps {
  results: MatchResultItem[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  variant: "resumes_for_job" | "jobs_for_resume";
}

export function ResultsPanel({ results, selectedId, onSelect, variant }: ResultsPanelProps) {
  if (results.length === 0) {
    return (
      <p className="muted">
        {variant === "jobs_for_resume"
          ? "Add jobs to your library and rank to see best fits."
          : "Upload files and run match to see rankings."}
      </p>
    );
  }

  return (
    <div className="results-list">
      {results.map((item, index) => {
        const label =
          variant === "jobs_for_resume"
            ? (item.job_filename ?? "Job")
            : (item.resume_filename ?? "Resume");

        const meta = [item.job_location, item.job_source].filter(Boolean).join(" · ");

        return (
          <div
            key={item.id}
            className={`result-card ${selectedId === item.id ? "selected" : ""}`}
          >
            <button type="button" className="result-main" onClick={() => onSelect(item.id)}>
              <div className="result-header">
                <span className="rank">#{index + 1}</span>
                <strong>{label}</strong>
                <span className="score">{item.score}%</span>
              </div>
              {meta ? <div className="result-meta">{meta}</div> : null}
              <div className="score-breakdown">
                <span>Semantic {item.semantic_score}%</span>
                <span>Keyword {item.keyword_score}%</span>
              </div>
              <p className="chip-row">
                {item.breakdown.matched_skills.slice(0, 5).map((skill) => (
                  <span key={skill} className="chip good">
                    {skill}
                  </span>
                ))}
                {item.breakdown.missing_skills.slice(0, 3).map((skill) => (
                  <span key={skill} className="chip warn">
                    -{skill}
                  </span>
                ))}
              </p>
            </button>
            {item.job_url ? (
              <a
                className="apply-link"
                href={item.job_url}
                target="_blank"
                rel="noopener noreferrer"
              >
                View & apply →
              </a>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
