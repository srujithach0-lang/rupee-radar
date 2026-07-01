import { useState } from "react";
import { getReportUrl } from "../api/client";

interface ReportExportProps {
  sessionId: string;
}

export default function ReportExport({ sessionId }: ReportExportProps) {
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function downloadPdf() {
    setDownloading(true);
    setError(null);
    try {
      const response = await fetch(getReportUrl(sessionId, "pdf"));
      if (!response.ok) {
        throw new Error("Failed to generate PDF report");
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `rupeeradar-report-${sessionId.slice(0, 8)}.pdf`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Download failed");
    } finally {
      setDownloading(false);
    }
  }

  function openPrintView() {
    window.open(getReportUrl(sessionId, "html"), "_blank", "noopener,noreferrer");
  }

  return (
    <div className="flex flex-wrap items-center gap-3">
      <button
        type="button"
        onClick={downloadPdf}
        disabled={downloading}
        className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-60"
      >
        {downloading ? "Generating PDF…" : "Download PDF"}
      </button>
      <button
        type="button"
        onClick={openPrintView}
        className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
      >
        Print / Share
      </button>
      {error && <p className="text-sm text-red-600">{error}</p>}
    </div>
  );
}
