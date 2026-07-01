const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export const CATEGORIES = [
  "Food",
  "Travel",
  "Shopping",
  "Bills",
  "EMI",
  "Subscriptions",
  "Salary",
  "Rent",
  "Investments",
  "Other",
] as const;

export type Category = (typeof CATEGORIES)[number];

export interface Session {
  id: string;
  filename: string;
  file_type: string;
  status: string;
  uploaded_at: string;
  expires_at: string | null;
  row_count: number;
  error_message: string | null;
  parse_warnings: string[];
}

export interface Transaction {
  id: string;
  date: string;
  description_raw: string;
  description_clean: string;
  amount: number;
  type: string;
  balance: number | null;
  category: string;
  category_confidence: number;
  category_overridden: boolean;
  is_recurring: boolean;
  payment_mode: string | null;
  merchant: string | null;
}

export interface MonthlySpend {
  month: string;
  amount: number;
}

export interface Analytics {
  total_income: number;
  total_spend: number;
  savings: number;
  savings_rate: number | null;
  top_categories: { category: string; amount: number; count: number }[];
  biggest_debit: {
    id: string;
    date: string;
    description_clean: string;
    amount: number;
    category: string;
  } | null;
  transaction_count: number;
  period_start: string | null;
  period_end: string | null;
  monthly_spend: MonthlySpend[];
  recurring_total_monthly: number;
}

export interface Insight {
  text: string;
  source: "template" | "ai";
}

export interface RecurringGroup {
  id: string;
  label: string;
  category: string;
  frequency: string;
  typical_amount: number;
  last_seen_date: string;
  transaction_ids: string[];
  confidence: number;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const message = body.detail || `Request failed: ${response.status}`;
    throw new Error(typeof message === "string" ? message : JSON.stringify(message));
  }
  return response.json();
}

export async function checkHealth(): Promise<{ status: string; groq_configured: boolean }> {
  const response = await fetch(`${API_URL}/api/v1/health`);
  return handleResponse(response);
}

export async function uploadStatement(file: File): Promise<{ session_id: string; status: string }> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`${API_URL}/api/v1/upload`, { method: "POST", body: form });
  return handleResponse(response);
}

export async function getSession(sessionId: string): Promise<Session> {
  const response = await fetch(`${API_URL}/api/v1/sessions/${sessionId}`);
  return handleResponse(response);
}

export async function getAnalytics(sessionId: string): Promise<Analytics> {
  const response = await fetch(`${API_URL}/api/v1/sessions/${sessionId}/analytics`);
  return handleResponse(response);
}

export async function getInsights(sessionId: string): Promise<{ insights: Insight[] }> {
  const response = await fetch(`${API_URL}/api/v1/sessions/${sessionId}/insights`);
  return handleResponse(response);
}

export async function getRecurring(sessionId: string): Promise<{
  groups: RecurringGroup[];
  recurring_total_monthly: number;
}> {
  const response = await fetch(`${API_URL}/api/v1/sessions/${sessionId}/recurring`);
  return handleResponse(response);
}

export async function getTransactions(
  sessionId: string,
  page = 1,
  pageSize = 50,
): Promise<{ items: Transaction[]; total: number; page: number; page_size: number }> {
  const response = await fetch(
    `${API_URL}/api/v1/sessions/${sessionId}/transactions?page=${page}&page_size=${pageSize}&sort_by=date&sort_order=desc`,
  );
  return handleResponse(response);
}

export async function updateTransactionCategory(
  sessionId: string,
  txnId: string,
  category: Category,
): Promise<{ transaction: Transaction; analytics_updated: boolean }> {
  const response = await fetch(
    `${API_URL}/api/v1/sessions/${sessionId}/transactions/${txnId}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ category }),
    },
  );
  return handleResponse(response);
}

export async function deleteSession(sessionId: string): Promise<void> {
  const response = await fetch(`${API_URL}/api/v1/sessions/${sessionId}`, { method: "DELETE" });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const message = body.detail || `Request failed: ${response.status}`;
    throw new Error(typeof message === "string" ? message : JSON.stringify(message));
  }
}

export function getReportUrl(sessionId: string, format: "html" | "pdf" = "html"): string {
  return `${API_URL}/api/v1/sessions/${sessionId}/report?format=${format}`;
}

export { API_URL };
