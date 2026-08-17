import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { discoverAndMatch, listSources } from "@/lib/api";
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
}

export function DiscoverPanel({ ensureResumeId, onResults, onError }: DiscoverPanelProps) {
  const [keywords, setKeywords] = useState("");
  const [location, setLocation] = useState("");
  const [seniority, setSeniority] = useState("");
  const [remoteOnly, setRemoteOnly] = useState(true);
  const [country, setCountry] = useState("my");
  const [limit, setLimit] = useState(25);
  const [minScore, setMinScore] = useState(0);
  const [report, setReport] = useState<DiscoverResponse | null>(null);

  const sourcesQuery = useQuery({ queryKey: ["sources"], queryFn: listSources });

  const discoverMutation = useMutation({
    mutationFn: async () => {
      if (keywords.trim().length < 2) {
        throw new Error("Enter a role or some keywords to search for.");
      }
      const resumeId = await ensureResumeId();
      return discoverAndMatch({
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
      });
    },
    onSuccess: (data) => {
      setReport(data);
      onResults(data);
      onError(null);
    },
    onError: (err: Error) => {
      setReport(null);
      onError(err.message);
    },
  });

  const pending = discoverMutation.isPending;

  return (
    <div className="discover">
      <p className="muted small-hint">
        Tell us what you want, then we search public job boards and rank every result
        against your resume.
      </p>

      <label className="field">
        <span>Role or keywords</span>
        <input
          type="text"
          value={keywords}
          placeholder="e.g. python backend engineer"
          onChange={(e) => setKeywords(e.target.value)}
          disabled={pending}
        />
      </label>

      <div className="field-row">
        <label className="field">
          <span>Experience level</span>
          <select value={seniority} onChange={(e) => setSeniority(e.target.value)} disabled={pending}>
            {SENIORITY.map((level) => (
              <option key={level || "any"} value={level}>
                {level || "Any"}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>City / area</span>
          <input
            type="text"
            value={location}
            placeholder="e.g. London"
            onChange={(e) => setLocation(e.target.value)}
            disabled={pending}
          />
        </label>
      </div>

      <div className="field-row">
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

        <label className="field">
          <span>Jobs to pull ({limit})</span>
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
      </div>

      <div className="field-row">
        <label className="field">
          <span>Minimum match ({minScore}%)</span>
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

      <button
        type="button"
        className="btn primary"
        onClick={() => discoverMutation.mutate()}
        disabled={pending}
      >
        {pending ? "Searching job boards..." : "Find & rank jobs online"}
      </button>

      {pending ? (
        <p className="muted small-hint">
          Fetching from job boards, then scoring each one. This takes a few seconds.
        </p>
      ) : null}

      {report ? (
        <div className="source-report">
          <p className="muted small-hint">
            Pulled {report.fetched_count} jobs, ranked {report.ranked_count}.
          </p>
          <ul className="source-list">
            {report.sources.map((s) => (
              <li key={s.name} className={s.error ? "muted" : ""}>
                {s.name}: {s.error ? s.error : `${s.fetched} found`}
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <ul className="source-list">
          {sourcesQuery.data?.map((s) => (
            <li key={s.name} className={s.available ? "" : "muted"}>
              {s.label} {s.available ? "" : "- not configured"}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
