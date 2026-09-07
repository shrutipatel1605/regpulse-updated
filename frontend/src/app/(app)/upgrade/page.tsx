"use client";

import { useCallback } from "react";
import { Btn, Icon } from "@/components/design/Primitives";
import { useCreateOrder, usePlans } from "@/hooks/useSubscriptions";
import { useAuthStore } from "@/stores/authStore";
import { useToast } from "@/components/design/Primitives";

export default function UpgradePage() {
  const toast = useToast();
  const { data: plansData, isLoading } = usePlans();
  const createOrder = useCreateOrder();
  const user = useAuthStore((s) => s.user);

  const handleUpgrade = useCallback(
    async (planId: string) => {
      try {
        const order = await createOrder.mutateAsync(planId);
        toast.push({
          tag: "ORDER",
          text: `Order ${order.order_id} created. Razorpay checkout would open here.`,
        });
      } catch {
        toast.push({ tag: "ERROR", text: "Failed to create order. Please try again." });
      }
    },
    [createOrder, toast],
  );

  // Live plans or editorial fallback
  const livePlans = plansData?.data ?? [];
  const plans =
    livePlans.length > 0
      ? livePlans.map((p) => ({
          id: p.id,
          name: p.name || p.id,
          price: p.amount_display || `₹${(p.amount_paise / 100).toLocaleString()}`,
          sub: p.duration_days === 30 ? "/ user / mo" : "/ user / yr",
          features: [
            `${p.credits.toLocaleString()} credits`,
            "Cited answers from RBI circulars",
            "PDF briefing exports",
            "Full question history",
          ],
          cta: "Upgrade",
          featured: false,
          current: false,
          canUpgrade: true,
        }))
      : [
          {
            id: "free",
            name: "Free",
            price: "₹0",
            sub: "forever",
            features: [
              "5 questions / mo",
              "Basic citations",
              "Single user",
            ],
            cta: "Current",
            featured: false,
            current: true,
            canUpgrade: false,
          },
          {
            id: "pro",
            name: "Pro",
            price: "₹2,400",
            sub: "/ user / mo",
            features: [
              "Unlimited questions",
              "PDF briefing exports",
              "Team learnings",
              "Debates & annotations",
              "Priority support",
            ],
            cta: "Upgrade",
            featured: true,
            current: false,
            canUpgrade: true,
          },
          {
            id: "enterprise",
            name: "Enterprise",
            price: "Custom",
            sub: "billed annually",
            features: [
              "Everything in Pro",
              "Workflow integrations",
              "Custom ingestion (internal memos)",
              "Dedicated reviewer",
              "SSO & SCIM",
              "DPDP deletion workflow",
            ],
            cta: "Talk to sales",
            featured: false,
            current: false,
            canUpgrade: false,
          },
        ];

  return (
    <div
      className="rp-route-fade"
      style={{ padding: "30px 24px 60px", maxWidth: 1100, margin: "0 auto" }}
    >
      {/* Editorial headline */}
      <div
        className="serif"
        style={{
          fontSize: 36,
          fontWeight: 400,
          letterSpacing: "-0.02em",
          lineHeight: 1.1,
          marginBottom: 10,
          textAlign: "center",
        }}
      >
        The fastest path from circular to board briefing.
      </div>
      <p
        className="serif"
        style={{
          fontSize: 16,
          fontStyle: "italic",
          color: "var(--ink-3)",
          textAlign: "center",
          marginBottom: 12,
        }}
      >
        Pro plans pay for themselves the first time you catch a 10 bps miss
        before the regulator does.
      </p>
      {user && (
        <div
          className="mono"
          style={{
            textAlign: "center",
            fontSize: 11,
            color: "var(--ink-4)",
            marginBottom: 36,
          }}
        >
          Current: {user.credit_balance} credits · {user.plan} plan
        </div>
      )}

      {isLoading && (
        <div style={{ padding: 40, textAlign: "center", color: "var(--ink-4)" }}>
          Loading plans...
        </div>
      )}

      {/* 3-col plan cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr 1fr",
          gap: 16,
        }}
      >
        {plans.map((p) => (
          <div
            key={p.id}
            className="panel"
            style={{
              padding: 24,
              position: "relative",
              borderColor: p.featured ? "var(--signal)" : "var(--line)",
              borderWidth: p.featured ? 2 : 1,
              borderStyle: "solid",
            }}
          >
            {/* MOST CHOSEN ribbon */}
            {p.featured && (
              <div
                className="mono"
                style={{
                  position: "absolute",
                  top: -10,
                  left: 20,
                  background: "var(--signal)",
                  color: "#fff",
                  padding: "3px 10px",
                  fontSize: 10,
                  fontWeight: 600,
                  borderRadius: 2,
                  letterSpacing: ".08em",
                }}
              >
                MOST CHOSEN
              </div>
            )}

            <div
              className="mono up"
              style={{ fontSize: 11, color: "var(--ink-4)", marginBottom: 8 }}
            >
              {p.name.toUpperCase()}
            </div>
            <div
              style={{
                display: "flex",
                alignItems: "baseline",
                gap: 6,
                marginBottom: 20,
              }}
            >
              <span
                className="tnum"
                style={{
                  fontSize: 38,
                  fontWeight: 600,
                  letterSpacing: "-0.02em",
                }}
              >
                {p.price}
              </span>
              <span
                className="mono"
                style={{ fontSize: 11, color: "var(--ink-4)" }}
              >
                {p.sub}
              </span>
            </div>
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: 8,
                marginBottom: 20,
              }}
            >
              {p.features.map((f) => (
                <div
                  key={f}
                  style={{
                    display: "flex",
                    gap: 8,
                    fontSize: 13,
                    color: "var(--ink-2)",
                    alignItems: "flex-start",
                  }}
                >
                  <Icon.Check
                    style={{
                      color: "var(--good)",
                      marginTop: 2,
                      flexShrink: 0,
                    }}
                  />{" "}
                  {f}
                </div>
              ))}
            </div>
            <Btn
              variant={p.featured ? "accent" : p.current ? "" : "primary"}
              disabled={p.current || createOrder.isPending}
              onClick={() => p.canUpgrade && handleUpgrade(p.id)}
              style={{
                width: "100%",
                justifyContent: "center",
                padding: "10px",
              }}
            >
              {createOrder.isPending ? "Processing..." : p.cta}
            </Btn>
          </div>
        ))}
      </div>
    </div>
  );
}
