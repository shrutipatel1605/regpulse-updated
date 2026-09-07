"use client";

import { useState } from "react";
import { Avatar, Btn, Icon, Pill, useToast } from "@/components/design/Primitives";
import { RP_DATA } from "@/lib/mockData";
import { usePaymentHistory, usePlanInfo } from "@/hooks/useSubscriptions";
import { useAuthStore } from "@/stores/authStore";
import api from "@/lib/api";

export default function AccountPage() {
  const toast = useToast();
  const user = useAuthStore((s) => s.user);
  const clearAuth = useAuthStore((s) => s.clearAuth);
  const { data: planData, isLoading: planLoading } = usePlanInfo();
  const { data: historyData } = usePaymentHistory();

  // Auto-renew toggle state
  const [autoRenew, setAutoRenew] = useState<boolean | null>(null);
  const [autoRenewLoading, setAutoRenewLoading] = useState(false);

  // Deletion state
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleteOtp, setDeleteOtp] = useState("");
  const [deleteStep, setDeleteStep] = useState<"confirm" | "otp">("confirm");
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [deleteError, setDeleteError] = useState("");

  // Export state
  const [exportLoading, setExportLoading] = useState(false);

  // Derive auto-renew from plan data if not overridden
  const isAutoRenew = autoRenew ?? planData?.data.plan_auto_renew ?? true;

  if (!user) {
    return (
      <div style={{ padding: 40, textAlign: "center", color: "var(--ink-4)" }}>
        Please log in to view your account.
      </div>
    );
  }

  // --- Handlers (preserved from existing page) ---

  async function handleAutoRenewToggle() {
    setAutoRenewLoading(true);
    try {
      await api.patch("/subscriptions/auto-renew", {
        auto_renew: !isAutoRenew,
      });
      setAutoRenew(!isAutoRenew);
      toast.push({
        tag: "ACCOUNT",
        text: `Auto-renew ${!isAutoRenew ? "enabled" : "disabled"}.`,
      });
    } catch {
      toast.push({ tag: "ERROR", text: "Failed to update auto-renew." });
    } finally {
      setAutoRenewLoading(false);
    }
  }

  async function handleRequestDeletionOTP() {
    setDeleteLoading(true);
    setDeleteError("");
    try {
      await api.post("/account/request-deletion-otp");
      setDeleteStep("otp");
    } catch {
      setDeleteError("Failed to send OTP. Please try again.");
    } finally {
      setDeleteLoading(false);
    }
  }

  async function handleConfirmDeletion() {
    setDeleteLoading(true);
    setDeleteError("");
    try {
      await api.patch("/account/delete", { otp: deleteOtp });
      clearAuth();
      window.location.href = "/login";
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { error?: string } } })?.response?.data
          ?.error || "Deletion failed. Please try again.";
      setDeleteError(msg);
    } finally {
      setDeleteLoading(false);
    }
  }

  async function handleExportData() {
    setExportLoading(true);
    try {
      const { data } = await api.get("/account/export");
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `regpulse_export_${Date.now()}.json`;
      a.click();
      URL.revokeObjectURL(url);
      toast.push({ tag: "EXPORT", text: "Data export downloaded." });
    } catch {
      toast.push({ tag: "ERROR", text: "Export failed." });
    } finally {
      setExportLoading(false);
    }
  }

  // Display values — live user or mock
  const displayName = user.full_name || RP_DATA.user.name;
  const displayEmail = user.email || RP_DATA.user.email;
  const displayRole = user.designation || RP_DATA.user.role;
  const displayOrg = user.org_name || RP_DATA.user.org;
  const displayPlan = planData?.data.plan || user.plan || RP_DATA.user.plan;
  const displayCredits = planData?.data.credit_balance ?? user.credit_balance;
  const displayExpires = planData?.data.plan_expires_at
    ? new Date(planData.data.plan_expires_at).toLocaleDateString("en-IN", {
        day: "numeric",
        month: "short",
        year: "numeric",
      })
    : "Never (free plan)";

  // Team — mock for now
  const team = [
    { i: "PM", n: "Priya Menon", r: "CCO" },
    { i: "RK", n: "Raghav Krishnan", r: "Head, Risk" },
    { i: "AS", n: "Anjali Shah", r: "Treasury" },
    { i: "VN", n: "Vikram Nair", r: "Compliance Lead" },
    { i: "DK", n: "Divya Kapoor", r: "Capital Strategy" },
  ];

  return (
    <div
      className="rp-route-fade"
      style={{ padding: "20px 24px 60px", maxWidth: 900 }}
    >
      <h1
        className="serif"
        style={{ fontSize: 28, fontWeight: 400, marginBottom: 20 }}
      >
        Account
      </h1>

      {/* ── PROFILE ──────────────────────────────────────────────────── */}
      <div className="panel" style={{ padding: 20, marginBottom: 16 }}>
        <div className="tick" style={{ marginBottom: 14 }}>
          PROFILE
        </div>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "120px 1fr",
            gap: 10,
            fontSize: 13,
          }}
        >
          <div style={{ color: "var(--ink-4)" }}>Name</div>
          <div>{displayName}</div>
          <div style={{ color: "var(--ink-4)" }}>Email</div>
          <div className="mono">{displayEmail}</div>
          <div style={{ color: "var(--ink-4)" }}>Role</div>
          <div>{displayRole}</div>
          <div style={{ color: "var(--ink-4)" }}>Organisation</div>
          <div>{displayOrg}</div>
          <div style={{ color: "var(--ink-4)" }}>Plan</div>
          <div>
            <Pill tone="amber">{displayPlan.toUpperCase()}</Pill>
          </div>
          <div style={{ color: "var(--ink-4)" }}>Credits</div>
          <div className="mono tnum" style={{ fontWeight: 600 }}>
            {displayCredits}
          </div>
          <div style={{ color: "var(--ink-4)" }}>Expires</div>
          <div className="mono" style={{ fontSize: 12 }}>
            {displayExpires}
          </div>
          <div style={{ color: "var(--ink-4)" }}>Auto-Renew</div>
          <div>
            <button
              onClick={handleAutoRenewToggle}
              disabled={autoRenewLoading || planLoading}
              style={{
                position: "relative",
                display: "inline-flex",
                alignItems: "center",
                width: 40,
                height: 22,
                borderRadius: 11,
                background: isAutoRenew ? "var(--signal)" : "var(--line-2)",
                border: "none",
                cursor: "pointer",
                transition: "background .2s",
              }}
            >
              <span
                style={{
                  display: "block",
                  width: 16,
                  height: 16,
                  borderRadius: "50%",
                  background: "#fff",
                  transition: "transform .2s",
                  transform: isAutoRenew ? "translateX(20px)" : "translateX(3px)",
                }}
              />
            </button>
          </div>
        </div>
      </div>

      {/* ── TEAM ─────────────────────────────────────────────────────── */}
      <div className="panel" style={{ padding: 20, marginBottom: 16 }}>
        <div className="tick" style={{ marginBottom: 14 }}>
          TEAM · {team.length} MEMBERS
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {team.map((m) => (
            <div
              key={m.i}
              style={{ display: "flex", alignItems: "center", gap: 10 }}
            >
              <Avatar
                initials={m.i}
                size={26}
                tone={m.i === "PM" ? "signal" : "default"}
              />
              <div style={{ fontSize: 13, fontWeight: 500 }}>{m.n}</div>
              <div
                className="mono"
                style={{ fontSize: 10.5, color: "var(--ink-4)" }}
              >
                {m.r}
              </div>
              <div style={{ flex: 1 }} />
              <Btn size="sm" variant="ghost">
                Permissions
              </Btn>
            </div>
          ))}
        </div>
      </div>

      {/* ── PAYMENT HISTORY ──────────────────────────────────────────── */}
      {historyData && historyData.data.length > 0 && (
        <div className="panel" style={{ padding: 20, marginBottom: 16 }}>
          <div className="tick" style={{ marginBottom: 14 }}>
            PAYMENT HISTORY
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {historyData.data.map((event) => (
              <div
                key={event.id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                  padding: "8px 0",
                  borderBottom: "1px solid var(--line)",
                }}
              >
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 13, fontWeight: 500, textTransform: "capitalize" }}>
                    {event.plan}
                  </div>
                  <div
                    className="mono"
                    style={{ fontSize: 10.5, color: "var(--ink-4)" }}
                  >
                    {new Date(event.created_at).toLocaleDateString("en-IN", {
                      day: "numeric",
                      month: "short",
                      year: "numeric",
                    })}
                  </div>
                </div>
                <div
                  className="mono tnum"
                  style={{ fontSize: 13, fontWeight: 600 }}
                >
                  {"\u20b9"}
                  {(event.amount_paise / 100).toLocaleString()}
                </div>
                <Pill tone={event.status === "captured" ? "good" : "ghost"}>
                  {event.status.toUpperCase()}
                </Pill>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── DATA · DPDP COMPLIANCE ───────────────────────────────────── */}
      <div className="panel" style={{ padding: 20, marginBottom: 16 }}>
        <div className="tick" style={{ marginBottom: 14 }}>
          DATA · DPDP COMPLIANCE
        </div>
        <div
          style={{
            fontSize: 12.5,
            color: "var(--ink-3)",
            marginBottom: 12,
          }}
        >
          You have the right to export or delete your data at any time under the
          DPDP Act.
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <Btn onClick={handleExportData} disabled={exportLoading}>
            {exportLoading ? "Exporting..." : "Export my data"}
          </Btn>
          <Btn
            variant="ghost"
            style={{ color: "var(--bad)" }}
            onClick={() => {
              setShowDeleteModal(true);
              setDeleteStep("confirm");
              setDeleteOtp("");
              setDeleteError("");
            }}
          >
            Delete account
          </Btn>
        </div>
      </div>

      {/* ── Delete Account Modal ─────────────────────────────────────── */}
      {showDeleteModal && (
        <div
          onClick={() => setShowDeleteModal(false)}
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 90,
            background: "rgba(0,0,0,0.35)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              width: 480,
              background: "var(--panel)",
              border: "1px solid var(--line-2)",
              boxShadow: "var(--shadow-lg)",
              borderRadius: 4,
              overflow: "hidden",
            }}
          >
            <div
              style={{
                padding: "14px 18px",
                borderBottom: "1px solid var(--line)",
                display: "flex",
                alignItems: "center",
                gap: 10,
              }}
            >
              <Icon.Flag style={{ color: "var(--bad)" }} />
              <h3 style={{ fontSize: 14, fontWeight: 600 }}>Delete Account</h3>
              <div style={{ flex: 1 }} />
              <Btn
                variant="ghost"
                icon
                onClick={() => setShowDeleteModal(false)}
              >
                <Icon.Close />
              </Btn>
            </div>

            <div style={{ padding: 18 }}>
              {deleteStep === "confirm" ? (
                <>
                  <p
                    style={{
                      fontSize: 13,
                      color: "var(--ink-2)",
                      lineHeight: 1.5,
                      marginBottom: 16,
                    }}
                  >
                    This action is <strong>permanent and irreversible</strong>.
                    Your personal data will be anonymised, and your questions,
                    saved interpretations, and action items will be deleted. An
                    OTP will be sent to your email for verification.
                  </p>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "flex-end",
                      gap: 8,
                    }}
                  >
                    <Btn
                      variant="ghost"
                      onClick={() => setShowDeleteModal(false)}
                    >
                      Cancel
                    </Btn>
                    <Btn
                      variant="accent"
                      onClick={handleRequestDeletionOTP}
                      disabled={deleteLoading}
                      style={{
                        background: "var(--bad)",
                        borderColor: "var(--bad)",
                      }}
                    >
                      {deleteLoading ? "Sending OTP..." : "Send Verification OTP"}
                    </Btn>
                  </div>
                </>
              ) : (
                <>
                  <p
                    style={{
                      fontSize: 13,
                      color: "var(--ink-2)",
                      lineHeight: 1.5,
                      marginBottom: 12,
                    }}
                  >
                    Enter the 6-digit OTP sent to your email to confirm account
                    deletion.
                  </p>
                  <input
                    type="text"
                    maxLength={6}
                    value={deleteOtp}
                    onChange={(e) =>
                      setDeleteOtp(e.target.value.replace(/\D/g, ""))
                    }
                    placeholder="Enter OTP"
                    className="input"
                    style={{
                      textAlign: "center",
                      fontSize: 18,
                      letterSpacing: "0.3em",
                      marginBottom: 12,
                    }}
                  />
                  {deleteError && (
                    <div
                      style={{
                        fontSize: 12,
                        color: "var(--bad)",
                        marginBottom: 12,
                      }}
                    >
                      {deleteError}
                    </div>
                  )}
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "flex-end",
                      gap: 8,
                    }}
                  >
                    <Btn
                      variant="ghost"
                      onClick={() => setShowDeleteModal(false)}
                    >
                      Cancel
                    </Btn>
                    <Btn
                      variant="accent"
                      onClick={handleConfirmDeletion}
                      disabled={deleteLoading || deleteOtp.length !== 6}
                      style={{
                        background: "var(--bad)",
                        borderColor: "var(--bad)",
                      }}
                    >
                      {deleteLoading
                        ? "Deleting..."
                        : "Permanently Delete Account"}
                    </Btn>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
