import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { ChatPanel } from "@/components/ChatPanel";
import { DocumentInput } from "@/components/DocumentInput";
import { JobLibrary } from "@/components/JobLibrary";
import { ResultsPanel } from "@/components/ResultsPanel";
import {
  createTextDocument,
  exportSessionUrl,
  getSession,
  listJobs,
  rankJobsForResume,
  uploadDocument,
} from "@/lib/api";
import type { MatchResultItem, RankResponse } from "@/types/api";

type ResumeSource = { kind: "file"; file: File } | { kind: "text"; text: string; label: string };

interface SeekerViewProps {
  rankData: RankResponse | null;
  onRankData: (data: RankResponse) => void;
  onError: (message: string | null) => void;
}

export function SeekerView({ rankData, onRankData, onError }: SeekerViewProps) {
  const [resumeSource, setResumeSource] = useState<ResumeSource | null>(null);
  const [resumeId, setResumeId] = useState<string | null>(null);
  const [selectedJobIds, setSelectedJobIds] = useState<string[]>([]);
  const [selectedResultId, setSelectedResultId] = useState<string | null>(null);

  const jobsQuery = useQuery({ queryKey: ["jobs"], queryFn: listJobs });

  const matchMutation = useMutation({
    mutationFn: async () => {
      let id = resumeId;
      if (!id && resumeSource) {
        const doc =
          resumeSource.kind === "file"
            ? await uploadDocument("resume", resumeSource.file)
            : await createTextDocument({
                doc_type: "resume",
                text: resumeSource.text,
                label: resumeSource.label,
              });
        id = doc.id;
        setResumeId(id);
      }
      if (!id) {
        throw new Error("Upload or paste your resume first.");
      }

      const jobIds =
        selectedJobIds.length > 0 ? selectedJobIds : jobsQuery.data?.map((j) => j.id);

      if (!jobIds?.length) {
        throw new Error("Add at least one job to your library.");
      }

      return rankJobsForResume({
        resume_id: id,
        job_ids: jobIds,
        explain: true,
        explain_top: 5,
      });
    },
    onSuccess: (data) => {
      onRankData(data);
      setSelectedResultId(data.results[0]?.id ?? null);
      onError(null);
    },
    onError: (err: Error) => onError(err.message),
  });

  const selected = useMemo<MatchResultItem | null>(() => {
    if (!rankData || !selectedResultId) return null;
    return rankData.results.find((r) => r.id === selectedResultId) ?? null;
  }, [rankData, selectedResultId]);

  const toggleJob = (jobId: string) => {
    setSelectedJobIds((prev) =>
      prev.includes(jobId) ? prev.filter((id) => id !== jobId) : [...prev, jobId],
    );
  };

  return (
    <>
      <section className="grid-2">
        <div className="panel">
          <h2>Your resume</h2>
          <DocumentInput
            label="Resume"
            docType="resume"
            onReady={(payload) => {
              setResumeId(null);
              if (payload.file) setResumeSource({ kind: "file", file: payload.file });
              if (payload.text) {
                setResumeSource({
                  kind: "text",
                  text: payload.text,
                  label: payload.label ?? "resume-paste.txt",
                });
              }
            }}
            disabled={matchMutation.isPending}
          />
          {resumeId ? <p className="muted">Resume loaded and ready to reuse.</p> : null}
          <button
            type="button"
            className="btn primary"
            disabled={matchMutation.isPending}
            onClick={() => matchMutation.mutate()}
          >
            {matchMutation.isPending ? "Matching..." : "Rank jobs for my resume"}
          </button>
          <p className="muted small-hint">
            Matches against selected jobs, or all jobs in the library if none selected.
          </p>
        </div>

        <div className="panel">
          <JobLibrary
            selectedIds={selectedJobIds}
            onToggle={toggleJob}
            onSelectAll={setSelectedJobIds}
            disabled={matchMutation.isPending}
          />
        </div>
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
            variant="jobs_for_resume"
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
          <ChatPanel
            sessionId={rankData?.session_id ?? null}
            selected={selected}
            variant="jobs_for_resume"
          />
        </div>
      </section>
    </>
  );
}

export function useLoadSeekerSession(
  onRankData: (data: RankResponse) => void,
  onError: (message: string | null) => void,
) {
  return async (sessionId: string) => {
    onError(null);
    try {
      const data = await getSession(sessionId);
      onRankData(data);
    } catch (err) {
      onError((err as Error).message);
    }
  };
}
