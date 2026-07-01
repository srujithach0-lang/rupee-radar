import type { RecurringGroup } from "../api/client";
import { CATEGORY_COLORS, formatINR } from "../utils/format";

interface RecurringListProps {
  groups: RecurringGroup[];
  totalMonthly: number;
}

export default function RecurringList({ groups, totalMonthly }: RecurringListProps) {
  if (groups.length === 0) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-slate-500">
        No recurring payments detected in this statement.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-brand-200 bg-brand-50 px-4 py-3 text-sm text-brand-800">
        {groups.length} recurring payment{groups.length !== 1 ? "s" : ""} totalling{" "}
        <span className="font-semibold">{formatINR(totalMonthly)}/month</span>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        {groups.map((group) => (
          <div
            key={group.id}
            className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
          >
            <div className="flex items-start justify-between gap-2">
              <div>
                <h3 className="font-semibold text-slate-800">{group.label}</h3>
                <p className="mt-0.5 text-sm text-slate-500 capitalize">
                  {group.frequency} · last seen {group.last_seen_date}
                </p>
              </div>
              <span
                className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium ${
                  CATEGORY_COLORS[group.category] ?? CATEGORY_COLORS.Other
                }`}
              >
                {group.category}
              </span>
            </div>
            <p className="mt-3 text-lg font-semibold text-slate-900">
              {formatINR(group.typical_amount)}
              <span className="text-sm font-normal text-slate-500"> / {group.frequency}</span>
            </p>
            <p className="mt-1 text-xs text-slate-400">
              {group.transaction_ids.length} occurrences · {Math.round(group.confidence * 100)}% confidence
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
