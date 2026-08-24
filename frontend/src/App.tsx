import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { ChatPanel } from "@/components/ChatPanel";
import { DiscoverPanel } from "@/components/DiscoverPanel";
import { DocumentInput } from "@/components/DocumentInput";
import { JobLibrary } from "@/components/JobLibrary";
import { ResultsPanel } from "@/components/ResultsPanel";
import { Step } from "@/components/Step";
import {
  createTextDocument,
  exportSessionUrl,
  getHealth,
  getSession,
  listSessions,
  uploadDocument,
} from "@/lib/api";
import type { MatchResultItem, RankResponse } from "@/types/api";

type ResumeSource = { kind: "file"; file: File } | { kind: "text"; text: string; label: string };

export default function App() {
  const [rankData, setRankData] = useState<RankResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [resumeSource, setResumeSource] = useState<ResumeSource | null>(null);
  const [resumeId, setResumeId] = useState<string | null>(null);
  const [selectedResultId, setSelectedResultId] = useState<string | null>(null);
  const [searching, setSearching] = useState(false);

  const healthQuery = useQuery({ queryKey: ["health"], queryFn: getHealth });
  const sessionsQuery = useQuery({ queryKey: ["sessions"], queryFn: listSessions });

  // The search needs the resume persisted before it can rank anything.
  const ensureResumeId = async (): Promise<string> => {
    if (resumeId) return resumeId;
    if (!resumeSource) {
      throw new Error("Upload or paste your resume first.");
    }
    const doc =
      resumeSource.kind === "file"
        ? await uploadDocument("resume", resumeSource.file)
        : await createTextDocument({
            doc_type: "resume",
            text: resumeSource.text,
            label: resumeSource.label,
          });
    setResumeId(doc.id);
    return doc.id;
  };

  const clearResults = () => {
    setRankData(null);
    setSelectedResultId(null);
    setError(null);
  };

  const loadSession = async (sessionId: string) => {
    setError(null);
    try {
      const data = await getSession(sessionId);
      setRankData(data);
      setSelectedResultId(data.results[0]?.id ?? null);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const selected = useMemo<MatchResultItem | null>(() => {
    if (!rankData || !selectedResultId) return null;
    return rankData.results.find((r) => r.id === selectedResultId) ?? null;
  }, [rankData, selectedResultId]);

  const health = healthQuery.data;
  const results = rankData?.results ?? [];

  return (
    <div className="workspace">
      <aside className="sidebar">
        <div className="brand">
          <h1>Resume Matcher</h1>
          <span
            className="status-dot"
            data-status={health?.status ?? "unknown"}
            title={
              healthQuery.isLoading
                ? "Checking Ollama"
                : health?.status === "ok"
                  ? `Ollama: ${health.ollama_model}`
                  : "Ollama offline — ranking still works, analysis falls back to a rule-based summary"
            }
          />
        </div>

        <Step index={1} title="Your resume" done={Boolean(resumeSource)}>
          <DocumentInput
            label="Resume"
            docType="resume"
            onReady={(payload) => {
              // A new resume replaces the old one outright, and the rankings
              // it produced no longer describe the resume on screen.
              setResumeId(null);
              clearResults();
              if (payload.file) setResumeSource({ kind: "file", file: payload.file });
              if (payload.text) {
                setResumeSource({
                  kind: "text",
                  text: payload.text,
                  label: payload.label ?? "resume-paste.txt",
                });
              }
            }}
            onCleared={() => {
              setResumeId(null);
              setResumeSource(null);
              clearResults();
            }}
            disabled={searching}
          />
          <p className="muted small-hint">One resume at a time — adding another replaces it.</p>
        </Step>

        <DiscoverPanel
          ensureResumeId={ensureResumeId}
          onBusyChange={setSearching}
          onResults={(data) => {
            setRankData(data);
            setSelectedResultId(data.results[0]?.id ?? null);
            setError(null);
          }}
          onError={setError}
        />

        <section className="rail-section">
          <JobLibrary disabled={searching} />
        </section>

        <section className="rail-section">
          <h2>Recent runs</h2>
          {sessionsQuery.data?.length ? (
            <ul className="session-list">
              {sessionsQuery.data.map((session) => (
                <li key={session.id}>
                  <button
                    type="button"
                    className={`session-item ${rankData?.session_id === session.id ? "current" : ""}`}
                    onClick={() => loadSession(session.id)}
                  >
                    <span className="session-name">{session.resume_filename ?? "Session"}</span>
                    <span className="session-time">
                      {new Date(session.created_at).toLocaleString()}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted small-hint">Past runs appear here after a search.</p>
          )}
        </section>
      </aside>

      <main className="results-panel">
        <header className="panel-top">
          <div>
            <h2>Best jobs for you</h2>
            {results.length > 0 ? (
              <p className="muted small-hint">
                {results.length} ranked
                {rankData?.resume_filename ? ` against ${rankData.resume_filename}` : ""}
              </p>
            ) : null}
          </div>
          {rankData ? (
            <a className="btn secondary small" href={exportSessionUrl(rankData.session_id)}>
              Export .md
            </a>
          ) : null}
        </header>

        {error ? <p className="error banner-error">{error}</p> : null}

        {results.length === 0 ? (
          <div className="empty-state">
            <h3>No rankings yet</h3>
            <p className="muted">
              Add your resume on the left, tell us the role you want, then run
              <strong> Find &amp; rank jobs online</strong>.
            </p>
          </div>
        ) : (
          <ResultsPanel
            results={results}
            selectedId={selectedResultId}
            onSelect={setSelectedResultId}
          />
        )}
      </main>

      <aside className="detail-panel">
        <header className="panel-top">
          <div>
            <h2>Analysis</h2>
            {selected ? <p className="muted small-hint">{selected.job_filename}</p> : null}
          </div>
        </header>

        {selected?.explanation ? (
          <pre className="analysis">{selected.explanation}</pre>
        ) : selected ? (
          <p className="muted">No analysis for this job — the top few are analysed by default.</p>
        ) : (
          <p className="muted">Select a job to see how it matches.</p>
        )}

        <ChatPanel sessionId={rankData?.session_id ?? null} selected={selected} />
      </aside>
    </div>
  );
}
