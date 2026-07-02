import type { Metadata } from "next";
import { Plus_Jakarta_Sans } from "next/font/google";
import "./globals.css";

const plusJakartaSans = Plus_Jakarta_Sans({
  variable: "--font-plus-jakarta",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
});

export const metadata: Metadata = {
  title: "Cookd — Your AI Dating Coach",
  description:
    "Cookd crafts personalized, high-impact opening lines and conversation strategies based on real-time chat analysis. Get the edge you need.",
  openGraph: {
    title: "Cookd — Your AI Dating Coach",
    description:
      "AI-powered dating coach that analyzes chats and crafts winning responses.",
    siteName: "Cookd",
    type: "website",
  },
  robots: {
    index: true,
    follow: true,
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
