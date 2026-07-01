interface ProcessingStatusProps {
  message?: string;
}

export default function ProcessingStatus({ message = "Analyzing your statement…" }: ProcessingStatusProps) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-slate-200 bg-white p-16 shadow-sm">
      <div className="h-10 w-10 animate-spin rounded-full border-4 border-brand-200 border-t-brand-600" />
      <p className="mt-4 text-lg font-medium text-slate-800">{message}</p>
      <p className="mt-2 text-sm text-slate-500">Cleaning, categorizing, and generating insights</p>
    </div>
  );
}
