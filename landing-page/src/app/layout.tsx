import type { Metadata } from "next";
import { Plus_Jakarta_Sans } from "next/font/google";
import "./globals.css";

const plusJakartaSans = Plus_Jakarta_Sans({
  variable: "--font-plus-jakarta",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
});

export const metadata: Metadata = {
  title:
    "Cookd — AI Dating Coach: Get Better Replies on Hinge, Bumble & Tinder",
  description:
    "AI dating coach that analyzes your chats and crafts winning replies in real-time. Get better responses on Hinge, Bumble, Tinder & more. Download on Google Play.",
  openGraph: {
    title:
      "Cookd — AI Dating Coach: Get Better Replies on Hinge, Bumble & Tinder",
    description:
      "AI dating coach that analyzes your chats and crafts winning replies in real-time. Get better responses on Hinge, Bumble, Tinder & more.",
    siteName: "Cookd",
    type: "website",
    url: "https://cookd.app",
    locale: "en_US",
    images: [
      {
        url: "https://cookd.app/og-image.png",
        width: 1200,
        height: 630,
        alt: "Cookd — AI Dating Coach",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title:
      "Cookd — AI Dating Coach: Get Better Replies on Hinge, Bumble & Tinder",
    description:
      "AI dating coach that analyzes chats and crafts winning replies in real-time. Get better responses on Hinge, Bumble, Tinder & more. Download on Google Play.",
    images: ["https://cookd.app/og-image.png"],
    site: "@cookd_app",
  },
  icons: {
    icon: "/logo.svg",
  },
  robots: {
    index: true,
    follow: true,
  },
  verification: {
    google: "YOUR_GOOGLE_VERIFICATION_CODE", // Replace with actual verification code
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${plusJakartaSans.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-nothing-black text-nothing-white font-sans">
        {children}
      </body>
    </html>
  );
}
