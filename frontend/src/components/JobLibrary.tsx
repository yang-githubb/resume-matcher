import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { DocumentInput } from "@/components/DocumentInput";
import { createTextDocument, deleteJob, listJobs, uploadDocument } from "@/lib/api";
import type { JobSummary } from "@/types/api";

interface JobLibraryProps {
  disabled?: boolean;
}

async function addJob(payload: { file?: File; text?: string; label?: string }) {
  if (payload.file) {
    return uploadDocument("job", payload.file);
  }
  if (payload.text) {
    return createTextDocument({
      doc_type: "job",
      text: payload.text,
      label: payload.label ?? "job-paste.txt",
    });
  }
  throw new Error("No job content provided.");
}

export function JobLibrary({ disabled }: JobLibraryProps) {
  const queryClient = useQueryClient();
  // Remounting after each add clears the picker, so the next posting starts blank.
  const [inputKey, setInputKey] = useState(0);
  // "all" merges what you added by hand with what a search pulled in, so
  // there is one library and one selection pool instead of two disjoint ones.
  const jobsQuery = useQuery({ queryKey: ["jobs", "all"], queryFn: () => listJobs("all") });

  const addMutation = useMutation({
    mutationFn: addJob,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      setInputKey((k) => k + 1);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteJob,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["jobs"] }),
  });

  const jobs = jobsQuery.data ?? [];
  const onlineCount = jobs.filter((j) => j.origin === "discovered").length;
  const manualCount = jobs.length - onlineCount;

  return (
    <div className="job-library">
      <div className="panel-header">
        <div>
          <h2>Job library ({jobs.length})</h2>
          {jobs.length > 0 ? (
            <p className="muted small-hint">
              {manualCount} added by hand, {onlineCount} found online. Jobs you add by hand
              are ranked alongside every search.
            </p>
          ) : null}
        </div>
      </div>

      <DocumentInput
        key={inputKey}
        label="Add job to library"
        docType="job"
        onReady={(payload) => addMutation.mutate(payload)}
        disabled={disabled || addMutation.isPending}
      />
      {addMutation.isError ? (
        <p className="error">{(addMutation.error as Error).message}</p>
      ) : null}

      {jobsQuery.isLoading ? (
        <p className="muted">Loading jobs...</p>
      ) : jobs.length === 0 ? (
        <p className="muted">
          No jobs yet. Paste or upload a posting, or use Find jobs online to pull some in.
        </p>
      ) : (
        <ul className="job-list scroll-list">
          {jobs.map((job: JobSummary) => {
            const meta = [job.company, job.location].filter(Boolean).join(" · ");
            return (
              <li key={job.id} className="job-row">
                <div className="job-info">
                  <div className="job-title-row">
                    <span className="job-title">{job.filename}</span>
                    <span className={`badge ${job.origin === "manual" ? "badge-manual" : "badge-online"}`}>
                      {job.origin === "manual" ? "Manual" : (job.source ?? "Online")}
                    </span>
                  </div>
                  {meta ? <span className="job-meta">{meta}</span> : null}
                </div>
                <div className="job-actions">
                  {job.url ? (
                    <a
                      className="apply-link"
                      href={job.url}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      View &amp; apply →
                    </a>
                  ) : null}
                  <button
                    type="button"
                    className="btn secondary small"
                    disabled={disabled || deleteMutation.isPending}
                    onClick={() => deleteMutation.mutate(job.id)}
                  >
                    Remove
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
