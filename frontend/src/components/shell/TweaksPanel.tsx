"use client";

import { useEffect, useState } from "react";
import { Icon } from "@/components/design/Primitives";
import { useThemeStore } from "@/stores/themeStore";

type Accent = "amber" | "emerald" | "crimson" | "cobalt";
const ACCENTS: Record<Accent, { light: string; dark: string }> = {
  amber:   { light: "#c25a11", dark: "#f0a24a" },
  emerald: { light: "#12734f", dark: "#6bd38a" },
  crimson: { light: "#a22020", dark: "#ef7d6d" },
  cobalt:  { light: "#1c4ebc", dark: "#7aa4de" },
};

function TweakRow<T extends string>({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: Array<[T, string]>;
  value: T;
  onChange: (v: T) => void;
}) {
  return (
    <div>
      <div
        className="mono up"
        style={{ fontSize: 10, color: "var(--ink-4)", marginBottom: 6 }}
      >
        {label}
      </div>
      <div style={{ display: "flex", gap: 4 }}>
        {options.map(([k, l]) => (
          <button
            key={k}
            onClick={() => onChange(k)}
            style={{
              flex: 1,
              fontSize: 11.5,
              padding: "5px 0",
              border: `1px solid ${value === k ? "var(--signal)" : "var(--line)"}`,
              background: value === k ? "var(--signal-bg)" : "var(--bg)",
              color: value === k ? "var(--signal-ink)" : "var(--ink-2)",
              borderRadius: 2,
              cursor: "pointer",
            }}
          >
            {l}
          </button>
        ))}
      </div>
    </div>
  );
}

export function TweaksPanel({ open, onClose }: { open: boolean; onClose: () => void }) {
  const theme = useThemeStore((s) => s.theme);
  const setTheme = useThemeStore((s) => s.setTheme);
  const [density, setDensity] = useState<"compact" | "normal">("compact");
  const [font, setFont] = useState<"editorial" | "memo">("editorial");
  const [accent, setAccent] = useState<Accent>("amber");

  useEffect(() => {
    const hex = ACCENTS[accent][theme === "dark" ? "dark" : "light"];
    document.documentElement.style.setProperty("--signal", hex);
  }, [accent, theme]);

  if (!open) return null;

  return (
    <div
      style={{
        position: "fixed",
        bottom: 20,
        right: 20,
        width: 260,
        background: "var(--panel)",
        border: "1px solid var(--line-2)",
        boxShadow: "var(--shadow-lg)",
        zIndex: 150,
        borderRadius: 4,
      }}
    >
      <div
        style={{
          padding: "10px 14px",
          borderBottom: "1px solid var(--line)",
          display: "flex",
          alignItems: "center",
          gap: 8,
        }}
      >
        <Icon.Settings style={{ color: "var(--signal)" }} />
        <span style={{ fontWeight: 600, fontSize: 12.5 }}>Tweaks</span>
        <div style={{ flex: 1 }} />
        <button
          onClick={onClose}
          style={{
            background: "transparent",
            border: "none",
            color: "var(--ink-3)",
            cursor: "pointer",
            padding: 2,
          }}
          aria-label="Close tweaks"
        >
          <Icon.Close />
        </button>
      </div>
      <div style={{ padding: 14, display: "flex", flexDirection: "column", gap: 14 }}>
        <TweakRow
          label="Theme"
          options={[
            ["light", "Light"],
            ["dark", "Dark"],
          ]}
          value={theme}
          onChange={(v) => setTheme(v as "light" | "dark")}
        />
        <TweakRow
          label="Accent"
          options={[
            ["amber", "Amber"],
            ["emerald", "Emerald"],
            ["crimson", "Crimson"],
            ["cobalt", "Cobalt"],
          ]}
          value={accent}
          onChange={setAccent}
        />
        <TweakRow
          label="Density"
          options={[
            ["compact", "Compact"],
            ["normal", "Normal"],
          ]}
          value={density}
          onChange={setDensity}
        />
        <TweakRow
          label="Answer style"
          options={[
            ["editorial", "Editorial"],
            ["memo", "Memo"],
          ]}
          value={font}
          onChange={setFont}
        />
      </div>
    </div>
  );
}
