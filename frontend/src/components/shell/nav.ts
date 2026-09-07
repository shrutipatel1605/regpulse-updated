import { Icon } from "@/components/design/Primitives";

export interface NavItem {
  id: string;
  label: string;
  href: string;
  icon: (typeof Icon)[keyof typeof Icon];
  kbd?: string;
  badgeKey?: "updates" | "actions" | "debate";
  signal?: boolean;
  tag?: string;
}

export const NAV: NavItem[] = [
  { id: "dashboard", label: "Dashboard",    href: "/dashboard",    icon: Icon.Grid },
  { id: "ask",       label: "Ask",          href: "/ask",          icon: Icon.Ask,   kbd: "A" },
  { id: "updates",   label: "Updates",      href: "/updates",      icon: Icon.Pulse, badgeKey: "updates" },
  { id: "library",   label: "Library",      href: "/library",      icon: Icon.Book },
  { id: "actions",   label: "Action Items", href: "/action-items", icon: Icon.Flag,  badgeKey: "actions" },
  { id: "history",   label: "History",      href: "/history",      icon: Icon.Search },
  { id: "saved",     label: "Saved",        href: "/saved",        icon: Icon.Bookmark },
  { id: "learnings", label: "Learnings",    href: "/learnings",    icon: Icon.Spark, signal: true },
  { id: "debate",    label: "Debate",       href: "/debate",       icon: Icon.Users, badgeKey: "debate" },
];

export const NAV_BOTTOM: NavItem[] = [
  { id: "upgrade", label: "Upgrade", href: "/upgrade", icon: Icon.Plus },
  { id: "account", label: "Account", href: "/account", icon: Icon.Settings },
  { id: "admin",   label: "Admin",   href: "/admin",   icon: Icon.Settings, tag: "ADMIN" },
];
