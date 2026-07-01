export function formatINR(amount: number): string {
  const abs = Math.abs(amount);
  const [whole, frac = "00"] = abs.toFixed(2).split(".");
  let formatted: string;
  if (whole.length <= 3) {
    formatted = whole;
  } else {
    const last3 = whole.slice(-3);
    let rest = whole.slice(0, -3);
    const groups: string[] = [];
    while (rest.length > 0) {
      groups.unshift(rest.slice(-2));
      rest = rest.slice(0, -2);
    }
    formatted = `${groups.join(",")},${last3}`;
  }
  const sign = amount < 0 ? "-" : "";
  return `${sign}₹${formatted}.${frac}`;
}

export const CATEGORY_COLORS: Record<string, string> = {
  Food: "bg-orange-100 text-orange-800",
  Travel: "bg-blue-100 text-blue-800",
  Shopping: "bg-pink-100 text-pink-800",
  Bills: "bg-yellow-100 text-yellow-800",
  EMI: "bg-red-100 text-red-800",
  Subscriptions: "bg-purple-100 text-purple-800",
  Salary: "bg-green-100 text-green-800",
  Rent: "bg-indigo-100 text-indigo-800",
  Investments: "bg-teal-100 text-teal-800",
  Other: "bg-slate-100 text-slate-700",
};
