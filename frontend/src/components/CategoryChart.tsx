import {
  Bar,
  BarChart,
  Cell,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Analytics } from "../api/client";
import { formatINR } from "../utils/format";

const CATEGORY_FILL: Record<string, string> = {
  EMI: "#f97316",
  Rent: "#3b82f6",
  Investments: "#ec4899",
  Travel: "#eab308",
  Shopping: "#ef4444",
  Other: "#a855f7",
  Food: "#22c55e",
  Bills: "#6366f1",
  Subscriptions: "#14b8a6",
  Salary: "#64748b",
};

const FALLBACK_COLORS = [
  "#f97316", "#3b82f6", "#ec4899", "#eab308", "#ef4444",
  "#a855f7", "#22c55e", "#6366f1", "#14b8a6", "#64748b",
];

function categoryColor(name: string, index: number): string {
  return CATEGORY_FILL[name] ?? FALLBACK_COLORS[index % FALLBACK_COLORS.length];
}

interface CategoryChartProps {
  analytics: Analytics;
}

export default function CategoryChart({ analytics }: CategoryChartProps) {
  const total = analytics.top_categories.reduce((sum, c) => sum + c.amount, 0);
  const data = analytics.top_categories.map((c) => ({
    name: c.category,
    value: c.amount,
    percent: total > 0 ? (c.amount / total) * 100 : 0,
  }));

  if (data.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-500">
        No spending data to chart
      </div>
    );
  }

  const chartHeight = Math.max(240, data.length * 36 + 32);

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <ResponsiveContainer width="100%" height={chartHeight}>
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 4, right: 72, left: 0, bottom: 4 }}
        >
          <XAxis type="number" hide domain={[0, "dataMax"]} />
          <YAxis
            type="category"
            dataKey="name"
            width={96}
            tick={{ fontSize: 12, fill: "#334155" }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            formatter={(value) => formatINR(Number(value ?? 0))}
            labelFormatter={(label) => String(label)}
            contentStyle={{ borderRadius: 8, border: "1px solid #e2e8f0" }}
          />
          <Bar dataKey="value" name="Spend" barSize={22} radius={[0, 4, 4, 0]}>
            {data.map((entry, index) => (
              <Cell key={entry.name} fill={categoryColor(entry.name, index)} />
            ))}
            <LabelList
              dataKey="percent"
              position="right"
              formatter={(v) => `${Number(v).toFixed(0)}%`}
              style={{ fill: "#64748b", fontSize: 12 }}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <p className="mt-2 text-center text-xs text-slate-500">
        Total spend {formatINR(total)} · hover a bar for exact amount
      </p>
    </div>
  );
}
