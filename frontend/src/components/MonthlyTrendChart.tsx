import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Analytics } from "../api/client";
import { formatINR } from "../utils/format";

interface MonthlyTrendChartProps {
  analytics: Analytics;
  highlightMonth?: string | null;
}

function formatMonth(month: string): string {
  const [year, m] = month.split("-");
  const date = new Date(Number(year), Number(m) - 1);
  return date.toLocaleDateString("en-IN", { month: "short", year: "2-digit" });
}

export default function MonthlyTrendChart({ analytics, highlightMonth }: MonthlyTrendChartProps) {
  const data = analytics.monthly_spend.map((m) => ({
    month: formatMonth(m.month),
    rawMonth: m.month,
    spend: m.amount,
    isHighlighted: m.month === highlightMonth,
  }));

  if (data.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-500">
        No monthly data to chart
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey="month" tick={{ fontSize: 12 }} />
          <YAxis tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`} tick={{ fontSize: 12 }} />
          <Tooltip
            formatter={(value) => formatINR(Number(value ?? 0))}
            contentStyle={{ borderRadius: 8, border: "1px solid #e2e8f0" }}
          />
          <Bar dataKey="spend" name="Spend" radius={[4, 4, 0, 0]}>
            {data.map((entry) => (
              <Cell
                key={entry.rawMonth}
                fill={entry.isHighlighted ? "#f97316" : "#3b82f6"}
                opacity={highlightMonth && !entry.isHighlighted ? 0.45 : 1}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      {highlightMonth && (
        <div className="mt-2 flex items-center justify-center gap-3 text-xs text-slate-500">
          <span className="flex items-center gap-1">
            <span className="inline-block h-2.5 w-2.5 rounded-sm bg-orange-500" />
            {formatMonth(highlightMonth)} (selected)
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block h-2.5 w-2.5 rounded-sm bg-blue-400 opacity-45" />
            Other months
          </span>
        </div>
      )}
    </div>
  );
}
