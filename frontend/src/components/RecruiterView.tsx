import { useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { ChatPanel } from "@/components/ChatPanel";
import { DocumentInput } from "@/components/DocumentInput";
import { ResultsPanel } from "@/components/ResultsPanel";
import {
  createTextDocument,
  exportSessionUrl,
  getSession,
  rankDocuments,
  uploadDocument,
} from "@/lib/api";
import type { MatchResultItem, RankResponse } from "@/types/api";

type JobSource = { kind: "file"; file: File } | { kind: "text"; text: string; label: string };
type ResumeSource = { kind: "file"; file: File } | { kind: "text"; text: string; label: string };

async function resolveDocument(
  docType: "resume" | "job",
  source: JobSource | ResumeSource,
) {
  if (source.kind === "file") {
    return uploadDocument(docType, source.file);
  }
  return createTextDocument({
    doc_type: docType,
    text: source.text,
    label: source.label,
  });
}

interface RecruiterViewProps {
  rankData: RankResponse | null;
  onRankData: (data: RankResponse) => void;
  onError: (message: string | null) => void;
}

export function RecruiterView({ rankData, onRankData, onError }: RecruiterViewProps) {
  const [jobSource, setJobSource] = useState<JobSource | null>(null);
  const [resumeSources, setResumeSources] = useState<ResumeSource[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const matchMutation = useMutation({
    mutationFn: async () => {
      if (!jobSource || resumeSources.length === 0) {
        throw new Error("Provide a job description and at least one resume.");
      }
      const job = await resolveDocument("job", jobSource);
      const resumes = await Promise.all(
        resumeSources.map((source) => resolveDocument("resume", source)),
      );
      return rankDocuments({
        mode: "recruiter",
        job_id: job.id,
        resume_ids: resumes.map((r) => r.id),
        explain: true,
      });
    },
    onSuccess: (data) => {
      onRankData(data);
      setSelectedId(data.results[0]?.id ?? null);
      onError(null);
    },
    onError: (err: Error) => onError(err.message),
  });

  const selected = useMemo<MatchResultItem | null>(() => {
    if (!rankData || !selectedId) return null;
    return rankData.results.find((r) => r.id === selectedId) ?? null;
  }, [rankData, selectedId]);

  const handleResumeReady = (payload: { file?: File; text?: string; label?: string }) => {
    if (payload.file) {
      setResumeSources((prev) =>
        [...prev, { kind: "file" as const, file: payload.file! }].slice(-2),
      );
      return;
    }
    if (payload.text) {
      setResumeSources((prev) =>
        [
          ...prev,
          {
            kind: "text" as const,
            text: payload.text!,
            label: payload.label ?? "resume-paste.txt",
          },
        ].slice(-2),
      );
    }
  };

  return (
    <>
      <section className="grid-2">
        <div className="panel">
          <h2>Input</h2>
          <DocumentInput
            label="Job description"
            docType="job"
            onReady={(payload) => {
              if (payload.file) setJobSource({ kind: "file", file: payload.file });
              if (payload.text) {
                setJobSource({
                  kind: "text",
                  text: payload.text,
                  label: payload.label ?? "job-paste.txt",
                });
              }
            }}
            disabled={matchMutation.isPending}
          />
          <DocumentInput
            label="Resume 1"
            docType="resume"
            onReady={handleResumeReady}
            disabled={matchMutation.isPending}
          />
          <DocumentInput
            label="Resume 2 (optional)"
            docType="resume"
            onReady={handleResumeReady}
            disabled={matchMutation.isPending}
          />
          {resumeSources.length > 0 ? (
            <p className="muted">{resumeSources.length} resume(s) ready</p>
          ) : null}
          <button
            type="button"
            className="btn primary"
            disabled={matchMutation.isPending}
            onClick={() => matchMutation.mutate()}
          >
            {matchMutation.isPending ? "Matching..." : "Rank candidates"}
          </button>
        </div>

        <div className="panel placeholder-panel">
          <h2>Recruiter mode</h2>
          <p className="muted">
            Upload one job description and up to two resumes. The best-matching candidate is ranked
            first.
          </p>
        </div>
      </section>

      <section className="grid-2">
        <div className="panel">
          <div className="panel-header">
            <h2>Rankings</h2>
            {rankData ? (
              <a className="btn secondary small" href={exportSessionUrl(rankData.session_id)}>
                Export .md
              </a>
            ) : null}
          </div>
          <ResultsPanel
            results={rankData?.results ?? []}
            selectedId={selectedId}
            onSelect={setSelectedId}
            variant="resumes_for_job"
          />
        </div>

        <div className="panel">
          <h2>Analysis</h2>
          {selected?.explanation ? (
            <pre className="analysis">{selected.explanation}</pre>
          ) : (
            <p className="muted">Select a result to view the generated analysis.</p>
          )}
          <ChatPanel
            sessionId={rankData?.session_id ?? null}
            selected={selected}
            variant="resumes_for_job"
          />
        </div>
      </section>
    </>
  );
}

export async function loadRecruiterSession(
  sessionId: string,
  onRankData: (data: RankResponse) => void,
  onError: (message: string | null) => void,
) {
  onError(null);
  try {
    const data = await getSession(sessionId);
    onRankData(data);
  } catch (err) {
    onError((err as Error).message);
  }
}
