export interface CommandExample {
  id: string;
  name: string;
  command: string;
  description: string;
  category: "automation" | "moderation" | "appeals" | "utility";
  steps: {
    sender: "user" | "docket";
    avatarUrl?: string;
    username: string;
    roleColor?: string;
    isBot?: boolean;
    timestamp: string;
    content: string;
    embed?: {
      title?: string;
      description?: string;
      color?: string; // Tailwind border color class or hex
      fields?: { name: string; value: string; inline?: boolean }[];
      footer?: string;
    };
  }[];
}

export interface DashboardTab {
  id: string;
  label: string;
  iconName: string; // Used to pick correct Lucide icon
}

export interface FeatureItem {
  id: string;
  title: string;
  description: string;
  iconName: string;
  category: "protection" | "management" | "analytics";
  badge?: string;
}

export interface PricingPlan {
  name: string;
  priceMonthly: number;
  priceYearly: number;
  description: string;
  features: string[];
  ctaText: string;
  isPopular?: boolean;
  color: string; // Accent color hex/class
}

export interface FAQItem {
  id: string;
  question: string;
  answer: string;
  category: "setup" | "security" | "ai" | "billing";
}

export interface TestimonialItem {
  id: string;
  quote: string;
  author: string;
  role: string;
  serverName: string;
  serverIconUrl?: string;
  memberCount: string;
}

export interface CaseLog {
  id: string;
  user: string;
  userId: string;
  moderator: string;
  action: "MUTE" | "KICK" | "BAN" | "WARN" | "RESOLVED";
  reason: string;
  timestamp: string;
  severity: "low" | "medium" | "high";
  aiSummary?: string;
}
