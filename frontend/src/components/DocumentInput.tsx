import { useRef, useState } from "react";

export type InputMode = "file" | "paste";

interface DocumentInputProps {
  label: string;
  docType: "resume" | "job";
  accept?: string;
  multiple?: boolean;
  maxFiles?: number;
  onReady: (payload: { file?: File; text?: string; label?: string }) => void;
  onCleared?: () => void;
  disabled?: boolean;
}

export function DocumentInput({
  label,
  docType,
  accept = ".pdf,.docx",
  multiple = false,
  maxFiles = 1,
  onReady,
  onCleared,
  disabled = false,
}: DocumentInputProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [mode, setMode] = useState<InputMode>("file");
  const [fileNames, setFileNames] = useState<string[]>([]);
  const [pasteText, setPasteText] = useState("");
  // Blur fires whenever focus leaves, not only when the text changed.
  const lastSubmitted = useRef("");

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(event.target.files ?? []).slice(0, maxFiles);
    // Clearing the input lets the same file be picked again: the browser
    // fires no change event when the value is unchanged.
    event.target.value = "";
    if (selected.length === 0) return;

    setFileNames(selected.map((f) => f.name));
    if (!multiple) {
      onReady({ file: selected[0] });
    } else {
      selected.forEach((file) => onReady({ file }));
    }
  };

  const handlePasteBlur = () => {
    const text = pasteText.trim();
    if (text.length >= 30 && text !== lastSubmitted.current) {
      lastSubmitted.current = text;
      onReady({ text, label: `${docType}-paste.txt` });
    }
  };

  const clearSelection = () => {
    setFileNames([]);
    setPasteText("");
    lastSubmitted.current = "";
    if (inputRef.current) inputRef.current.value = "";
    onCleared?.();
  };

  const hasSelection = fileNames.length > 0 || pasteText.trim().length > 0;

  // Once a file is chosen the dropbox has nothing left to say, so it collapses
  // to a row naming what is loaded. Paste keeps its textarea for editing.
  if (onCleared && mode === "file" && fileNames.length > 0) {
    return (
      <div className="loaded-file">
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
        </svg>
        <div className="loaded-file-name">
          <span>{fileNames.join(", ")}</span>
          <span className="loaded-file-label">{label}</span>
        </div>
        <button
          type="button"
          className="linkish"
          disabled={disabled}
          onClick={() => inputRef.current?.click()}
        >
          Change
        </button>
        <button type="button" className="linkish" disabled={disabled} onClick={clearSelection}>
          Remove
        </button>
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          multiple={multiple}
          hidden
          onChange={handleFileChange}
        />
      </div>
    );
  }

  return (
    <div className="upload-card">
      <div className="input-header">
        <label className="upload-label">{label}</label>
        <div className="mini-toggle">
          <button
            type="button"
            className={mode === "file" ? "btn active small" : "btn secondary small"}
            disabled={disabled}
            onClick={() => setMode("file")}
          >
            File
          </button>
          <button
            type="button"
            className={mode === "paste" ? "btn active small" : "btn secondary small"}
            disabled={disabled}
            onClick={() => setMode("paste")}
          >
            Paste
          </button>
        </div>
      </div>

      {mode === "file" ? (
        <>
          <button
            type="button"
            className="btn secondary"
            disabled={disabled}
            onClick={() => inputRef.current?.click()}
          >
            {fileNames.length > 0 ? "Change file" : `Choose file${multiple ? "s" : ""}`}
          </button>
          <input
            ref={inputRef}
            type="file"
            accept={accept}
            multiple={multiple}
            hidden
            onChange={handleFileChange}
          />
          {fileNames.length > 0 ? (
            <p className="muted selected-file">
              <span>{fileNames.join(", ")}</span>
              {onCleared ? (
                <button
                  type="button"
                  className="linkish"
                  disabled={disabled}
                  onClick={clearSelection}
                >
                  Remove
                </button>
              ) : null}
            </p>
          ) : (
            <p className="muted">PDF or DOCX</p>
          )}
        </>
      ) : (
        <>
          <textarea
            className="paste-area"
            rows={6}
            placeholder="Paste job description or resume text here..."
            value={pasteText}
            disabled={disabled}
            onChange={(e) => setPasteText(e.target.value)}
            onBlur={handlePasteBlur}
          />
          <p className="muted selected-file">
            <span>Min 30 characters. Click outside the box to confirm.</span>
            {onCleared && hasSelection ? (
              <button
                type="button"
                className="linkish"
                disabled={disabled}
                onClick={clearSelection}
              >
                Remove
              </button>
            ) : null}
          </p>
        </>
      )}
    </div>
  );
}
