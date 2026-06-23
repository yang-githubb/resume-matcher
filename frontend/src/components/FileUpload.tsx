import { useRef, useState } from "react";

interface FileUploadProps {
  label: string;
  accept: string;
  multiple?: boolean;
  maxFiles?: number;
  onFiles: (files: File[]) => void;
  disabled?: boolean;
}

export function FileUpload({
  label,
  accept,
  multiple = false,
  maxFiles = 1,
  onFiles,
  disabled = false,
}: FileUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [names, setNames] = useState<string[]>([]);

  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(event.target.files ?? []).slice(0, maxFiles);
    setNames(selected.map((f) => f.name));
    onFiles(selected);
  };

  return (
    <div className="upload-card">
      <label className="upload-label">{label}</label>
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
        onChange={handleChange}
      />
      {names.length > 0 ? (
        <p className="muted">{names.join(", ")}</p>
      ) : (
        <p className="muted">PDF or DOCX</p>
      )}
    </div>
  );
}
