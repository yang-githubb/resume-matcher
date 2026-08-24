import type { ReactNode } from "react";

interface StepProps {
  index: number;
  title: string;
  /** A finished step shows a tick instead of its number. */
  done?: boolean;
  /** The last step draws no connecting line below its marker. */
  last?: boolean;
  children: ReactNode;
}

export function Step({ index, title, done = false, last = false, children }: StepProps) {
  return (
    <div className="step">
      <div className="step-rail">
        <span className="step-marker" data-done={done}>
          {done ? (
            <svg
              width="12"
              height="12"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="3.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <polyline points="20 6 9 17 4 12" />
            </svg>
          ) : (
            index
          )}
        </span>
        {last ? null : <span className="step-line" />}
      </div>
      <div className="step-body">
        <h2 className="step-title">{title}</h2>
        {children}
      </div>
    </div>
  );
}
