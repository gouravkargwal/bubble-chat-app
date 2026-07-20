// ── App URLs ──
const APP_DOMAIN = "cookdai.site";
export const APP_URLS = {
  googlePlay: "https://play.google.com/store/apps/details?id=com.cookd.mobile",
  iosWaitlist: `mailto:support@${APP_DOMAIN}?subject=iOS%20Waitlist`,
  website: `https://${APP_DOMAIN}`,
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
export const SOCIAL_LINKS = {
  twitter: "https://x.com/trycookdai",
  instagram: "https://instagram.com/trycookdai",
  youtube: "https://youtube.com/@trycookdai",
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

// ── Careers / Hiring ──
export const CAREERS = {
  mediaManagerForm:
    process.env.NEXT_PUBLIC_CAREERS_MEDIA_MANAGER_FORM ||
    "https://forms.gle/gYeDAHN9GKELoJJJA",
} as const;

// ── Job Listings ──
export interface Job {
  slug: string;
  title: string;
  location: string;
  type: "Full-time" | "Internship" | "Contract";
  department: string;
  stipend?: string;
  salary?: string;
  publishedAt: string;
  status: "open" | "coming_soon";
  description: string;
  details: Array<{ title: string; items: string[] }>;
  formUrl?: string;
}

export const JOBS: Job[] = [
  {
    slug: "media-marketing-manager-intern",
    title: "Media Marketing Manager Intern",
    location: "Remote",
    type: "Internship",
    department: "Marketing",
    stipend: "₹5,000 / month",
    publishedAt: "2026-07-01",
    status: "open",
    description:
      "Own Cookd\u2019s social media presence across TikTok, Instagram Reels, and Twitter/X. Create viral hooks and grow organic reach among Gen Z/Millennial messaging app users.",
    details: [
      {
        title: "What You\u2019ll Do",
        items: [
          "Own Cookd\u2019s social media presence across TikTok, Instagram Reels, and Twitter/X",
          "Create viral hooks, trend-jack, and grow organic reach among Gen Z/Millennial messaging app users",
          "Collaborate with the product team to shape and amplify brand voice",
          "Analyze content performance and iterate on what works",
          "Produce short-form video content that drives app downloads",
        ],
      },
      {
        title: "Who You Are",
        items: [
          "Deeply fluent in meme culture, messaging app dynamics, and what makes content spread",
          "Comfortable on camera or can direct someone who is \u2014 you know what makes a 15-second hook land",
          "Data-informed: you look at retention curves, not just likes",
          "Resourceful and autonomous \u2014 this is a high-agency role at an early-stage startup",
          "Familiar with CapCut, DaVinci Resolve, or equivalent editing tools",
        ],
      },
      {
        title: "Details",
        items: [
          "Stipend: \u20B95,000 / month",
          "Duration: 3 months (renewable based on performance)",
          "Location: Remote \u2014 work from anywhere",
          "Task-based application \u2014 submit your CV along with the task",
          "Start date: Immediate",
        ],
      },
    ],
    formUrl: CAREERS.mediaManagerForm,
  },
  {
    slug: "software-engineering-intern",
    title: "Software Engineering Intern",
    location: "Remote",
    type: "Internship",
    department: "Engineering",
    stipend: "₹10,000 / month",
    publishedAt: "",
    status: "coming_soon",
    description:
      "Build and scale the AI-powered features that make Cookd magical. Work on real production systems from day one.",
    details: [
      {
        title: "What You\u2019ll Do",
        items: [
          "Build and maintain backend APIs in Python/FastAPI",
          "Contribute to our AI/ML pipeline for conversation analysis",
          "Write clean, tested, well-documented code that ships",
        ],
      },
      {
        title: "Who You Are",
        items: [
          "Proficient in Python and familiar with async programming",
          "Comfortable with SQL and database design",
          "Excited about AI/ML applications in consumer products",
        ],
      },
      {
        title: "Details",
        items: [
          "Stipend: \u20B910,000 / month",
          "Duration: 3 months (renewable)",
          "Location: Remote",
          "Start date: TBD",
        ],
      },
    ],
  },
  {
    slug: "product-design-intern",
    title: "Product Design Intern",
    location: "Remote",
    type: "Internship",
    department: "Design",
    stipend: "₹8,000 / month",
    publishedAt: "",
    status: "coming_soon",
    description:
      "Help shape the visual and interaction design of Cookd\u2019s mobile experience. Work closely with founders and engineering.",
    details: [
      {
        title: "What You\u2019ll Do",
        items: [
          "Design intuitive mobile interfaces for AI-powered chat features",
          "Create and maintain our design system components",
          "Conduct user research and translate insights into delightful interactions",
        ],
      },
      {
        title: "Who You Are",
        items: [
          "Strong portfolio in mobile UI/UX design",
          "Proficient in Figma and prototyping tools",
          "Eye for micro-interactions and motion design",
        ],
      },
      {
        title: "Details",
        items: [
          "Stipend: \u20B98,000 / month",
          "Duration: 3 months (renewable)",
          "Location: Remote",
          "Start date: TBD",
        ],
      },
    ],
  },
];

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
  tagline: "AI Conversation Assistant",
  // Title is the primary SERP text. Keep it ≤60 chars for desktop SERP.
  // The tagline + description go in the meta description for snippet.
  title:
    "Cookd — AI Conversation Assistant: Craft Better Replies on Any Chat App",
  description:
    "AI conversation assistant that analyzes your chats and crafts winning replies in 3 seconds. Get better responses across any messaging app. Download on Google Play.",
} as const;
