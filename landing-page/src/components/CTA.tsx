"use client";

import { motion } from "framer-motion";
import { StatusDot, Logo } from "./Logo";
import { AnimatedSection, ScaleHover } from "./Animations";
import { APP_URLS } from "@/app/constants";

export function CTA() {
  return (
    <section id="cta" className="relative px-6 py-24 sm:py-32">
      {/* Background grid */}
      <div
        className="absolute inset-0 opacity-[0.02] pointer-events-none"
        style={{
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)",
          backgroundSize: "40px 40px",
        }}
      />

      <div className="relative mx-auto max-w-3xl">
        <AnimatedSection>
          <motion.div
            className="relative rounded-2xl border border-nothing-border bg-nothing-surface p-8 sm:p-12 lg:p-16 text-center"
            initial={{ opacity: 0, scale: 0.95, y: 40 }}
            whileInView={{ opacity: 1, scale: 1, y: 0 }}
            viewport={{ once: true, margin: "-80px" }}
            transition={{
              duration: 0.8,
              ease: [0.16, 1, 0.3, 1],
            }}
          >
            {/* Decorative corner status */}
            <motion.div
              className="absolute top-4 right-4 flex items-center gap-1.5 text-[10px] font-mono text-nothing-text-tertiary tracking-wider"
              initial={{ opacity: 0 }}
              whileInView={{ opacity: 1 }}
              viewport={{ once: true }}
              transition={{ delay: 0.3 }}
            >
              <motion.div
                animate={{ opacity: [1, 0.2, 1] }}
                transition={{
                  duration: 1.5,
                  repeat: Infinity,
                  ease: "easeInOut",
                }}
              >
                <StatusDot active />
              </motion.div>
              <span>READY</span>
            </motion.div>

            {/* Logo */}
            <motion.div
              className="mb-6 flex justify-center"
              initial={{ scale: 0 }}
              whileInView={{ scale: 1 }}
              viewport={{ once: true }}
              transition={{
                type: "spring",
                stiffness: 200,
                damping: 15,
                delay: 0.1,
              }}
            >
              <Logo size={64} />
            </motion.div>

            {/* Heading */}
            <motion.h2
              className="text-3xl sm:text-4xl md:text-5xl font-extrabold tracking-tight text-nothing-white leading-tight"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{
                duration: 0.6,
                delay: 0.2,
                ease: [0.16, 1, 0.3, 1],
              }}
            >
              Get Your First Reply
              <br />
              <span className="text-neon-red">in 3 Seconds</span>
            </motion.h2>

            <motion.p
              className="mx-auto mt-4 max-w-lg text-sm sm:text-base leading-relaxed text-nothing-text-secondary"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{
                duration: 0.6,
                delay: 0.3,
                ease: [0.16, 1, 0.3, 1],
              }}
            >
              Get started free — no credit card required.
            </motion.p>

            {/* Referral callout */}
            <motion.div
              className="mt-8 mb-8 inline-flex flex-col sm:flex-row items-center gap-3 sm:gap-6 rounded-lg border border-nothing-border bg-nothing-black/50 px-5 py-3"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{
                duration: 0.6,
                delay: 0.4,
                ease: [0.16, 1, 0.3, 1],
              }}
            >
              <span className="text-xs font-mono text-nothing-text-tertiary tracking-wider">
                REFER & EARN
              </span>
              <div className="flex items-center gap-4 text-xs font-mono tracking-wider">
                <span className="text-nothing-text-secondary">
                  You get{" "}
                  <span className="text-nothing-success font-bold">
                    10 conversations
                  </span>
                </span>
                <motion.span
                  className="text-nothing-text-tertiary"
                  animate={{ x: [0, 3, 0] }}
                  transition={{
                    duration: 1.5,
                    repeat: Infinity,
                    ease: "easeInOut",
                  }}
                >
                  →
                </motion.span>
                <span className="text-nothing-text-secondary">
                  Friend gets{" "}
                  <span className="text-nothing-success font-bold">
                    5 conversations
                  </span>
                </span>
              </div>
            </motion.div>

            {/* CTA — Primary action: redirect to Google Play */}
            <motion.div
              className="flex flex-col sm:flex-row items-center justify-center gap-4"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{
                duration: 0.6,
                delay: 0.5,
                ease: [0.16, 1, 0.3, 1],
              }}
            >
              <ScaleHover scale={1.05}>
                <motion.a
                  href={APP_URLS.googlePlay}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="group inline-flex items-center gap-2 rounded-full bg-neon-red px-8 py-3.5 text-sm font-bold text-nothing-white transition-all duration-300"
                  animate={{
                    boxShadow: [
                      "0 0 20px rgba(255,0,60,0.15), 0 0 40px rgba(255,0,60,0.05)",
                      "0 0 30px rgba(255,0,60,0.25), 0 0 60px rgba(255,0,60,0.1)",
                      "0 0 20px rgba(255,0,60,0.15), 0 0 40px rgba(255,0,60,0.05)",
                    ],
                  }}
                  transition={{
                    duration: 3,
                    repeat: Infinity,
                    ease: "easeInOut",
                  }}
                  whileHover={{ boxShadow: "0 0 40px rgba(255,0,60,0.35)" }}
                >
                  <svg
                    className="h-4 w-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2.5}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M10.5 1.5H8.25A2.25 2.25 0 006 3.75v16.5a2.25 2.25 0 002.25 2.25h7.5A2.25 2.25 0 0018 20.25V3.75a2.25 2.25 0 00-2.25-2.25H13.5m-3 0V3h3V1.5m-3 0h3m-1.5 15v.01M12 12v7.5"
                    />
                  </svg>
                  <span>Get on Google Play</span>
                  <motion.svg
                    className="h-4 w-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2.5}
                    animate={{ x: [0, 3, 0] }}
                    transition={{
                      duration: 2,
                      repeat: Infinity,
                      ease: "easeInOut",
                    }}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M9 5l7 7-7 7"
                    />
                  </motion.svg>
                </motion.a>
              </ScaleHover>
              <ScaleHover scale={1.05}>
                <a
                  href="#pricing"
                  className="inline-flex items-center gap-2 rounded-full border border-nothing-border px-8 py-3.5 text-sm font-bold text-nothing-white transition-all duration-200 hover:bg-nothing-white/5"
                >
                  View Pricing
                </a>
              </ScaleHover>
            </motion.div>
          </motion.div>
        </AnimatedSection>
      </div>
    </section>
  );
}
