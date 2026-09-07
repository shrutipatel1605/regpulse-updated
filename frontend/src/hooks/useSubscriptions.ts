"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { useAuthStore } from "@/stores/authStore";

interface PlanOption {
  id: string;
  name: string;
  amount_paise: number;
  amount_display: string;
  credits: number;
  duration_days: number;
}

interface PlanInfo {
  plan: string;
  credit_balance: number;
  plan_expires_at: string | null;
  plan_auto_renew: boolean;
}

interface SubscriptionEvent {
  id: string;
  order_id: string | null;
  razorpay_event_id: string | null;
  plan: string;
  amount_paise: number;
  status: string;
  created_at: string;
}

/** Fetch available plans. */
export function usePlans() {
  return useQuery<{ success: boolean; data: PlanOption[] }>({
    queryKey: ["subscriptions", "plans"],
    queryFn: async () => {
      const { data } = await api.get("/subscriptions/plans");
      return data;
    },
    staleTime: 300_000,
  });
}

/** Fetch current plan info. */
export function usePlanInfo() {
  return useQuery<{ success: boolean; data: PlanInfo }>({
    queryKey: ["subscriptions", "plan"],
    queryFn: async () => {
      const { data } = await api.get("/subscriptions/plan");
      return data;
    },
    staleTime: 30_000,
  });
}

/** Fetch payment history. */
export function usePaymentHistory() {
  return useQuery<{ success: boolean; data: SubscriptionEvent[] }>({
    queryKey: ["subscriptions", "history"],
    queryFn: async () => {
      const { data } = await api.get("/subscriptions/history");
      return data;
    },
    staleTime: 30_000,
  });
}

/** Create a Razorpay order. */
export function useCreateOrder() {
  return useMutation<
    { success: boolean; order_id: string; amount_paise: number; plan: string },
    Error,
    string
  >({
    mutationFn: async (plan: string) => {
      const { data } = await api.post("/subscriptions/order", { plan });
      return data;
    },
  });
}

/** Verify payment after Razorpay checkout. */
export function useVerifyPayment() {
  const queryClient = useQueryClient();
  return useMutation<
    { success: boolean; credit_balance: number },
    Error,
    { razorpay_order_id: string; razorpay_payment_id: string; razorpay_signature: string }
  >({
    mutationFn: async (payload) => {
      const { data } = await api.post("/subscriptions/verify", payload);
      return data;
    },
    onSuccess: (data) => {
      const currentUser = useAuthStore.getState().user;
      if (currentUser) {
        useAuthStore.setState({
          user: { ...currentUser, credit_balance: data.credit_balance },
        });
      }
      queryClient.invalidateQueries({ queryKey: ["subscriptions"] });
    },
  });
}
