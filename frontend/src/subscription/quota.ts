// Daily calculation quota — local device counter.
//
// Free tier: 5 calculations / day. Premium: unlimited (handled in caller).
// Persisted with the same AsyncStorage lib used by the history feature.

import AsyncStorage from "@react-native-async-storage/async-storage";

const QUOTA_KEY = "@structura/quota/v1";

export const FREE_DAILY_LIMIT = 5;

export type QuotaState = {
  date: string; // YYYY-MM-DD
  count: number;
};

function todayKey(): string {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

export async function loadQuota(): Promise<QuotaState> {
  try {
    const raw = await AsyncStorage.getItem(QUOTA_KEY);
    if (!raw) return { date: todayKey(), count: 0 };
    const parsed = JSON.parse(raw) as QuotaState;
    // Reset if a new day started.
    if (parsed.date !== todayKey()) {
      return { date: todayKey(), count: 0 };
    }
    return parsed;
  } catch {
    return { date: todayKey(), count: 0 };
  }
}

/** Returns updated quota after increment. */
export async function incrementQuota(): Promise<QuotaState> {
  const current = await loadQuota();
  const next: QuotaState = { date: current.date, count: current.count + 1 };
  await AsyncStorage.setItem(QUOTA_KEY, JSON.stringify(next));
  return next;
}

export function remaining(state: QuotaState): number {
  return Math.max(0, FREE_DAILY_LIMIT - state.count);
}
