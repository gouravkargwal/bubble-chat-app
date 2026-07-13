// ── App URLs ──
const APP_DOMAIN = "cookdai.site";
export const APP_URLS = {
  googlePlay: "https://play.google.com/store/apps/details?id=com.cookd.mobile",
  iosWaitlist: `mailto:support@${APP_DOMAIN}?subject=iOS%20Waitlist`,
  website: `https://${APP_DOMAIN}`,
  ogImage: `https://${APP_DOMAIN}/og-image.png`,
  // PayU LTD checkout pages (relative — handled by Next.js routing)
  ltdSuccess: "/ltd/success",
  ltdFailure: "/ltd/failure",
} as const;

// ── API URLs ──
// BASE_URL is just the origin without any path suffix.
// All endpoints append their full path including /api/v1/ prefix.
export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export const API_URLS = {
  leadMagnet: `${API_BASE_URL}/api/v1/public/lead-magnet/generate`,
  ltdCreateOrder: `${API_BASE_URL}/api/v1/billing/ltd/create-order`,
  ltdBannerConfig: `${API_BASE_URL}/api/v1/billing/ltd/banner-config`,
} as const;

// ── Social Links ──
// Update these when you create official accounts.
export const SOCIAL_LINKS = {
  twitter: "#",
  instagram: "#",
  tiktok: "#",
  discord: "#",
} as const;

// ── Email Addresses ──
// All emails use cookdai.site domain. Update the domain part when you change
// your primary domain.
const EMAIL_DOMAIN = "cookdai.site";
export const EMAILS = {
  support: `support@${EMAIL_DOMAIN}`,
  hello: `hello@${EMAIL_DOMAIN}`,
  legal: `legal@${EMAIL_DOMAIN}`,
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
  // Title is the primary SERP text. Keep it ≤60 chars for desktop SERP.
  // The tagline + description go in the meta description for snippet.
  title:
    "Cookd — AI Dating Coach: Get Better Replies on Hinge, Bumble & Tinder",
  description:
    "AI dating coach that analyzes your chats and crafts winning replies in real-time. Get better responses on Hinge, Bumble, Tinder & more. Download on Google Play.",
} as const;
