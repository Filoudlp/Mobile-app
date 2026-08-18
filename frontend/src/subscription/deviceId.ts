// Persistent device identifier used to key freemium/subscription state on
// the backend when no user auth is present. Generated once, stored forever
// in AsyncStorage.

import AsyncStorage from "@react-native-async-storage/async-storage";

const KEY = "@structura/device_id/v1";

function randomId(): string {
  // Simple UUID-ish string — 128 bits of randomness is fine here.
  const random = (n: number) =>
    Array.from({ length: n }, () =>
      Math.floor(Math.random() * 16).toString(16),
    ).join("");
  return `${random(8)}-${random(4)}-${random(4)}-${random(4)}-${random(12)}`;
}

let cached: string | null = null;

export async function getDeviceId(): Promise<string> {
  if (cached) return cached;
  const stored = await AsyncStorage.getItem(KEY);
  if (stored) {
    cached = stored;
    return stored;
  }
  const id = randomId();
  await AsyncStorage.setItem(KEY, id);
  cached = id;
  return id;
}
