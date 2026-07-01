import { useCallback, useState } from "react";
import { uploadStatement } from "../api/client";

interface FileUploadProps {
  onUploaded: (sessionId: string) => void;
  onError: (message: string) => void;
}

const ACCEPTED_EXTENSIONS = [".csv", ".xlsx"];

export default function FileUpload({ onUploaded, onError }: FileUploadProps) {
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  const handleFile = useCallback(
    async (file: File | null) => {
      if (!file) return;
      const lower = file.name.toLowerCase();
      if (!ACCEPTED_EXTENSIONS.some((ext) => lower.endsWith(ext))) {
        onError("Please upload a CSV or Excel (.xlsx) bank statement.");
        return;
      }
      setUploading(true);
      try {
        const result = await uploadStatement(file);
        onUploaded(result.session_id);
      } catch (err) {
        onError(err instanceof Error ? err.message : "Upload failed");
      } finally {
        setUploading(false);
      }
    },
    [onUploaded, onError],
  );

  return (
    <div
      className={`rounded-2xl border-2 border-dashed p-12 text-center transition-colors ${
        dragOver ? "border-brand-500 bg-brand-50" : "border-slate-300 bg-white"
      }`}
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragOver(false);
        handleFile(e.dataTransfer.files[0] ?? null);
      }}
    >
      <p className="text-lg font-medium text-slate-800">Drop your bank statement here</p>
      <p className="mt-2 text-sm text-slate-500">
        HDFC · ICICI · generic CSV · Excel (.xlsx) · max 10 MB
      </p>
      <label className="mt-6 inline-block cursor-pointer rounded-lg bg-brand-600 px-6 py-2.5 text-sm font-medium text-white hover:bg-brand-700">
        {uploading ? "Analyzing…" : "Choose file"}
        <input
          type="file"
          accept=".csv,.xlsx"
          className="hidden"
          disabled={uploading}
          onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
        />
      </label>
      <p className="mt-4 text-xs text-slate-400">
        Unsupported format?{" "}
        <a
          href="/sample-statement-template.csv"
          download
          className="text-brand-600 hover:underline"
        >
          Download CSV template
        </a>
      </p>
    </div>
  );
}
