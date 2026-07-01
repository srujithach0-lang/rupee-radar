import { useState } from "react";
import {
  CATEGORIES,
  type Category,
  type Transaction,
  updateTransactionCategory,
} from "../api/client";
import { CATEGORY_COLORS, formatINR } from "../utils/format";

interface TransactionTableProps {
  sessionId: string;
  transactions: Transaction[];
  onCategoryUpdated?: (txn: Transaction) => void;
}

export default function TransactionTable({
  sessionId,
  transactions,
  onCategoryUpdated,
}: TransactionTableProps) {
  const [updating, setUpdating] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleCategoryChange(txnId: string, category: Category) {
    setUpdating(txnId);
    setError(null);
    try {
      const result = await updateTransactionCategory(sessionId, txnId, category);
      onCategoryUpdated?.(result.transaction);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update category");
    } finally {
      setUpdating(null);
    }
  }

  return (
    <div>
      {error && (
        <div className="mb-3 rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
          {error}
        </div>
      )}
      <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-slate-600">
            <tr>
              <th className="px-4 py-3 font-medium">Date</th>
              <th className="px-4 py-3 font-medium">Description</th>
              <th className="px-4 py-3 font-medium">Amount</th>
              <th className="px-4 py-3 font-medium">Category</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {transactions.map((txn) => (
              <tr key={txn.id} className="hover:bg-slate-50">
                <td className="whitespace-nowrap px-4 py-3 text-slate-700">
                  {txn.date}
                  {txn.is_recurring && (
                    <span className="ml-1.5 inline-flex rounded bg-purple-100 px-1.5 py-0.5 text-[10px] font-medium text-purple-700">
                      recurring
                    </span>
                  )}
                </td>
                <td className="px-4 py-3">
                  <div className="font-medium text-slate-800">{txn.description_clean}</div>
                  <div className="mt-0.5 text-xs text-slate-400">{txn.description_raw}</div>
                </td>
                <td
                  className={`whitespace-nowrap px-4 py-3 font-medium ${
                    txn.amount < 0 ? "text-red-700" : "text-green-700"
                  }`}
                >
                  {formatINR(txn.amount)}
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <select
                      value={txn.category}
                      disabled={updating === txn.id}
                      onChange={(e) => handleCategoryChange(txn.id, e.target.value as Category)}
                      className={`rounded-lg border border-slate-200 px-2 py-1 text-xs font-medium focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 ${
                        CATEGORY_COLORS[txn.category] ?? CATEGORY_COLORS.Other
                      }`}
                    >
                      {CATEGORIES.map((cat) => (
                        <option key={cat} value={cat}>
                          {cat}
                        </option>
                      ))}
                    </select>
                    {txn.category_overridden && (
                      <span className="inline-flex rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-medium text-amber-800">
                        edited
                      </span>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
