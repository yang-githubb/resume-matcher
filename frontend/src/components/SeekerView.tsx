import { useMemo, useState } from "react";

import { ChatPanel } from "@/components/ChatPanel";
import { DiscoverPanel } from "@/components/DiscoverPanel";
import { DocumentInput } from "@/components/DocumentInput";
import { JobLibrary } from "@/components/JobLibrary";
import { ResultsPanel } from "@/components/ResultsPanel";
import { createTextDocument, exportSessionUrl, uploadDocument } from "@/lib/api";
import type { MatchResultItem, RankResponse } from "@/types/api";

type ResumeSource = { kind: "file"; file: File } | { kind: "text"; text: string; label: string };

interface SeekerViewProps {
  rankData: RankResponse | null;
  onRankData: (data: RankResponse | null) => void;
  onError: (message: string | null) => void;
}

export function SeekerView({ rankData, onRankData, onError }: SeekerViewProps) {
  const [resumeSource, setResumeSource] = useState<ResumeSource | null>(null);
  const [resumeId, setResumeId] = useState<string | null>(null);
  const [selectedResultId, setSelectedResultId] = useState<string | null>(null);
  const [searching, setSearching] = useState(false);

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

  const selected = useMemo<MatchResultItem | null>(() => {
    if (!rankData || !selectedResultId) return null;
    return rankData.results.find((r) => r.id === selectedResultId) ?? null;
  }, [rankData, selectedResultId]);

  return (
    <>
      <section className="grid-2">
        <div className="panel">
          <h2>Your resume</h2>
          <DocumentInput
            label="Resume"
            docType="resume"
            onReady={(payload) => {
              // A new resume replaces the old one outright, and the rankings
              // it produced no longer describe the resume on screen.
              setResumeId(null);
              onRankData(null);
              setSelectedResultId(null);
              onError(null);
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
              onRankData(null);
              setSelectedResultId(null);
              onError(null);
            }}
            disabled={searching}
          />
          <p className="muted small-hint">
            One resume at a time — adding another replaces it. Then run the search on the
            right to see which roles fit you best.
          </p>
        </div>

        <div className="panel">
          <h2>Find jobs online</h2>
          <DiscoverPanel
            ensureResumeId={ensureResumeId}
            onBusyChange={setSearching}
            onResults={(data) => {
              onRankData(data);
              setSelectedResultId(data.results[0]?.id ?? null);
            }}
            onError={onError}
          />
        </div>
      </section>

      <section className="panel">
        <JobLibrary disabled={searching} />
      </section>

      <section className="grid-2">
        <div className="panel">
          <div className="panel-header">
            <h2>Best jobs for you</h2>
            {rankData ? (
              <a className="btn secondary small" href={exportSessionUrl(rankData.session_id)}>
                Export .md
              </a>
            ) : null}
          </div>
          <ResultsPanel
            results={rankData?.results ?? []}
            selectedId={selectedResultId}
            onSelect={setSelectedResultId}
          />
        </div>

        <div className="panel">
          <h2>Analysis</h2>
          {selected?.explanation ? (
            <pre className="analysis">{selected.explanation}</pre>
          ) : selected ? (
            <p className="muted">No analysis yet for this job (top 5 are analyzed by default).</p>
          ) : (
            <p className="muted">Select a job from the rankings to view analysis.</p>
          )}
          <ChatPanel sessionId={rankData?.session_id ?? null} selected={selected} />
        </div>
      </section>
    </>
  );
}
