export interface Insight {
  text: string;
  source: "template" | "ai";
}

interface InsightCardsProps {
  insights: Insight[];
}

export default function InsightCards({ insights }: InsightCardsProps) {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {insights.map((insight, index) => (
        <div
          key={index}
          className="rounded-xl border border-brand-100 bg-brand-50 p-5 text-sm leading-relaxed text-slate-800"
        >
          <span className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-brand-700">
            Insight {index + 1}
            {insight.source === "ai" && (
              <span className="rounded bg-purple-100 px-1.5 py-0.5 text-[10px] font-bold text-purple-700">
                AI
              </span>
            )}
          </span>
          {insight.text}
        </div>
      ))}
    </div>
  );
}
