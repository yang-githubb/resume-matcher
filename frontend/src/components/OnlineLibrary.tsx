import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { deleteJob, listJobs } from "@/lib/api";
import type { JobSummary } from "@/types/api";

export function OnlineLibrary() {
  const queryClient = useQueryClient();
  const jobsQuery = useQuery({
    queryKey: ["jobs", "discovered"],
    queryFn: () => listJobs("discovered"),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteJob,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["jobs"] }),
  });

  const jobs = jobsQuery.data ?? [];

  return (
    <div className="job-library">
      <div className="panel-header">
        <h3>Found online ({jobs.length})</h3>
      </div>

      {jobsQuery.isLoading ? (
        <p className="muted">Loading...</p>
      ) : jobs.length === 0 ? (
        <p className="muted">
          Nothing yet. Run <strong>Find &amp; rank jobs online</strong> and every posting
          it pulls is kept here.
        </p>
      ) : (
        <ul className="job-list scroll-list">
          {jobs.map((job: JobSummary) => {
            const meta = [job.location, job.source].filter(Boolean).join(" · ");
            return (
              <li key={job.id} className="job-row online-row">
                <div className="online-main">
                  <span className="online-title">{job.filename}</span>
                  {meta ? <span className="online-meta">{meta}</span> : null}
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
                </div>
                <button
                  type="button"
                  className="btn secondary small"
                  disabled={deleteMutation.isPending}
                  onClick={() => deleteMutation.mutate(job.id)}
                >
                  Remove
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
