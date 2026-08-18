// Subscription state — Stripe subscription (recurring EUR 4.99 / month).
//
// The backend is the source of truth (see /app/backend/stripe_service.py).
// We cache the last known state in AsyncStorage so the UI stays responsive
// while offline; every screen that cares calls `refreshSubscription()` on
// focus so it reflects webhook updates within a few seconds.

import AsyncStorage from "@react-native-async-storage/async-storage";

import { getDeviceId } from "./deviceId";

const CACHE_KEY = "@structura/premium/v2";
const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL ?? "";

export type SubscriptionSource = "backend" | "mock" | "cache";

export type SubscriptionState = {
  active: boolean;
  since: number | null;
  source: SubscriptionSource;
  status?: string | null;
  currentPeriodEnd?: number | null;
  stripeSubscriptionId?: string | null;
  cancelAtPeriodEnd?: boolean;
};

export const PRICE = "4,99 €";
export const PRICE_PER_MONTH = "4,99 €/mois";

const DEFAULT_STATE: SubscriptionState = {
  active: false,
  since: null,
  source: "cache",
  status: null,
  currentPeriodEnd: null,
  stripeSubscriptionId: null,
  cancelAtPeriodEnd: false,
};

async function readCache(): Promise<SubscriptionState> {
  try {
    const raw = await AsyncStorage.getItem(CACHE_KEY);
    if (!raw) return { ...DEFAULT_STATE };
    return { ...DEFAULT_STATE, ...(JSON.parse(raw) as SubscriptionState) };
  } catch {
    return { ...DEFAULT_STATE };
  }
}

async function writeCache(state: SubscriptionState): Promise<void> {
  await AsyncStorage.setItem(CACHE_KEY, JSON.stringify(state));
}

/** Return the last known state — fast, from cache. */
export async function loadSubscription(): Promise<SubscriptionState> {
  return readCache();
}

/** Force a network refresh and return the updated state. */
export async function refreshSubscription(): Promise<SubscriptionState> {
  if (!BACKEND_URL) return readCache();
  try {
    const deviceId = await getDeviceId();
    const res = await fetch(`${BACKEND_URL}/api/stripe/status/${deviceId}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const json = (await res.json()) as {
      is_premium: boolean;
      status: string | null;
      current_period_end: number | null;
      stripe_subscription_id: string | null;
      cancel_at_period_end: boolean;
    };
    const state: SubscriptionState = {
      active: json.is_premium,
      since: json.is_premium ? Date.now() : null,
      source: "backend",
      status: json.status,
      currentPeriodEnd: json.current_period_end,
      stripeSubscriptionId: json.stripe_subscription_id,
      cancelAtPeriodEnd: json.cancel_at_period_end,
    };
    await writeCache(state);
    return state;
  } catch {
    // Network / server hiccup — keep whatever we had cached.
    return readCache();
  }
}

/** Ask the backend to trigger a manual reconciliation (post-checkout). */
export async function reconcileSubscription(
  sessionId: string,
): Promise<SubscriptionState> {
  if (!BACKEND_URL) return readCache();
  try {
    const deviceId = await getDeviceId();
    const params = new URLSearchParams({
      device_id: deviceId,
      session_id: sessionId,
    });
    const res = await fetch(
      `${BACKEND_URL}/api/stripe/reconcile?${params.toString()}`,
      { method: "POST" },
    );
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return refreshSubscription();
  } catch {
    return refreshSubscription();
  }
}

/**
 * Ask the backend to create a Stripe Checkout Session.
 * Returns the hosted checkout URL to open in the browser.
 */
export async function createCheckoutSession(params: {
  successUrl: string;
  cancelUrl: string;
  email?: string;
}): Promise<{ url: string; sessionId: string }> {
  if (!BACKEND_URL) throw new Error("Backend URL not configured");
  const deviceId = await getDeviceId();
  const res = await fetch(`${BACKEND_URL}/api/stripe/create-checkout`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      device_id: deviceId,
      success_url: params.successUrl,
      cancel_url: params.cancelUrl,
      email: params.email,
    }),
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`Stripe checkout: ${res.status} — ${txt}`);
  }
  const data = (await res.json()) as { url: string; session_id: string };
  return { url: data.url, sessionId: data.session_id };
}

/**
 * Dev-only helper: force a premium state locally. Kept so the "mock toggle"
 * in Paramètres still works while the app is offline / Stripe not wired.
 */
export async function setPremium(active: boolean): Promise<SubscriptionState> {
  const next: SubscriptionState = {
    ...DEFAULT_STATE,
    active,
    since: active ? Date.now() : null,
    source: "mock",
    status: active ? "active" : null,
  };
  await writeCache(next);
  return next;
}
