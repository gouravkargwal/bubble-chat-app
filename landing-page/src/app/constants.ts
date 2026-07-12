// ── App URLs ──
export const APP_URLS = {
  googlePlay: "https://play.google.com/store/apps/details?id=com.cookd.mobile",
  iosWaitlist: "mailto:support@cookd.app?subject=iOS%20Waitlist",
  website: "https://cookd.app",
  ogImage: "https://cookd.app/og-image.png",
  // PayU LTD checkout pages (relative — handled by Next.js routing)
  ltdSuccess: "/ltd/success",
  ltdFailure: "/ltd/failure",
} as const;

// ── API URLs ──
// BASE_URL is just the origin (e.g. https://nonconscientious-annette-saddeningly.ngrok-free.dev)
// without any path.  All endpoints append their full path including /api/v1/ prefix.
export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export const API_URLS = {
  leadMagnet: `${API_BASE_URL}/api/v1/public/lead-magnet/generate`,
  ltdCreateOrder: `${API_BASE_URL}/api/v1/billing/ltd/create-order`,
  ltdBannerConfig: `${API_BASE_URL}/api/v1/billing/ltd/banner-config`,
} as const;

// ── Social Links ──
export const SOCIAL_LINKS = {
  twitter: "https://x.com/cookd_app",
  instagram: "https://instagram.com/cookd.app",
  tiktok: "https://tiktok.com/@cookd.app",
  discord: "https://discord.gg/cookd",
} as const;

// ── Email Addresses ──
export const EMAILS = {
  support: "support@cookd.app",
  hello: "hello@cookd.app",
  privacy: "tickets@cookd.p.tawk.email",
} as const;

// ── Pricing ──
export const PRICING = {
  plans: {
    crush: { price: 99, currency: "₹", period: "/week", credits: 50 },
    match: { price: 249, currency: "₹", period: "/month", credits: 150 },
    ltd: { price: 999, currency: "₹", period: "/forever" },
  },
  ltdSpots: { total: 1000, claimed: 342 },
} as const;

// ── Site Metadata ──
export const SITE = {
  name: "Cookd",
  tagline: "AI Dating Coach",
  title:
    "Cookd — AI Dating Coach: Get Better Replies on Hinge, Bumble & Tinder",
  description:
    "AI dating coach that analyzes your chats and crafts winning replies in real-time. Get better responses on Hinge, Bumble, Tinder & more. Download on Google Play.",
} as const;
