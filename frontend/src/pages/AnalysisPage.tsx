import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  deleteSession,
  getAnalytics,
  getInsights,
  getRecurring,
  getSession,
  getTransactions,
  type Analytics,
  type Insight,
  type RecurringGroup,
  type Transaction,
} from "../api/client";
import CategoryChart from "../components/CategoryChart";
import InsightCards from "../components/InsightCards";
import MonthlyTrendChart from "../components/MonthlyTrendChart";
import ProcessingStatus from "../components/ProcessingStatus";
import RecurringList from "../components/RecurringList";
import ReportExport from "../components/ReportExport";
import SummaryCards from "../components/SummaryCards";
import TransactionTable from "../components/TransactionTable";
import { formatINR } from "../utils/format";

type Tab = "summary" | "transactions" | "recurring" | "insights";

const TABS: { id: Tab; label: string }[] = [
  { id: "summary", label: "Summary" },
  { id: "transactions", label: "Transactions" },
  { id: "recurring", label: "Recurring" },
  { id: "insights", label: "Insights" },
];

export default function AnalysisPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("summary");
  const [thisMonthOnly, setThisMonthOnly] = useState(false);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [insights, setInsights] = useState<Insight[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [recurringGroups, setRecurringGroups] = useState<RecurringGroup[]>([]);
  const [recurringTotal, setRecurringTotal] = useState(0);
  const [filename, setFilename] = useState("");
  const [parseWarnings, setParseWarnings] = useState<string[]>([]);

  const latestMonth = useMemo(() => {
    if (!analytics?.period_end) return null;
    return analytics.period_end.slice(0, 7);
  }, [analytics?.period_end]);

  // Filtered transaction list for the transactions tab
  const filteredTransactions = useMemo(() => {
    if (!thisMonthOnly || !latestMonth) return transactions;
    return transactions.filter((t) => t.date.startsWith(latestMonth));
  }, [transactions, thisMonthOnly, latestMonth]);

  // Recomputed analytics for the summary tab when "this month" is toggled
  const filteredAnalytics = useMemo(() => {
    if (!analytics || !thisMonthOnly || !latestMonth) return analytics;

    const monthTxns = transactions.filter((t) => t.date.startsWith(latestMonth) && t.amount < 0);
    const spend = monthTxns.reduce((sum, t) => sum + Math.abs(t.amount), 0);
    const categoryMap: Record<string, { amount: number; count: number }> = {};
    for (const t of monthTxns) {
      if (!categoryMap[t.category]) categoryMap[t.category] = { amount: 0, count: 0 };
      categoryMap[t.category].amount += Math.abs(t.amount);
      categoryMap[t.category].count += 1;
    }
    const top_categories = Object.entries(categoryMap)
      .map(([category, { amount, count }]) => ({ category, amount, count }))
      .sort((a, b) => b.amount - a.amount);

    return {
      ...analytics,
      total_spend: spend,
      top_categories,
      monthly_spend: analytics.monthly_spend.filter((m) => m.month === latestMonth),
    };
  }, [analytics, thisMonthOnly, latestMonth, transactions]);

  const refreshData = useCallback(async () => {
    if (!sessionId) return;
    const [analyticsData, insightsData, txnData, recurringData] = await Promise.all([
      getAnalytics(sessionId),
      getInsights(sessionId),
      getTransactions(sessionId, 1, 100),
      getRecurring(sessionId),
    ]);
    setAnalytics(analyticsData);
    setInsights(insightsData.insights);
    setTransactions(txnData.items);
    setRecurringGroups(recurringData.groups);
    setRecurringTotal(recurringData.recurring_total_monthly);
  }, [sessionId]);

  useEffect(() => {
    if (!sessionId) return;

    async function load() {
      try {
        const session = await getSession(sessionId!);
        setFilename(session.filename);
        if (session.parse_warnings && session.parse_warnings.length > 0) {
          setParseWarnings(session.parse_warnings);
        }

        if (session.status !== "ready") {
          setError(session.error_message || "Session is not ready");
          setLoading(false);
          return;
        }

        await refreshData();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load analysis");
      } finally {
        setLoading(false);
      }
    }

    load();
  }, [sessionId, refreshData]);

  async function handleDeleteSession() {
    if (!sessionId) return;
    if (!window.confirm("Delete this analysis and all associated data?")) return;
    try {
      await deleteSession(sessionId);
      window.location.href = "/";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete session");
    }
  }

  async function handleCategoryUpdated() {
    await refreshData();
  }

  if (loading) {
    return (
      <PageShell>
        <ProcessingStatus />
      </PageShell>
    );
  }

  if (error || !analytics || !filteredAnalytics) {
    return (
      <PageShell>
        <div className="rounded-xl border border-red-200 bg-red-50 p-8 text-center">
          <p className="text-red-800">{error || "Analysis not found"}</p>
          <Link to="/" className="mt-4 inline-block text-sm font-medium text-brand-700 hover:underline">
            Upload another statement
          </Link>
        </div>
      </PageShell>
    );
  }

  return (
    <PageShell>
      <div className="mb-8">
        <Link to="/" className="text-sm font-medium text-brand-700 hover:underline">
          ← Upload another
        </Link>
        <h1 className="mt-2 text-2xl font-bold text-slate-900">Spending Analysis</h1>
        <p className="text-sm text-slate-500">
          {filename} · {analytics.transaction_count} transactions
          {analytics.period_start && analytics.period_end && (
            <> · {analytics.period_start} to {analytics.period_end}</>
          )}
        </p>
        <div className="mt-4 flex flex-wrap items-center gap-4">
          {sessionId && <ReportExport sessionId={sessionId} />}
          <button
            type="button"
            onClick={handleDeleteSession}
            className="text-sm font-medium text-red-600 hover:text-red-800"
          >
            Delete my data
          </button>
        </div>
        {parseWarnings.length > 0 && (
          <details className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-xs text-amber-800">
            <summary className="cursor-pointer font-medium">
              {parseWarnings.length} parse warning{parseWarnings.length !== 1 ? "s" : ""} — some rows were skipped
            </summary>
            <ul className="mt-2 list-disc space-y-0.5 pl-4">
              {parseWarnings.map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          </details>
        )}
      </div>

      <div className="mb-6 flex flex-wrap items-center gap-4 border-b border-slate-200">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            className={`border-b-2 px-1 pb-3 text-sm font-medium transition-colors ${
              activeTab === tab.id
                ? "border-brand-600 text-brand-700"
                : "border-transparent text-slate-500 hover:text-slate-700"
            }`}
          >
            {tab.label}
            {tab.id === "recurring" && recurringGroups.length > 0 && (
              <span className="ml-1.5 rounded-full bg-purple-100 px-1.5 py-0.5 text-xs text-purple-700">
                {recurringGroups.length}
              </span>
            )}
          </button>
        ))}
      </div>

      {activeTab === "summary" && (
        <section className="space-y-8">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-lg font-semibold text-slate-800">Overview</h2>
            {latestMonth && (
              <label className="flex items-center gap-2 text-sm text-slate-600">
                <input
                  type="checkbox"
                  checked={thisMonthOnly}
                  onChange={(e) => setThisMonthOnly(e.target.checked)}
                  className="rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                />
                This month only ({latestMonth})
              </label>
            )}
          </div>

          <SummaryCards analytics={thisMonthOnly ? filteredAnalytics : analytics} />

          {analytics.recurring_total_monthly > 0 && !thisMonthOnly && (
            <div className="rounded-lg border border-purple-200 bg-purple-50 px-4 py-3 text-sm text-purple-800">
              Recurring commitments:{" "}
              <span className="font-semibold">{formatINR(analytics.recurring_total_monthly)}/month</span>
            </div>
          )}

          <div className="grid gap-8 lg:grid-cols-2">
            <div>
              <h3 className="mb-3 text-base font-semibold text-slate-800">Spend by Category</h3>
              <CategoryChart analytics={filteredAnalytics} />
            </div>
            <div>
              <h3 className="mb-3 text-base font-semibold text-slate-800">Monthly Trend</h3>
              <MonthlyTrendChart
                analytics={thisMonthOnly ? analytics : filteredAnalytics}
                highlightMonth={thisMonthOnly ? latestMonth : null}
              />
            </div>
          </div>
        </section>
      )}

      {activeTab === "transactions" && sessionId && (
        <section>
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-slate-500">
              {filteredTransactions.length} transaction{filteredTransactions.length !== 1 ? "s" : ""}
              {thisMonthOnly && latestMonth ? ` in ${latestMonth}` : ""} · click a category to override
            </p>
            {latestMonth && (
              <label className="flex items-center gap-2 text-sm text-slate-600">
                <input
                  type="checkbox"
                  checked={thisMonthOnly}
                  onChange={(e) => setThisMonthOnly(e.target.checked)}
                  className="rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                />
                This month only ({latestMonth})
              </label>
            )}
          </div>
          <TransactionTable
            sessionId={sessionId}
            transactions={filteredTransactions}
            onCategoryUpdated={handleCategoryUpdated}
          />
        </section>
      )}

      {activeTab === "recurring" && (
        <section>
          <RecurringList groups={recurringGroups} totalMonthly={recurringTotal} />
        </section>
      )}

      {activeTab === "insights" && (
        <section>
          <InsightCards insights={insights} />
        </section>
      )}
    </PageShell>
  );
}

function PageShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-6xl px-6 py-4">
          <h1 className="text-xl font-bold text-brand-700">RupeeRadar</h1>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-10">{children}</main>
    </div>
  );
}
