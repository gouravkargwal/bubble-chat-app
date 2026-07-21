"use client";

import React from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { StatusDot } from "@/components/Logo";
import { EMAILS, PRICING } from "@/app/constants";

const EASE_OUT = [0.16, 1, 0.3, 1] as const;

const sections = [
  {
    title: "1. Acceptance of Terms",
    content:
      "By accessing or using Cookd (\u201Cthe Service\u201D), you agree to be bound by these Terms of Service. If you do not agree, do not use the Service. These terms apply to all users, including free-tier and subscription-based users.",
  },
  {
    title: "2. Subscription Plans (Crush Pass & Match Pro)",
    content: `Crush Pass (${PRICING.plans.crush.currency}${PRICING.plans.crush.price}${PRICING.plans.crush.period}) and Match Pro (${PRICING.plans.match.currency}${PRICING.plans.match.price}${PRICING.plans.match.period}) are recurring subscription plans. Subscriptions auto-renew unless cancelled at least 24 hours before the renewal date. Cancellations take effect at the end of the current billing period. No partial refunds are provided for unused portions of a billing cycle.`,
  },
  {
    title: "3. Credits & Usage Limits",
    content:
      "Each plan is allocated a monthly credit pool (exact number displayed at checkout). One AI generation consumes one credit. Screenshot processing, context analysis, and profile audits consume credits at the rates displayed in-app. Unused credits expire at the end of each billing period and do not transfer.",
  },
  {
    title: "4. User Conduct",
    content:
      "You agree not to: (a) use the Service for any illegal purpose or in violation of any laws; (b) attempt to reverse-engineer, scrape, or automate the AI generation pipeline; (c) resell or redistribute generated replies as a standalone service; (d) upload content that violates any third-party rights or contains hate speech, harassment, or explicit non-consensual material. Violation may result in immediate termination of your account without refund.",
  },
  {
    title: "5. Data Privacy & Storage",
    content:
      "Chat screenshots and context data are processed solely to generate replies. Uploaded images are not stored permanently; they are deleted within 24 hours of processing. We do not train our models on your data. For full details, see our Privacy Policy. By using the Service, you consent to this processing.",
  },
  {
    title: "6. Intellectual Property",
    content:
      "You retain full ownership of any content you upload. Generated replies are provided as suggestions; you are solely responsible for deciding whether and how to use them. The Service name, logo, branding, and underlying AI models are the intellectual property of Cookd and may not be reproduced without explicit written permission.",
  },
  {
    title: "7. Service Availability & Modifications",
    content:
      "We strive for 99.9% uptime but do not guarantee uninterrupted access. The Service may be temporarily suspended for maintenance, updates, or emergency fixes. We reserve the right to modify, suspend, or discontinue any feature at any time with reasonable notice.",
  },
  {
    title: "8. Limitation of Liability",
    content:
      "Cookd provides AI-generated suggestions for entertainment and conversational assistance. We do not guarantee specific outcomes (e.g., dates, replies, matches). To the maximum extent permitted by law, Cookd shall not be liable for any indirect, incidental, or consequential damages arising from your use of the Service. Our total liability is limited to the amount you paid in the 12 months preceding the claim.",
  },
  {
    title: "9. Refund Policy",
    content: `Subscription plan refunds are handled on a case-by-case basis within 7 days of purchase. To request a refund or report an issue, contact ${EMAILS.support} with your order ID and reason.`,
  },
  {
    title: "10. Termination",
    content:
      "We reserve the right to suspend or terminate accounts under the following circumstances:",
    bullets: [
      "Violation of any provision of these Terms, including User Conduct (Section 4).",
      "Engaging in abusive, fraudulent, or illegal activity through the Service.",
      "Failure to pay applicable fees for subscription plans.",
      "Attempting to circumvent usage limits, access controls, or payment requirements.",
      "Upon termination or revocation, your access to the Service ceases immediately. We will notify you via email of any termination and the reason for it. You may appeal by contacting ${EMAILS.support} within 14 days of the notice.",
    ],
  },
  {
    title: "11. Governing Law & Dispute Resolution",
    content:
      "These terms are governed by the laws of India. Any disputes arising from these terms shall be resolved exclusively in the courts of Mumbai, Maharashtra. For consumers in the EEA or UK, nothing in this section deprives you of the protection of mandatory consumer protection laws in your country of residence. We encourage you to contact us first to resolve any dispute informally before pursuing legal action.",
  },
  {
    title: "12. Changes to Terms",
    content:
      "We may update these Terms of Service at any time at our sole discretion. Changes take effect immediately upon posting to this page, except for material changes which will be communicated via email or in-app notification. Your continued use of the Service after any changes constitutes acceptance of the new terms. If you do not agree to a material change, you may stop using the Service. No refund will be provided for discontinuing use due to terms changes.",
  },
  {
    title: "13. Contact",
    content: `For questions about these terms or your account, reach out to ${EMAILS.legal}. We aim to respond within 48 hours.`,
  },
];

export default function TermsPage() {
  return (
    <>
      <head>
        <title>Terms of Service | Cookd</title>
        <meta
          name="description"
          content="Cookd terms of service — conditions for using our AI conversation assistant app, including subscriptions, refunds, and acceptable use."
        />
      </head>
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
              Terms of <span className="text-neon-red">Service</span>
            </h1>
            <p className="text-sm text-nothing-text-secondary max-w-xl mx-auto leading-relaxed">
              Last updated: July 2026 &bull; These terms govern your use of
              Cookd.
            </p>
          </motion.div>

          {/* TOC */}
          <motion.nav
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2, duration: 0.5, ease: EASE_OUT }}
            className="mb-12 rounded-xl border border-nothing-border bg-nothing-surface/50 p-5"
          >
            <p className="text-[10px] font-mono text-nothing-text-tertiary tracking-widest mb-3 uppercase">
              Table of Contents
            </p>
            <div className="grid gap-1.5 sm:grid-cols-2">
              {sections.map((s) => (
                <a
                  key={s.title}
                  href={`#${s.title
                    .toLowerCase()
                    .replace(/\s+/g, "-")
                    .replace(/[&.]/g, "")}`}
                  className="text-xs font-mono text-nothing-text-secondary hover:text-neon-red transition-colors underline underline-offset-2 decoration-nothing-border hover:decoration-neon-red"
                >
                  {s.title}
                </a>
              ))}
            </div>
          </motion.nav>

          {/* Sections */}
          <div className="space-y-10">
            {sections.map((section, i) => (
              <motion.section
                key={section.title}
                id={section.title
                  .toLowerCase()
                  .replace(/\s+/g, "-")
                  .replace(/[&.]/g, "")}
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
                <p className="text-sm text-nothing-text-secondary leading-relaxed mb-2">
                  {section.content}
                </p>
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
