import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { Step } from "@/components/Step";
import { discoverAndMatch } from "@/lib/api";
import type { SearchProgress } from "@/lib/api";
import type { DiscoverResponse } from "@/types/api";

const COUNTRIES = [
  { code: "my", label: "Malaysia" },
  { code: "sg", label: "Singapore" },
  { code: "id", label: "Indonesia" },
  { code: "th", label: "Thailand" },
  { code: "ph", label: "Philippines" },
  { code: "vn", label: "Vietnam" },
  { code: "hk", label: "Hong Kong" },
  { code: "jp", label: "Japan" },
  { code: "au", label: "Australia" },
  { code: "nz", label: "New Zealand" },
  { code: "in", label: "India" },
  { code: "gb", label: "United Kingdom" },
  { code: "us", label: "United States" },
  { code: "ca", label: "Canada" },
  { code: "de", label: "Germany" },
  { code: "nl", label: "Netherlands" },
  { code: "fr", label: "France" },
];

const SENIORITY = ["", "junior", "mid-level", "senior", "lead", "principal"];

interface DiscoverPanelProps {
  ensureResumeId: () => Promise<string>;
  onResults: (data: DiscoverResponse) => void;
  onError: (message: string | null) => void;
  onBusyChange?: (busy: boolean) => void;
}

export function DiscoverPanel({
  ensureResumeId,
  onResults,
  onError,
  onBusyChange,
}: DiscoverPanelProps) {
  const [keywords, setKeywords] = useState("");
  const [location, setLocation] = useState("");
  const [seniority, setSeniority] = useState("");
  const [remoteOnly, setRemoteOnly] = useState(true);
  const [country, setCountry] = useState("my");
  const [limit, setLimit] = useState(25);
  const [minScore, setMinScore] = useState(0);
  const [report, setReport] = useState<DiscoverResponse | null>(null);
  const [progress, setProgress] = useState<SearchProgress | null>(null);
  // The settings behind Refine are read far less often than the role, so they
  // stay folded away with their values summarised instead.
  const [refineOpen, setRefineOpen] = useState(false);

  const queryClient = useQueryClient();

  const discoverMutation = useMutation({
    onMutate: () => {
      onBusyChange?.(true);
      setProgress({ progress: 0, label: "Starting..." });
    },
    onSettled: () => {
      onBusyChange?.(false);
      setProgress(null);
    },
    mutationFn: async () => {
      if (keywords.trim().length < 2) {
        throw new Error("Enter a role or some keywords to search for.");
      }
      const resumeId = await ensureResumeId();
      return discoverAndMatch(
        {
          resume_id: resumeId,
          preferences: {
            keywords: keywords.trim(),
            location: location.trim() || null,
            seniority: seniority || null,
            remote_only: remoteOnly,
            country,
            limit,
          },
          explain: true,
          explain_top: 3,
          min_score: minScore,
        },
        setProgress,
      );
    },
    onSuccess: (data) => {
      setReport(data);
      onResults(data);
      onError(null);
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
    onError: (err: Error) => {
      setReport(null);
      onError(err.message);
    },
  });

  const pending = discoverMutation.isPending;
  const hasRole = keywords.trim().length >= 2;

  const summary = [
    COUNTRIES.find((c) => c.code === country)?.label,
    location.trim() || null,
    remoteOnly ? "Remote" : null,
    seniority || "Any level",
    `${limit} jobs`,
    minScore > 0 ? `min ${minScore}%` : null,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <>
      <Step index={2} title="What you are looking for" done={hasRole}>
        <input
          className="role-input"
          type="text"
          value={keywords}
          placeholder="e.g. python backend engineer"
          onChange={(e) => setKeywords(e.target.value)}
          disabled={pending}
        />

        <div className="refine-row">
          <span className="refine-summary">{summary}</span>
          <button
            type="button"
            className="linkish refine-toggle"
            disabled={pending}
            onClick={() => setRefineOpen((open) => !open)}
          >
            {refineOpen ? "Done" : "Refine"}
          </button>
        </div>

        {refineOpen ? (
          <div className="refine-fields">
            <label className="field">
              <span>Experience level</span>
              <select
                value={seniority}
                onChange={(e) => setSeniority(e.target.value)}
                disabled={pending}
              >
                {SENIORITY.map((level) => (
                  <option key={level || "any"} value={level}>
                    {level || "Any"}
                  </option>
                ))}
              </select>
            </label>

            <label className="field">
              <span>Country</span>
              <select value={country} onChange={(e) => setCountry(e.target.value)} disabled={pending}>
                {COUNTRIES.map((c) => (
                  <option key={c.code} value={c.code}>
                    {c.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="field field-wide">
              <span>City / area</span>
              <input
                type="text"
                value={location}
                placeholder="e.g. Kuala Lumpur"
                onChange={(e) => setLocation(e.target.value)}
                disabled={pending}
              />
            </label>

            <label className="field field-slider field-wide">
              <span>
                Jobs to pull
                <span className="field-value">{limit}</span>
              </span>
              <input
                type="range"
                min={5}
                max={50}
                step={5}
                value={limit}
                onChange={(e) => setLimit(Number(e.target.value))}
                disabled={pending}
              />
            </label>

            <label className="field field-slider field-wide">
              <span>
                Minimum match
                <span className="field-value">{minScore > 0 ? `${minScore}%` : "Any"}</span>
              </span>
              <input
                type="range"
                min={0}
                max={80}
                step={5}
                value={minScore}
                onChange={(e) => setMinScore(Number(e.target.value))}
                disabled={pending}
              />
            </label>

            <label className="checkbox-field">
              <input
                type="checkbox"
                checked={remoteOnly}
                onChange={(e) => setRemoteOnly(e.target.checked)}
                disabled={pending}
              />
              <span>Remote only</span>
            </label>
          </div>
        ) : null}
      </Step>

      <Step index={3} title="Search and rank" last>
        <button
          type="button"
          className="btn primary block"
          onClick={() => discoverMutation.mutate()}
          disabled={pending}
        >
          {pending ? "Searching job boards..." : "Find & rank jobs"}
        </button>

        {pending && progress ? (
          <div className="search-progress">
            <div
              className="progress-track"
              role="progressbar"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={Math.round(progress.progress * 100)}
              aria-label="Search progress"
            >
              <div
                className="progress-fill"
                style={{ width: `${Math.max(2, Math.round(progress.progress * 100))}%` }}
              />
            </div>
            <p className="muted small-hint">{progress.label}</p>
          </div>
        ) : null}

        {!pending && report ? (
          <p className="muted small-hint">
            Pulled {report.fetched_count} jobs, ranked {report.ranked_count}.
          </p>
        ) : null}
      </Step>
    </>
  );
}
