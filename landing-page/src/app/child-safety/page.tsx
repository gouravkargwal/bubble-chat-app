"use client";

import React from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { StatusDot } from "@/components/Logo";

const EASE_OUT = [0.16, 1, 0.3, 1] as const;

export default function ChildSafetyPage() {
  return (
    <>
      <head>
        <title>Child Safety Standards | Cookd</title>
        <meta
          name="description"
          content="Cookd child safety standards and CSAE policy — our commitment to protecting minors on our platform."
        />
      </head>
      <Header />
      <main className="relative min-h-screen px-6 pt-28 pb-24">
        <div
          className="absolute inset-0 opacity-[0.02] pointer-events-none"
          style={{
            backgroundImage:
              "linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)",
            backgroundSize: "60px 60px",
          }}
        />

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
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: EASE_OUT }}
            className="mb-12 text-center"
          >
            <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-nothing-border bg-nothing-surface px-4 py-1.5 text-xs font-mono text-nothing-text-secondary tracking-wider">
              <StatusDot active />
              SAFETY
            </div>
            <h1 className="text-3xl sm:text-4xl md:text-5xl font-extrabold tracking-tight text-nothing-white mb-4">
              Child Safety <span className="text-neon-red">Standards</span>
            </h1>
            <p className="text-sm text-nothing-text-secondary max-w-xl mx-auto leading-relaxed">
              Last updated: July 15, 2026 &bull; Our commitment to protecting
              minors
            </p>
          </motion.div>

          <div className="space-y-10">
            <motion.section
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3, duration: 0.5, ease: EASE_OUT }}
            >
              <h2 className="text-lg font-bold text-nothing-white mb-2">
                1. Our Policy
              </h2>
              <p className="text-sm text-nothing-text-secondary leading-relaxed">
                Cookd has a zero-tolerance policy towards child sexual abuse and
                exploitation (CSAE). We prohibit any and all content, behaviour,
                or activity that involves the sexual abuse or exploitation of
                children. This includes but is not limited to child sexual abuse
                material (CSAM), grooming, sextortion, inappropriate
                communications with minors, and any other form of child
                exploitation.
              </p>
            </motion.section>

            <motion.section
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.35, duration: 0.5, ease: EASE_OUT }}
            >
              <h2 className="text-lg font-bold text-nothing-white mb-2">
                2. Age Restriction
              </h2>
              <p className="text-sm text-nothing-text-secondary leading-relaxed">
                Cookd is strictly for users aged 18 and over. We use Google
                Sign-In for authentication, which requires users to be at least
                18 years old in their Google account. We do not knowingly allow
                individuals under the age of 18 to use our Service. If we become
                aware that a user is under 18, we will immediately terminate
                their account and delete all associated data.
              </p>
            </motion.section>

            <motion.section
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4, duration: 0.5, ease: EASE_OUT }}
            >
              <h2 className="text-lg font-bold text-nothing-white mb-2">
                3. Prohibited Conduct
              </h2>
              <p className="text-sm text-nothing-text-secondary leading-relaxed mb-2">
                The following are strictly prohibited on Cookd:
              </p>
              <ul className="ml-5 space-y-1.5">
                <li className="text-sm text-nothing-text-secondary leading-relaxed list-disc">
                  Any content depicting or describing sexual abuse of children
                </li>
                <li className="text-sm text-nothing-text-secondary leading-relaxed list-disc">
                  Communications with minors or attempting to identify minor
                  users
                </li>
                <li className="text-sm text-nothing-text-secondary leading-relaxed list-disc">
                  Grooming, sextortion, or any exploitative behaviour
                </li>
                <li className="text-sm text-nothing-text-secondary leading-relaxed list-disc">
                  Uploading, sharing, or generating child sexual abuse material
                  (CSAM)
                </li>
                <li className="text-sm text-nothing-text-secondary leading-relaxed list-disc">
                  Using the AI reply generation feature for any purpose
                  involving minors
                </li>
              </ul>
            </motion.section>

            <motion.section
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.45, duration: 0.5, ease: EASE_OUT }}
            >
              <h2 className="text-lg font-bold text-nothing-white mb-2">
                4. Reporting
              </h2>
              <p className="text-sm text-nothing-text-secondary leading-relaxed mb-2">
                If you encounter any content or behaviour on Cookd that you
                believe involves child sexual abuse or exploitation, or if you
                suspect a user is a minor, please report it immediately:
              </p>
              <ul className="ml-5 space-y-1.5">
                <li className="text-sm text-nothing-text-secondary leading-relaxed list-disc">
                  <strong>Email:</strong>{" "}
                  <a
                    href="mailto:safety@cookdai.site"
                    className="text-[#FF003C] underline"
                  >
                    safety@cookdai.site
                  </a>
                </li>
                <li className="text-sm text-nothing-text-secondary leading-relaxed list-disc">
                  <strong>In-app reporting:</strong> Use the in-app support
                  channel
                </li>
                <li className="text-sm text-nothing-text-secondary leading-relaxed list-disc">
                  <strong>Law enforcement:</strong> Contact your local law
                  enforcement agency immediately
                </li>
                <li className="text-sm text-nothing-text-secondary leading-relaxed list-disc">
                  <strong>NCMEC:</strong> Reports can also be made to the
                  National Center for Missing & Exploited Children at{" "}
                  <a
                    href="https://report.cybertip.org"
                    className="text-[#FF003C] underline"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    report.cybertip.org
                  </a>
                </li>
              </ul>
            </motion.section>

            <motion.section
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5, duration: 0.5, ease: EASE_OUT }}
            >
              <h2 className="text-lg font-bold text-nothing-white mb-2">
                5. Enforcement
              </h2>
              <p className="text-sm text-nothing-text-secondary leading-relaxed">
                Upon receiving a valid report of CSAE or underage use, we will:
              </p>
              <ul className="ml-5 space-y-1.5 mt-2">
                <li className="text-sm text-nothing-text-secondary leading-relaxed list-disc">
                  Immediately terminate the offending account
                </li>
                <li className="text-sm text-nothing-text-secondary leading-relaxed list-disc">
                  Permanently delete all associated data
                </li>
                <li className="text-sm text-nothing-text-secondary leading-relaxed list-disc">
                  Report the incident to the appropriate law enforcement
                  authorities
                </li>
                <li className="text-sm text-nothing-text-secondary leading-relaxed list-disc">
                  Ban the user's device ID and Google account from future access
                </li>
                <li className="text-sm text-nothing-text-secondary leading-relaxed list-disc">
                  Cooperate fully with law enforcement investigations
                </li>
              </ul>
            </motion.section>

            <motion.section
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.55, duration: 0.5, ease: EASE_OUT }}
            >
              <h2 className="text-lg font-bold text-nothing-white mb-2">
                6. Contact Information
              </h2>
              <p className="text-sm text-nothing-text-secondary leading-relaxed">
                For child safety concerns or questions about these standards,
                contact our safety team:
              </p>
              <p className="text-sm text-nothing-text-secondary leading-relaxed mt-2">
                <strong>Email:</strong>{" "}
                <a
                  href="mailto:safety@cookdai.site"
                  className="text-[#FF003C] underline"
                >
                  safety@cookdai.site
                </a>
              </p>
            </motion.section>
          </div>

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
              &larr; Back to Home
            </Link>
          </motion.div>
        </div>
      </main>
      <Footer />
    </>
  );
}
