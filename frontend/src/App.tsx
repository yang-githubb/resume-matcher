import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { RecruiterView } from "@/components/RecruiterView";
import { SeekerView } from "@/components/SeekerView";
import { getHealth, getSession, listSessions } from "@/lib/api";
import type { RankResponse } from "@/types/api";

type Mode = "seeker" | "recruiter";

function sessionLabel(session: {
  mode: string;
  variant?: string;
  job_filename?: string | null;
  resume_filename?: string | null;
}) {
  if (session.resume_filename && !session.job_filename) {
    return `${session.resume_filename} → jobs`;
  }
  return session.job_filename ?? "Session";
}

export default function App() {
  const [mode, setMode] = useState<Mode>("seeker");
  const [rankData, setRankData] = useState<RankResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const healthQuery = useQuery({ queryKey: ["health"], queryFn: getHealth });
  const sessionsQuery = useQuery({ queryKey: ["sessions"], queryFn: listSessions });

  const loadSession = async (sessionId: string) => {
    setError(null);
    try {
      const data = await getSession(sessionId);
      setRankData(data);
      setMode(data.variant === "jobs_for_resume" ? "seeker" : data.mode);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <div className="app-shell">
      <header className="hero">
        <div>
          <p className="eyebrow">Local-first · Hybrid scoring · SQLite</p>
          <h1>Resume Matcher</h1>
          <p className="lede">
            Job seeker: upload your resume once, build a job library, and see which roles fit best.
            Recruiter: rank candidates against one job.
          </p>
        </div>
        <div className="health-pill" data-status={healthQuery.data?.status ?? "unknown"}>
          {healthQuery.isLoading
            ? "Checking Ollama..."
            : healthQuery.data?.status === "ok"
              ? `Ollama: ${healthQuery.data.ollama_model}`
              : "Ollama offline — ranking works, rule-based fallback for analysis"}
        </div>
      </header>

      <section className="mode-toggle">
        <button
          type="button"
          className={mode === "seeker" ? "btn active" : "btn secondary"}
          onClick={() => {
            setMode("seeker");
            setRankData(null);
          }}
        >
          Job seeker
        </button>
        <button
          type="button"
          className={mode === "recruiter" ? "btn active" : "btn secondary"}
          onClick={() => {
            setMode("recruiter");
            setRankData(null);
          }}
        >
          Recruiter
        </button>
      </section>

      {error ? <p className="error banner-error">{error}</p> : null}

      {mode === "seeker" ? (
        <SeekerView rankData={rankData} onRankData={setRankData} onError={setError} />
      ) : (
        <RecruiterView rankData={rankData} onRankData={setRankData} onError={setError} />
      )}

      <section className="panel sessions-panel">
        <h2>Saved sessions</h2>
        {sessionsQuery.data?.length ? (
          <ul className="session-list">
            {sessionsQuery.data.map((session) => (
              <li key={session.id}>
                <button type="button" className="linkish" onClick={() => loadSession(session.id)}>
                  {sessionLabel(session)} · {session.mode} ·{" "}
                  {new Date(session.created_at).toLocaleString()}
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted">Past matches appear here after you rank.</p>
        )}
      </section>
    </div>
  );
}
