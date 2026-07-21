// ── App URLs ──
const APP_DOMAIN = "cookdai.site";
export const APP_URLS = {
  googlePlay: "https://play.google.com/store/apps/details?id=com.cookd.mobile",
  iosWaitlist: `mailto:support@${APP_DOMAIN}?subject=iOS%20Waitlist`,
  website: `https://${APP_DOMAIN}`,
} as const;

// ── API URLs ──
// BASE_URL is just the origin without any path suffix.
// All endpoints append their full path including /api/v1/ prefix.
export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export const API_URLS = {
  leadMagnet: `${API_BASE_URL}/api/v1/public/lead-magnet/generate`,
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
  type: "Full-time" | "Internship" | "Contract" | "Co-Founder";
  department: string;
  stipend?: string;
  salary?: string;
  publishedAt: string;
  status: "open" | "coming_soon";
  description: string;
  details: Array<{ title: string; items: string[] }>;
  formUrl?: string;
  taskInstructions?: string;
}

export const JOBS: Job[] = [
  {
    slug: "head-of-growth-co-founder",
    title: "Head of Growth (Co-Founder)",
    location: "Remote",
    type: "Co-Founder",
    department: "Growth",
    publishedAt: "2026-07-21",
    status: "open",
    description:
      "Day-zero co-founder role. Own user acquisition end-to-end — viral content, zero-dollar distribution, community building. No salary, massive equity stake.",
    details: [
      {
        title: "The Vibe",
        items: [
          "We are building Cookd AI \u2014 the ultimate AI-powered wingman for Gen Z",
          "Our product ensures users never run out of things to say, generating the perfect, witty responses for dating apps and dry texts",
          "We don\u2019t do corporate fluff, we don\u2019t care about your GPA, and we don\u2019t do boring marketing",
          "We are a fast-moving, high-contrast startup looking for a partner who lives and breathes internet culture",
        ],
      },
      {
        title: "The Deal",
        items: [
          "This is a day-zero co-founder role \u2014 no salary, no corporate safety net, no marketing budget",
          "You are trading short-term comfort for a massive equity stake in an early-stage consumer AI startup",
          "Standard 4-year vest with 1-year cliff",
          "If Cookd wins, you own a huge piece of the pie",
          "I handle the codebase; you handle the users",
        ],
      },
      {
        title: "What You\u2019ll Actually Do",
        items: [
          "Script, shoot, edit, and post highly engaging TikToks, Reels, and Shorts",
          "Craft a 3-second hook that stops a doom-scroller cold",
          "Hack our growth \u2014 QR codes on college campuses, leverage meme pages, hijack internet trends",
          "Speak the language of Gen Z and position Cookd as an edgy, must-have utility",
          "Your single metric is user acquisition",
        ],
      },
      {
        title: "Who You Are",
        items: [
          "Scrappy & Relentless \u2014 you don\u2019t need a budget to get 1,000 strangers to download an app",
          "Internet Native & Video First \u2014 you live on TikTok and you are dangerous with CapCut or Premiere",
          "Builder Mentality \u2014 you aren\u2019t looking for a 9-to-5, you want to build a company from the ground up",
          "You have the financial runway to work for equity right now",
        ],
      },
      {
        title: "How to Apply",
        items: [
          "We don\u2019t want a generic resume and we don\u2019t care about your degree",
          "We only care about what you can build",
          "Click the link below and complete the \u201cProof of Work\u201d challenge",
          "You will be asked to create a real 15-second TikTok/Reel hook for the app and tell us exactly how you would get our first 50 users this weekend with a $0 budget",
        ],
      },
    ],
    formUrl: CAREERS.mediaManagerForm,
    taskInstructions:
      "Download Cookd from Google Play, use it to generate a \"rizz\" response for a conversation, and create a 15-second TikTok or Instagram Reel hook featuring the result. Then tell us exactly how you would get our first 50 users this weekend with a $0 budget.",
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
  },
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
