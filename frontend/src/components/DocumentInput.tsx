import { useRef, useState } from "react";

export type InputMode = "file" | "paste";

interface DocumentInputProps {
  label: string;
  docType: "resume" | "job";
  accept?: string;
  multiple?: boolean;
  maxFiles?: number;
  onReady: (payload: { file?: File; text?: string; label?: string }) => void;
  disabled?: boolean;
}

export function DocumentInput({
  label,
  docType,
  accept = ".pdf,.docx",
  multiple = false,
  maxFiles = 1,
  onReady,
  disabled = false,
}: DocumentInputProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [mode, setMode] = useState<InputMode>("file");
  const [fileNames, setFileNames] = useState<string[]>([]);
  const [pasteText, setPasteText] = useState("");

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(event.target.files ?? []).slice(0, maxFiles);
    setFileNames(selected.map((f) => f.name));
    if (selected.length === 1 && !multiple) {
      onReady({ file: selected[0] });
    } else if (selected.length > 0 && multiple) {
      selected.forEach((file) => onReady({ file }));
    }
  };

  const handlePasteBlur = () => {
    const text = pasteText.trim();
    if (text.length >= 30) {
      onReady({
        text,
        label: `${docType}-paste.txt`,
      });
    }
  };

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
            Choose file{multiple ? "s" : ""}
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
            <p className="muted">{fileNames.join(", ")}</p>
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
          <p className="muted">Min 30 characters. Click outside the box to confirm.</p>
        </>
      )}
    </div>
  );
}
