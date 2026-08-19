import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { SeekerView } from "@/components/SeekerView";
import { getHealth, getSession, listSessions } from "@/lib/api";
import type { RankResponse } from "@/types/api";

export default function App() {
  const [rankData, setRankData] = useState<RankResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const healthQuery = useQuery({ queryKey: ["health"], queryFn: getHealth });
  const sessionsQuery = useQuery({ queryKey: ["sessions"], queryFn: listSessions });

  const loadSession = async (sessionId: string) => {
    setError(null);
    try {
      setRankData(await getSession(sessionId));
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
            Upload your resume once, build a job library or pull postings from job boards, and
            see which roles fit you best.
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

      {error ? <p className="error banner-error">{error}</p> : null}

      <SeekerView rankData={rankData} onRankData={setRankData} onError={setError} />

      <section className="panel sessions-panel">
        <h2>Saved sessions</h2>
        {sessionsQuery.data?.length ? (
          <ul className="session-list">
            {sessionsQuery.data.map((session) => (
              <li key={session.id}>
                <button type="button" className="linkish" onClick={() => loadSession(session.id)}>
                  {session.resume_filename ?? "Session"} → jobs ·{" "}
                  {new Date(session.created_at).toLocaleString()}
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted">Past matches appear here after you rank.</p>
        )}
        <p className="muted small-hint">Only the 5 most recent runs are kept.</p>
      </section>
    </div>
  );
}
