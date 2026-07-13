import type { Metadata } from "next";
import { Space_Grotesk, DM_Sans } from "next/font/google";
import "./globals.css";
import { SITE, APP_URLS } from "./constants";
import { Suspense } from "react";
import { PostHogPageView } from "@/components/PostHogPageView";

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
        alt: `${SITE.name} — AI Dating Coach App Preview`,
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
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
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

        {/* JSON-LD structured data: WebApplication (AI Dating Coach) */}
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
      </head>
      <body className="min-h-full flex flex-col bg-brand-black text-brand-white font-sans">
        <Suspense fallback={null}>
          <PostHogPageView />
        </Suspense>
        {children}
      </body>
    </html>
  );
}
