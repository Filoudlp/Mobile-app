// React hook that centralises quota + subscription state and exposes helpers
// to the module/history/settings screens.

import { useCallback, useEffect, useState } from "react";
import {
  FREE_DAILY_LIMIT,
  incrementQuota,
  loadQuota,
  QuotaState,
  remaining as _remaining,
} from "./quota";
import {
  loadSubscription,
  refreshSubscription,
  setPremium,
  SubscriptionState,
} from "./subscription";

export type EntitlementState = {
  quota: QuotaState;
  remaining: number;
  premium: SubscriptionState;
  /** true if the user can run at least one more calculation right now */
  canCompute: boolean;
};

const initialQuota: QuotaState = { date: "", count: 0 };
const initialSub: SubscriptionState = {
  active: false,
  since: null,
  source: "cache",
};

export function useEntitlement(): {
  state: EntitlementState;
  refresh: () => Promise<void>;
  refreshRemote: () => Promise<void>;
  registerCalculation: () => Promise<void>;
  togglePremiumMock: (active: boolean) => Promise<void>;
} {
  const [quota, setQuota] = useState<QuotaState>(initialQuota);
  const [premium, setPremiumState] = useState<SubscriptionState>(initialSub);

  const refresh = useCallback(async () => {
    const [q, p] = await Promise.all([loadQuota(), loadSubscription()]);
    setQuota(q);
    setPremiumState(p);
  }, []);

  const refreshRemote = useCallback(async () => {
    const [q, p] = await Promise.all([loadQuota(), refreshSubscription()]);
    setQuota(q);
    setPremiumState(p);
  }, []);

  useEffect(() => {
    refresh();
    // Also try to sync with backend in the background.
    refreshRemote();
  }, [refresh, refreshRemote]);

  const registerCalculation = useCallback(async () => {
    // Premium users don't consume the quota.
    if (premium.active) return;
    const next = await incrementQuota();
    setQuota(next);
  }, [premium.active]);

  const togglePremiumMock = useCallback(async (active: boolean) => {
    const next = await setPremium(active);
    setPremiumState(next);
  }, []);

  const remainingLeft = _remaining(quota);
  const canCompute = premium.active || remainingLeft > 0;

  return {
    state: {
      quota,
      remaining: remainingLeft,
      premium,
      canCompute,
    },
    refresh,
    refreshRemote,
    registerCalculation,
    togglePremiumMock,
  };
}

export { FREE_DAILY_LIMIT };
