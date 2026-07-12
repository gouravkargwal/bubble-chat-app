"use client";

import React from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { StatusDot } from "@/components/Logo";
import { EMAILS } from "@/app/constants";

const EASE_OUT = [0.16, 1, 0.3, 1] as const;

const sections = [
  {
    title: "1. Who We Are",
    content:
      "Cookd provides a mobile application and related services for AI-assisted dating conversation support.",
  },
  {
    title: "2. Information We Collect",
    bullets: [
      "Account data (for example: name, email, sign-in provider identifiers).",
      "Usage and preferences (settings, feature usage, in-app analytics events).",
      "Content you submit (text, images, screenshots submitted for AI processing).",
      "Device and technical data (device type, OS, app version, crash diagnostics).",
      "Purchase data (subscription status and store transaction identifiers).",
    ],
  },
  {
    title: "3. How We Use Information",
    content:
      "We use data to operate and improve the app, personalize features, process subscriptions, secure services, comply with legal obligations, and provide support communications.",
  },
  {
    title: "4. AI Processing",
    content:
      "When you use AI features, we and our service providers process submitted input to generate outputs. We do not guarantee AI outputs are always accurate or suitable for every context.",
  },
  {
    title: "5. Sharing",
    content:
      "We may share data with service providers that support hosting, analytics, crash reporting, authentication, and billing; and with authorities when required by law.",
  },
  {
    title: "6. Retention",
    content:
      "We retain data as needed to provide services, comply with law, resolve disputes, and enforce agreements. You can request deletion by contacting us.",
  },
  {
    title: "7. Security",
    content:
      "We use reasonable safeguards, including encryption in transit, to protect data.",
  },
  {
    title: "8. Children",
    content:
      "Cookd is not directed to children under 13 (or higher minimum age where applicable).",
  },
  {
    title: "9. International Transfers",
    content:
      "Your information may be processed in countries outside your own, where data protection laws may differ.",
  },
  {
    title: "10. Changes to This Policy",
    content:
      "We may update this policy periodically. Updates will be posted on this page.",
  },
  {
    title: "11. Contact",
    content: `For privacy questions, contact: ${EMAILS.privacy}`,
  },
];

export default function PrivacyPage() {
  return (
    <>
      <Header />
      <main className="relative min-h-screen px-6 pt-28 pb-24">
        {/* Grid background */}
        <div
          className="absolute inset-0 opacity-[0.02] pointer-events-none"
          style={{
            backgroundImage:
              "linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)",
            backgroundSize: "60px 60px",
          }}
        />

        {/* Ambient glow */}
        <motion.div
          className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[600px] rounded-full pointer-events-none"
          style={{
            background:
              "radial-gradient(circle, rgba(255,0,60,0.04) 0%, transparent 70%)",
          }}
          animate={{ scale: [1, 1.1, 1], opacity: [0.2, 0.4, 0.2] }}
          transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
        />

        <div className="relative z-10 mx-auto max-w-3xl">
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: EASE_OUT }}
            className="mb-12 text-center"
          >
            <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-nothing-border bg-nothing-surface px-4 py-1.5 text-xs font-mono text-nothing-text-secondary tracking-wider">
              <StatusDot active />
              LEGAL
            </div>
            <h1 className="text-3xl sm:text-4xl md:text-5xl font-extrabold tracking-tight text-nothing-white mb-4">
              Privacy <span className="text-neon-red">Policy</span>
            </h1>
            <p className="text-sm text-nothing-text-secondary max-w-xl mx-auto leading-relaxed">
              Last updated: March 22, 2026 &bull; How we collect, use, and
              protect your data.
            </p>
          </motion.div>

          {/* Sections */}
          <div className="space-y-10">
            {sections.map((section, i) => (
              <motion.section
                key={section.title}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{
                  delay: 0.3 + i * 0.04,
                  duration: 0.5,
                  ease: EASE_OUT,
                }}
              >
                <h2 className="text-lg font-bold text-nothing-white mb-2">
                  {section.title}
                </h2>
                {section.content && (
                  <p className="text-sm text-nothing-text-secondary leading-relaxed mb-2">
                    {section.content}
                  </p>
                )}
                {section.bullets && (
                  <ul className="ml-5 space-y-1.5">
                    {section.bullets.map((b, bi) => (
                      <li
                        key={bi}
                        className="text-sm text-nothing-text-secondary leading-relaxed list-disc marker:text-nothing-text-tertiary"
                      >
                        {b}
                      </li>
                    ))}
                  </ul>
                )}
              </motion.section>
            ))}
          </div>

          {/* Back link */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.8, duration: 0.5 }}
            className="mt-16 text-center"
          >
            <Link
              href="/#pricing"
              className="inline-flex items-center gap-2 text-xs font-mono text-nothing-text-tertiary hover:text-neon-red transition-colors underline underline-offset-4"
            >
              &larr; Back to Pricing
            </Link>
          </motion.div>
        </div>
      </main>
      <Footer />
    </>
  );
}
