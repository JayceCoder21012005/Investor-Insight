// Number and date formatting for the Vietnamese UI. Display only: no business logic lives here.
const LOCALE = "vi-VN";
const MISSING = "—";

type Maybe = number | null | undefined;
const isMissing = (x: Maybe): x is null | undefined => x === null || x === undefined || Number.isNaN(x);

export function formatPercent(x: Maybe, digits = 1): string {
  if (isMissing(x)) return MISSING;
  return new Intl.NumberFormat(LOCALE, {
    style: "percent",
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(x);
}

export function formatNumber(x: Maybe, digits = 2): string {
  if (isMissing(x)) return MISSING;
  return new Intl.NumberFormat(LOCALE, { minimumFractionDigits: 0, maximumFractionDigits: digits }).format(x);
}

export function formatVnd(x: Maybe): string {
  if (isMissing(x)) return MISSING;
  return new Intl.NumberFormat(LOCALE, { style: "currency", currency: "VND", maximumFractionDigits: 0 }).format(x);
}

/** "2026-01-05" -> "05/01/2026" (string split, so no timezone can shift the day). */
export function formatDate(iso: string): string {
  const [y, m, d] = iso.split("-");
  return `${d}/${m}/${y}`;
}
