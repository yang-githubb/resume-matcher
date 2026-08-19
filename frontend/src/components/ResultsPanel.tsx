import type { MatchResultItem } from "@/types/api";

interface ResultsPanelProps {
  results: MatchResultItem[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export function ResultsPanel({ results, selectedId, onSelect }: ResultsPanelProps) {
  if (results.length === 0) {
    return <p className="muted">Add jobs to your library and rank to see best fits.</p>;
  }

  return (
    <div className="results-list">
      {results.map((item, index) => {
        const meta = [item.job_location, item.job_source].filter(Boolean).join(" · ");

        return (
          <div
            key={item.id}
            className={`result-card ${selectedId === item.id ? "selected" : ""}`}
          >
            <button type="button" className="result-main" onClick={() => onSelect(item.id)}>
              <div className="result-header">
                <span className="rank">#{index + 1}</span>
                <strong>{item.job_filename ?? "Job"}</strong>
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
                View &amp; apply →
              </a>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
