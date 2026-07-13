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
    title: "1. Who We Are & Data Controller",
    content:
      "Cookd (\u201Cwe\u201D, \u201Cus\u201D, or \u201Cour\u201D) provides a mobile application and related services for AI-assisted dating conversation support. We are the data controller for personal information collected through the Service. For any privacy-related inquiries, you can reach us at the contact details in Section 15.",
  },
  {
    title: "2. Information We Collect",
    content:
      "We collect and process the following categories of personal information:",
    bullets: [
      "Account Data: Name, email address, and sign-in provider identifiers (e.g., Google ID) when you create an account.",
      "Usage Data: Settings, feature usage, in-app analytics events, page views, and interaction data collected via PostHog (a third-party analytics platform).",
      "Content You Submit: Text, images, and screenshots you upload for AI processing. These are processed in real-time and not stored permanently.",
      "Device & Technical Data: Device type, operating system version, app version, crash diagnostics, and IP address.",
      "Purchase Data: Subscription status, Lifetime Deal records, and store transaction identifiers (processed via Google Play and PayU).",
      "Communication Data: If you contact us via email or the contact form, we retain the content of your message and your email address to respond.",
    ],
  },
  {
    title: "3. Lawful Basis for Processing (GDPR)",
    content:
      "If you are located in the European Economic Area (EEA) or the United Kingdom, we process your personal information under the following lawful bases:",
    bullets: [
      "Contractual Necessity: To provide the Service and fulfill our obligations under our Terms of Service (account creation, AI processing, subscription management).",
      "Legitimate Interests: To improve the Service, ensure security, prevent abuse, and analyze usage patterns. We balance these interests against your rights and do not process where your interests override ours.",
      "Consent: For non-essential cookies and analytics tracking where required by applicable law. You may withdraw consent at any time by adjusting your device settings or contacting us.",
      "Legal Obligation: To comply with applicable laws, regulatory requirements, and legal processes.",
    ],
  },
  {
    title: "4. How We Use Information",
    content: "We use your information for the following purposes:",
    bullets: [
      "To operate, maintain, and improve the Service and its features.",
      "To process AI-generated replies based on content you submit.",
      "To manage your account, process subscriptions and Lifetime Deal purchases, and send transactional communications (e.g., payment confirmations, LTD code delivery).",
      "To monitor and analyze usage trends via PostHog for product improvement and crash detection.",
      "To enforce our Terms of Service, prevent fraud and abuse, and protect the rights and safety of our users and the public.",
      "To comply with legal obligations and respond to lawful requests from authorities.",
    ],
  },
  {
    title: "5. AI Processing & Data Used for Training",
    content:
      "When you use our AI features, the content you submit (screenshots, text, conversation context) is processed by our AI models to generate reply suggestions. This processing occurs in real-time. We do not use your submitted content to train or fine-tune our AI models. Uploaded screenshots and conversation data are not stored beyond what is necessary to generate a response and are deleted within 24 hours of processing. AI-generated outputs may not always be accurate or suitable for every context. You are solely responsible for deciding whether and how to use any suggested replies.",
  },
  {
    title: "6. How We Share Information",
    content:
      "We do not sell your personal information. We may share your data with the following categories of third parties:",
    bullets: [
      "Service Providers: Hosting infrastructure (cloud providers), analytics (PostHog), payment processing (Google Play, PayU), crash reporting, and email communications. These providers are contractually bound to process data only on our instructions and to implement appropriate security measures.",
      "Legal Authorities: When required by applicable law, legal process, or governmental request, or to protect our rights, property, or safety, or that of our users or the public.",
      "Business Transfers: In connection with a merger, acquisition, or sale of all or substantially all of our assets, your information may be transferred as part of that transaction. We will notify you via email and a prominent notice on the Service of any change in ownership or uses of your personal information.",
    ],
  },
  {
    title: "7. Data Retention",
    content:
      "We retain your personal information only as long as necessary to fulfill the purposes described in this policy, unless a longer retention period is required or permitted by law:",
    bullets: [
      "Account Data: Retained for the duration of your account plus 90 days after account deletion, after which it is anonymized or deleted.",
      "Usage & Analytics Data: Retained in aggregated form for 24 months. Individual-level analytics events are retained for 12 months.",
      "Submitted Content (Screenshots/Images): Deleted within 24 hours of AI processing. Not retained beyond the generation session.",
      "Purchase Data: Retained for 7 years to comply with tax and accounting obligations.",
      "Communication Records: Retained for 12 months after the last communication.",
      "You may request earlier deletion of your data by contacting us (see Section 15).",
    ],
  },
  {
    title: "8. Your Rights (GDPR, CCPA & Others)",
    content:
      "Depending on your jurisdiction, you may have the following rights regarding your personal information:",
    bullets: [
      "Right to Access: Request a copy of the personal data we hold about you.",
      "Right to Rectification: Request correction of inaccurate or incomplete data.",
      "Right to Deletion (\u201CRight to be Forgotten\u201D): Request deletion of your personal data, subject to legal retention obligations.",
      "Right to Restrict Processing: Request restriction of processing in certain circumstances.",
      "Right to Data Portability: Request a copy of your data in a structured, machine-readable format.",
      "Right to Object: Object to processing based on legitimate interests, including analytics and profiling.",
      "Right to Withdraw Consent: Where processing is based on consent, you may withdraw at any time without affecting the lawfulness of processing before withdrawal.",
      "Right to Non-Discrimination (CCPA): We will not discriminate against you for exercising any of your privacy rights.",
      "To exercise any of these rights, contact us at the email in Section 15. We will respond within 30 days. If you are in the EEA, you also have the right to lodge a complaint with your local data protection authority.",
    ],
  },
  {
    title: "9. Third-Party Analytics (PostHog)",
    content:
      "We use PostHog as our analytics platform to understand how users interact with the Service. PostHog collects usage data including page views, feature interactions, and error events. This data is hosted on PostHog\u2019s US-based servers. PostHog acts as a data processor on our behalf. You can view PostHog\u2019s privacy policy at https://posthog.com/privacy. To opt out of analytics tracking, you may use browser-level Do Not Track settings or contact us. Note that opting out may affect our ability to improve the Service based on usage data.",
  },
  {
    title: "10. Security",
    content:
      "We implement reasonable technical and organizational security measures to protect your personal information, including: encryption in transit (TLS 1.3), encryption at rest for stored data, access controls and authentication for production systems, regular security reviews, and incident response procedures. No method of transmission or storage is 100% secure. We cannot guarantee absolute security but will notify you of any data breach affecting your personal information within 72 hours of becoming aware of it, where required by applicable law.",
  },
  {
    title: "11. Children",
    content:
      "Cookd is not directed to individuals under the age of 13 (or the applicable age of digital consent in your jurisdiction, which may be up to 16 in certain EEA countries). We do not knowingly collect personal information from children. If we become aware that a child has provided us with personal information, we will delete it promptly. If you believe a child has provided us with personal data, please contact us immediately.",
  },
  {
    title: "12. International Data Transfers",
    content:
      "Your information may be transferred to and processed in countries outside your own, including India (where we are based) and the United States (where our analytics provider PostHog is based). When transferring data from the EEA or UK to countries not deemed adequate by the European Commission, we use appropriate transfer mechanisms (including Standard Contractual Clauses where applicable) to ensure your data receives an equivalent level of protection.",
  },
  {
    title: "13. Data Breach Notification",
    content:
      "In the event of a data breach that is likely to result in a risk to your rights and freedoms, we will notify you without undue delay and within 72 hours of becoming aware of the breach, where required by applicable law (including Article 34 of the GDPR). Notifications will be sent to the email address associated with your account.",
  },
  {
    title: "14. Changes to This Policy",
    content:
      "We may update this Privacy Policy at any time at our sole discretion. Changes take effect immediately upon posting. Material changes will be communicated via email or through a prominent notice on the Service. Your continued use of the Service after any changes constitutes acceptance of the updated policy. We encourage you to review this page periodically. The \u201CLast updated\u201D date at the top of this page indicates when this policy was last revised.",
  },
  {
    title: "15. Contact & Privacy Requests",
    content:
      "If you have any questions, concerns, or requests regarding this Privacy Policy or our data practices, please contact us. We aim to respond within 48 hours.",
    bullets: [
      `Email: ${EMAILS.legal}`,
      "Response Time: We will acknowledge your request within 48 hours and resolve it within 30 days.",
      "For GDPR-related inquiries, please use the subject line \u201CPrivacy Request\u201D when emailing us.",
      "If you are in the EEA or UK and believe your data protection rights have not been respected, you may lodge a complaint with your local supervisory authority.",
    ],
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
              Last updated: July 13, 2026 &bull; How we collect, use, and
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
