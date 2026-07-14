import type { Metadata } from "next";
import { Space_Grotesk, DM_Sans } from "next/font/google";
import "./globals.css";
import { SITE, APP_URLS } from "./constants";
import { Suspense } from "react";
import { PostHogPageView } from "@/components/PostHogPageView";
import { WebVitalsReporter } from "@/components/WebVitalsReporter";
import { ClerkProvider } from "@clerk/nextjs";

const spaceGrotesk = Space_Grotesk({
  variable: "--font-heading",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const dmSans = DM_Sans({
  variable: "--font-sans",
  subsets: ["latin"],
  weight: ["400", "500", "700"],
});

const siteName = SITE.name;

export const metadata: Metadata = {
  title: {
    default: SITE.title,
    template: `%s | ${siteName}`,
  },
  description: SITE.description,
  metadataBase: new URL(APP_URLS.website),
  alternates: {
    canonical: "/",
    languages: {
      en: "/",
      "en-IN": "/",
    },
  },
  keywords: [
    "AI dating coach",
    "dating app replies",
    "Hinge reply generator",
    "Bumble chat assistant",
    "Tinder opener",
    "AI wingman",
    "dating profile help",
    "better dating responses",
    "free AI dating coach",
    "Cookd",
  ],
  authors: [{ name: siteName }],
  creator: siteName,
  publisher: siteName,
  openGraph: {
    title: SITE.title,
    description: SITE.description,
    siteName,
    type: "website",
    url: APP_URLS.website,
    locale: "en_US",
    images: [
      {
        url: APP_URLS.ogImage,
        width: 1200,
        height: 630,
        alt: `${SITE.name} — AI Dating Coach App Preview — Get Better Replies on Hinge, Bumble & Tinder`,
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: SITE.title,
    description: SITE.description,
    images: [APP_URLS.ogImage],
    creator: "@cookdai",
  },
  icons: {
    icon: "/logo.svg",
    apple: "/logo.svg",
  },
  manifest: "/site.webmanifest",
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
  category: "technology",
  // Verify ownership in Google Search Console (replace with your code)
  // verification: { google: "YOUR_VERIFICATION_CODE" },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <ClerkProvider>
      <html
        lang="en"
        className={`${spaceGrotesk.variable} ${dmSans.variable} h-full antialiased`}
      >
        <head>
          {/* Theme color matches the dark brand background */}
          <meta name="theme-color" content="#0a0a0b" />
          <meta name="apple-mobile-web-app-capable" content="yes" />
          <meta name="apple-mobile-web-app-status-bar-style" content="black" />
          <meta name="apple-mobile-web-app-title" content={SITE.name} />

          {/* Preload hero image for faster LCP */}
          <link rel="preload" as="image" href="/logo.svg" />

          {/* JSON-LD: WebApplication (AI Dating Coach) */}
          <script
            type="application/ld+json"
            dangerouslySetInnerHTML={{
              __html: JSON.stringify({
                "@context": "https://schema.org",
                "@type": "WebApplication",
                name: siteName,
                url: APP_URLS.website,
                description: SITE.description,
                applicationCategory: "LifestyleApplication",
                operatingSystem: "Android",
                offers: {
                  "@type": "Offer",
                  price: "0",
                  priceCurrency: "USD",
                },
                author: {
                  "@type": "Organization",
                  name: siteName,
                },
              }),
            }}
          />

          {/* JSON-LD: BreadcrumbList */}
          <script
            type="application/ld+json"
            dangerouslySetInnerHTML={{
              __html: JSON.stringify({
                "@context": "https://schema.org",
                "@type": "BreadcrumbList",
                itemListElement: [
                  {
                    "@type": "ListItem",
                    position: 1,
                    name: "Home",
                    item: APP_URLS.website,
                  },
                ],
              }),
            }}
          />

          {/* JSON-LD: FAQPage (matches FAQ component questions) */}
          <script
            type="application/ld+json"
            dangerouslySetInnerHTML={{
              __html: JSON.stringify({
                "@context": "https://schema.org",
                "@type": "FAQPage",
                mainEntity: [
                  {
                    "@type": "Question",
                    name: "How does Cookd work?",
                    acceptedAnswer: {
                      "@type": "Answer",
                      text: "You share screenshots of your conversations, and our AI analyzes the chat dynamics, her personality cues, and the context. Then it generates multiple response options tailored to the situation — from playful to direct, depending on what's needed.",
                    },
                  },
                  {
                    "@type": "Question",
                    name: "Is my chat data private?",
                    acceptedAnswer: {
                      "@type": "Answer",
                      text: "Absolutely. Your conversations are encrypted in transit and at rest. We never store your screenshots longer than needed to generate a response, and we never share your chat data with anyone. You can delete your data anytime from settings.",
                    },
                  },
                  {
                    "@type": "Question",
                    name: "Which dating apps does Cookd support?",
                    acceptedAnswer: {
                      "@type": "Answer",
                      text: "Cookd works with any chat-based app — Hinge, Bumble, Tinder, Instagram DM, WhatsApp, Telegram, you name it. If you can screenshot it, Cookd can analyze it.",
                    },
                  },
                  {
                    "@type": "Question",
                    name: "Is there a free plan?",
                    acceptedAnswer: {
                      "@type": "Answer",
                      text: "Yes! Every user gets 2 free conversations per day (up to 60 per month) plus 10 bonus conversations on signup. No credit card needed. It's enough to try it out and see the difference.",
                    },
                  },
                  {
                    "@type": "Question",
                    name: "How accurate is the AI?",
                    acceptedAnswer: {
                      "@type": "Answer",
                      text: "Our AI has been trained on thousands of successful dating conversations. It picks up on subtle cues like tone, engagement level, and personality signals that most people miss. Users report a 2-3x improvement in reply rates.",
                    },
                  },
                  {
                    "@type": "Question",
                    name: "Can I cancel my subscription anytime?",
                    acceptedAnswer: {
                      "@type": "Answer",
                      text: "Yes. All paid plans are month-to-month or weekly with no lock-in. Cancel anytime from the app settings, and you'll keep access until the end of your billing period.",
                    },
                  },
                ],
              }),
            }}
          />
        </head>
        <body className="min-h-full flex flex-col bg-brand-black text-brand-white font-sans">
          {/* Noscript fallback for search crawlers and users without JS */}
          <noscript>
            <div
              style={{
                padding: "2rem",
                textAlign: "center",
                fontFamily: "system-ui, sans-serif",
              }}
            >
              <h1>{SITE.title}</h1>
              <p>{SITE.description}</p>
              <p>
                <a href={APP_URLS.googlePlay} rel="nofollow">
                  Download Cookd on Google Play
                </a>
              </p>
            </div>
          </noscript>

          <Suspense fallback={null}>
            <PostHogPageView />
          </Suspense>
          <WebVitalsReporter />
          {children}
        </body>
      </html>
    </ClerkProvider>
  );
}
