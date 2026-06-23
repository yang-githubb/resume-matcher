import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { DocumentInput } from "@/components/DocumentInput";
import { createTextDocument, deleteJob, listJobs, uploadDocument } from "@/lib/api";
import type { JobSummary } from "@/types/api";

interface JobLibraryProps {
  selectedIds: string[];
  onToggle: (jobId: string) => void;
  onSelectAll: (jobIds: string[]) => void;
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

export function JobLibrary({ selectedIds, onToggle, onSelectAll, disabled }: JobLibraryProps) {
  const queryClient = useQueryClient();
  const jobsQuery = useQuery({ queryKey: ["jobs"], queryFn: listJobs });

  const addMutation = useMutation({
    mutationFn: addJob,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["jobs"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteJob,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["jobs"] }),
  });

  const jobs = jobsQuery.data ?? [];
  const allSelected = jobs.length > 0 && selectedIds.length === jobs.length;

  return (
    <div className="job-library">
      <div className="panel-header">
        <h3>Job library ({jobs.length})</h3>
        {jobs.length > 0 ? (
          <button
            type="button"
            className="btn secondary small"
            disabled={disabled}
            onClick={() => onSelectAll(allSelected ? [] : jobs.map((j) => j.id))}
          >
            {allSelected ? "Clear selection" : "Select all"}
          </button>
        ) : null}
      </div>

      <DocumentInput
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
        <p className="muted">No saved jobs yet. Paste or upload postings you want to apply to.</p>
      ) : (
        <ul className="job-list">
          {jobs.map((job: JobSummary) => (
            <li key={job.id} className="job-row">
              <label className="job-check">
                <input
                  type="checkbox"
                  checked={selectedIds.includes(job.id)}
                  disabled={disabled}
                  onChange={() => onToggle(job.id)}
                />
                <span>{job.filename}</span>
              </label>
              <button
                type="button"
                className="btn secondary small"
                disabled={disabled || deleteMutation.isPending}
                onClick={() => deleteMutation.mutate(job.id)}
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
