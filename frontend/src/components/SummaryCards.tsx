import type { Analytics } from "../api/client";
import { formatINR } from "../utils/format";

interface SummaryCardsProps {
  analytics: Analytics;
}

export default function SummaryCards({ analytics }: SummaryCardsProps) {
  const cards = [
    { label: "Total Income", value: formatINR(analytics.total_income), color: "text-green-700" },
    { label: "Total Spend", value: formatINR(analytics.total_spend), color: "text-red-700" },
    { label: "Savings", value: formatINR(analytics.savings), color: "text-brand-700" },
    {
      label: "Savings Rate",
      value: analytics.savings_rate !== null ? `${analytics.savings_rate}%` : "N/A",
      color: "text-slate-700",
    },
  ];

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((card) => (
        <div key={card.label} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm text-slate-500">{card.label}</p>
          <p className={`mt-1 text-2xl font-bold ${card.color}`}>{card.value}</p>
        </div>
      ))}
    </div>
  );
}
