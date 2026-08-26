import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { Step } from "@/components/Step";
import { discoverAndMatch, getSources } from "@/lib/api";
import type { SearchProgress } from "@/lib/api";
import type { DiscoverResponse, SourceInfo } from "@/types/api";

// The countries the keyed sources actually serve, US and Europe. Offering a
// country no source can search is what the capability checks below exist to
// prevent, so the list stays in step with that coverage.
const COUNTRIES = [
  { code: "us", label: "United States" },
  { code: "gb", label: "United Kingdom" },
  { code: "de", label: "Germany" },
  { code: "fr", label: "France" },
  { code: "nl", label: "Netherlands" },
  { code: "es", label: "Spain" },
  { code: "it", label: "Italy" },
  { code: "be", label: "Belgium" },
  { code: "at", label: "Austria" },
  { code: "pl", label: "Poland" },
];

const SENIORITY = ["", "junior", "mid-level", "senior", "lead", "principal"];

/** "JSearch / Google for Jobs (needs free RapidAPI key)" -> "JSearch". */
function shortName(source: SourceInfo): string {
  return source.label.split(/[/(]/)[0].trim();
}

function covers(source: SourceInfo, country: string): boolean {
  // A null country list means worldwide, so it covers everything.
  return source.supports_country && (source.countries === null || source.countries.includes(country));
}

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
  const [country, setCountry] = useState("us");
  const [limit, setLimit] = useState(25);
  const [minScore, setMinScore] = useState(0);
  const [report, setReport] = useState<DiscoverResponse | null>(null);
  const [progress, setProgress] = useState<SearchProgress | null>(null);
  // The settings behind Refine are read far less often than the role, so they
  // stay folded away with their values summarised instead.
  const [refineOpen, setRefineOpen] = useState(false);

  const queryClient = useQueryClient();
  const sourcesQuery = useQuery({ queryKey: ["sources"], queryFn: getSources });

  // Which filters mean anything depends on which boards are switched on, so
  // the panel asks the registry rather than keeping its own copy of the rules.
  const support = useMemo(() => {
    const sources = sourcesQuery.data ?? [];
    const active = sources.filter((s) => s.available);
    const enables = (pick: (s: SourceInfo) => boolean) =>
      sources.filter((s) => !s.available && pick(s)).map(shortName).join(" or ");

    return {
      known: sources.length > 0,
      location: active.some((s) => s.supports_location),
      locationNeeds: enables((s) => s.supports_location),
      country: active.some((s) => covers(s, country)),
      countryNeeds: enables((s) => covers(s, country)),
    };
  }, [sourcesQuery.data, country]);

  const countryLabel = COUNTRIES.find((c) => c.code === country)?.label ?? country;

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

        {support.known && !support.country ? (
          <p className="filter-warning">
            No active source covers {countryLabel}
            {support.countryNeeds ? ` - add a ${support.countryNeeds} key` : ""}. Results
            will come from the remote boards instead.
          </p>
        ) : null}

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
                placeholder={support.location ? "e.g. Berlin" : "Not available"}
                onChange={(e) => setLocation(e.target.value)}
                disabled={pending || (support.known && !support.location)}
              />
              {support.known && !support.location ? (
                <span className="field-note">
                  No active source filters by city
                  {support.locationNeeds ? ` - add a ${support.locationNeeds} key` : ""}.
                </span>
              ) : null}
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
