// Local-only calculation history storage.
// Backed by AsyncStorage (native) and a JSON shim on web (same lib).

import AsyncStorage from "@react-native-async-storage/async-storage";

const HISTORY_KEY = "@structura/history/v1";

export type HistoryResult = {
  label: string;
  value: string;
  unit?: string;
  status?: "ok" | "warning" | "error";
};

export type HistoryEntry = {
  id: string;
  moduleId: string;
  moduleName: string;
  categoryId: string;
  createdAt: number; // epoch ms
  inputs: Record<string, string>;
  results: HistoryResult[];
};

export async function loadHistory(): Promise<HistoryEntry[]> {
  try {
    const raw = await AsyncStorage.getItem(HISTORY_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed as HistoryEntry[];
  } catch {
    return [];
  }
}

export async function saveEntry(entry: HistoryEntry): Promise<void> {
  const current = await loadHistory();
  const next = [entry, ...current].slice(0, 100);
  await AsyncStorage.setItem(HISTORY_KEY, JSON.stringify(next));
}

export async function deleteEntry(id: string): Promise<void> {
  const current = await loadHistory();
  const next = current.filter((e) => e.id !== id);
  await AsyncStorage.setItem(HISTORY_KEY, JSON.stringify(next));
}

export async function clearHistory(): Promise<void> {
  await AsyncStorage.removeItem(HISTORY_KEY);
}
