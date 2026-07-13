"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { StatusDot } from "@/components/Logo";
import { AnimatedSection, ScaleHover } from "@/components/Animations";
import { EMAILS } from "@/app/constants";
import posthog from "posthog-js";

const FAQ_ITEMS = [
  {
    q: "How do I get started?",
    a: "Download Cookd from Google Play, create an account, and connect your dating apps. Our AI analyzes your conversations in real-time and suggests winning responses.",
  },
  {
    q: "Is my chat data private?",
    a: "Absolutely. All conversations are encrypted end-to-end. We never store your messages after analysis, and we never share your data with third parties.",
  },
  {
    q: "Which dating apps are supported?",
    a: "Cookd works with all major dating platforms including Tinder, Hinge, Bumble, and more. Our AI adapts to any conversation style across any app.",
  },
  {
    q: "Can I cancel anytime?",
    a: "Yes. You can cancel your subscription at any time from your account settings. Your credits remain valid until the end of your billing period.",
  },
];

const SOCIAL_LINKS = [
  {
    name: "Twitter / X",
    href: "#",
    icon: (
      <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
        <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
      </svg>
    ),
  },
  {
    name: "Instagram",
    href: "#",
    icon: (
      <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
        <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 100 12.324 6.162 6.162 0 000-12.324zM12 16a4 4 0 110-8 4 4 0 010 8zm6.406-11.845a1.44 1.44 0 100 2.881 1.44 1.44 0 000-2.881z" />
      </svg>
    ),
  },
  {
    name: "TikTok",
    href: "#",
    icon: (
      <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
        <path d="M12.525.02c1.31-.02 2.61-.01 3.91-.02.08 1.53.63 3.09 1.75 4.17 1.12 1.11 2.7 1.62 4.24 1.79v4.03c-1.44-.05-2.89-.35-4.2-.97-.57-.26-1.1-.59-1.62-.93-.01 2.92.01 5.84-.02 8.75-.08 1.4-.54 2.79-1.35 3.94-1.31 1.92-3.58 3.17-5.91 3.21-1.43.08-2.86-.31-4.08-1.03-2.02-1.19-3.44-3.37-3.65-5.71-.02-.5-.03-1-.01-1.49.18-1.9 1.12-3.72 2.58-4.96 1.66-1.44 3.98-2.13 6.15-1.72.02 1.48-.04 2.96-.04 4.44-.99-.32-2.15-.23-3.02.37-.63.41-1.11 1.04-1.36 1.75-.21.51-.15 1.07-.14 1.61.24 1.64 1.82 3.02 3.5 2.87 1.12-.01 2.19-.66 2.77-1.61.19-.33.4-.67.41-1.06.1-1.79.06-3.57.07-5.36.01-4.03-.01-8.05.02-12.07z" />
      </svg>
    ),
  },
  {
    name: "Discord",
    href: "#",
    icon: (
      <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
        <path d="M20.317 4.3698a19.7913 19.7913 0 00-4.8851-1.5152.0741.0741 0 00-.0785.0371c-.211.3753-.4447.8648-.6083 1.2495-1.8447-.2762-3.68-.2762-5.4868 0-.1636-.3933-.4058-.8742-.6177-1.2495a.077.077 0 00-.0785-.037 19.7363 19.7363 0 00-4.8852 1.515.0699.0699 0 00-.0321.0277C.5334 9.0458-.319 13.5799.0992 18.0578a.0824.0824 0 00.0312.0561c2.0528 1.5076 4.0413 2.4228 5.9929 3.0294a.0777.0777 0 00.0842-.0276c.4616-.6304.8731-1.2952 1.226-1.9942a.076.076 0 00-.0416-.1057c-.6528-.2476-1.2743-.5495-1.8722-.8923a.077.077 0 01-.0076-.1277c.1258-.0943.2517-.1923.3718-.2914a.0743.0743 0 01.0776-.0105c3.9278 1.7933 8.18 1.7933 12.0614 0a.0739.0739 0 01.0785.0095c.1202.099.246.1981.3728.2924a.077.077 0 01-.0066.1276 12.2986 12.2986 0 01-1.873.8914.0766.0766 0 00-.0407.1067c.3604.698.7719 1.3628 1.225 1.9932a.076.076 0 00.0842.0286c1.961-.6067 3.9495-1.5219 6.0023-3.0294a.077.077 0 00.0313-.0552c.5004-5.177-.8382-9.6739-3.5485-13.6604a.061.061 0 00-.0312-.0286zM8.02 15.3312c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9555-2.4189 2.157-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.9555 2.4189-2.1569 2.4189zm7.9748 0c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9554-2.4189 2.1569-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.946 2.4189-2.1568 2.4189z" />
      </svg>
    ),
  },
];

type FormStatus = "idle" | "sending" | "sent" | "error";

export default function ContactPage() {
  const [status, setStatus] = useState<FormStatus>("idle");
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    subject: "",
    message: "",
  });

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    setFormData((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus("sending");

    try {
      // For MVP: sends via mailto fallback + logs to console
      // Replace this with your preferred form backend when ready
      const mailtoLink = `mailto:${EMAILS.hello}?subject=${encodeURIComponent(
        formData.subject || "Contact from Cookd"
      )}&body=${encodeURIComponent(
        `Name: ${formData.name}\nEmail: ${formData.email}\n\n${formData.message}`
      )}`;

      // Simulate brief delay for UX
      await new Promise((r) => setTimeout(r, 800));

      // Open default mail client
      window.location.href = mailtoLink;

      posthog.capture("contact_form_submitted", { subject: formData.subject });
      setStatus("sent");
      setFormData({ name: "", email: "", subject: "", message: "" });
    } catch {
      setStatus("error");
    }
  };

  return (
    <>
      <Header />
      <main className="min-h-screen pt-24">
        {/* ── Hero Section ── */}
        <section className="relative px-6 pb-8 pt-12 overflow-hidden">
          <div
            className="absolute inset-0 opacity-[0.03] pointer-events-none"
            style={{
              backgroundImage:
                "linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)",
              backgroundSize: "60px 60px",
            }}
          />
          <motion.div
            className="absolute top-1/3 left-1/4 w-80 h-80 rounded-full pointer-events-none"
            style={{
              background:
                "radial-gradient(circle, rgba(255,0,60,0.06) 0%, transparent 70%)",
            }}
            animate={{ scale: [1, 1.15, 1], opacity: [0.3, 0.5, 0.3] }}
            transition={{
              duration: 6,
              repeat: Infinity,
              ease: "easeInOut",
            }}
          />

          <div className="relative z-10 mx-auto max-w-3xl text-center">
            <motion.div
              initial={{ opacity: 0, y: -20, scale: 0.9 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] as const }}
              className="mb-6 inline-flex items-center gap-2 rounded-full border border-nothing-border bg-nothing-surface/80 backdrop-blur-sm px-4 py-1.5 text-xs font-mono text-nothing-text-secondary tracking-wider"
            >
              <StatusDot active />
              GET IN TOUCH
            </motion.div>

            <motion.h1
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{
                duration: 0.7,
                delay: 0.1,
                ease: [0.16, 1, 0.3, 1] as const,
              }}
              className="text-4xl sm:text-5xl md:text-6xl font-extrabold leading-[1.05] tracking-tight"
            >
              Got a Question?{" "}
              <span className="text-neon-red">We&apos;re Here</span>
              <br />
              to Help.
            </motion.h1>

            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{
                duration: 0.6,
                delay: 0.25,
                ease: [0.16, 1, 0.3, 1] as const,
              }}
              className="mx-auto mt-4 max-w-xl text-sm sm:text-base leading-relaxed text-nothing-text-secondary"
            >
              Have feedback, a bug report, or just want to say hi? Drop us a
              message and we&apos;ll get back to you within 24 hours.
            </motion.p>
          </div>
        </section>

        {/* ── Contact Form + Info ── */}
        <section className="relative px-6 py-8 sm:py-12">
          <div className="mx-auto max-w-5xl">
            <div className="grid md:grid-cols-5 gap-8 md:gap-12">
              {/* Form */}
              <motion.div
                className="md:col-span-3"
                initial={{ opacity: 0, x: -30 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{
                  duration: 0.7,
                  delay: 0.35,
                  ease: [0.16, 1, 0.3, 1] as const,
                }}
              >
                <div className="rounded-2xl border border-nothing-border bg-nothing-surface p-6 sm:p-8">
                  <div className="flex items-center gap-2 mb-6">
                    <StatusDot active />
                    <span className="text-xs font-mono text-nothing-text-tertiary tracking-wider">
                      CONTACT_FORM // ACTIVE
                    </span>
                  </div>

                  <AnimatePresence mode="wait">
                    {status === "sent" ? (
                      <motion.div
                        key="success"
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.95 }}
                        className="flex flex-col items-center justify-center py-12 text-center"
                      >
                        <div className="mb-4 rounded-full border border-nothing-success/30 bg-nothing-success/5 p-4">
                          <svg
                            className="h-8 w-8 text-nothing-success"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                            strokeWidth={2}
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                            />
                          </svg>
                        </div>
                        <h3 className="text-lg font-bold text-nothing-white mb-2">
                          Message Sent!
                        </h3>
                        <p className="text-sm text-nothing-text-secondary max-w-xs">
                          Your default email client should have opened. Just hit
                          send and we&apos;ll take it from there.
                        </p>
                        <button
                          onClick={() => setStatus("idle")}
                          className="mt-6 rounded-full border border-nothing-border px-6 py-2 text-xs font-bold text-nothing-white transition-all duration-200 hover:bg-nothing-white/5"
                        >
                          Send Another
                        </button>
                      </motion.div>
                    ) : (
                      <motion.form
                        key="form"
                        onSubmit={handleSubmit}
                        initial={{ opacity: 1 }}
                        exit={{ opacity: 0, scale: 0.95 }}
                        className="space-y-5"
                      >
                        <div className="grid sm:grid-cols-2 gap-5">
                          <div>
                            <label
                              htmlFor="name"
                              className="mb-1.5 block text-xs font-mono text-nothing-text-tertiary tracking-wider"
                            >
                              NAME
                            </label>
                            <input
                              type="text"
                              id="name"
                              name="name"
                              value={formData.name}
                              onChange={handleChange}
                              required
                              placeholder="Your name"
                              className="w-full rounded-lg border border-nothing-border bg-nothing-black px-4 py-2.5 text-sm text-nothing-white placeholder-nothing-text-tertiary outline-none transition-all duration-200 focus:border-neon-red/50 focus:ring-1 focus:ring-neon-red/20"
                            />
                          </div>
                          <div>
                            <label
                              htmlFor="email"
                              className="mb-1.5 block text-xs font-mono text-nothing-text-tertiary tracking-wider"
                            >
                              EMAIL
                            </label>
                            <input
                              type="email"
                              id="email"
                              name="email"
                              value={formData.email}
                              onChange={handleChange}
                              required
                              placeholder="you@example.com"
                              className="w-full rounded-lg border border-nothing-border bg-nothing-black px-4 py-2.5 text-sm text-nothing-white placeholder-nothing-text-tertiary outline-none transition-all duration-200 focus:border-neon-red/50 focus:ring-1 focus:ring-neon-red/20"
                            />
                          </div>
                        </div>

                        <div>
                          <label
                            htmlFor="subject"
                            className="mb-1.5 block text-xs font-mono text-nothing-text-tertiary tracking-wider"
                          >
                            SUBJECT
                          </label>
                          <input
                            type="text"
                            id="subject"
                            name="subject"
                            value={formData.subject}
                            onChange={handleChange}
                            required
                            placeholder="What's this about?"
                            className="w-full rounded-lg border border-nothing-border bg-nothing-black px-4 py-2.5 text-sm text-nothing-white placeholder-nothing-text-tertiary outline-none transition-all duration-200 focus:border-neon-red/50 focus:ring-1 focus:ring-neon-red/20"
                          />
                        </div>

                        <div>
                          <label
                            htmlFor="message"
                            className="mb-1.5 block text-xs font-mono text-nothing-text-tertiary tracking-wider"
                          >
                            MESSAGE
                          </label>
                          <textarea
                            id="message"
                            name="message"
                            value={formData.message}
                            onChange={handleChange}
                            required
                            rows={5}
                            placeholder="Tell us what's on your mind..."
                            className="w-full resize-none rounded-lg border border-nothing-border bg-nothing-black px-4 py-2.5 text-sm text-nothing-white placeholder-nothing-text-tertiary outline-none transition-all duration-200 focus:border-neon-red/50 focus:ring-1 focus:ring-neon-red/20"
                          />
                        </div>

                        <ScaleHover scale={1.02}>
                          <button
                            type="submit"
                            disabled={status === "sending"}
                            className="group inline-flex w-full items-center justify-center gap-2 rounded-full bg-neon-red px-8 py-3 text-sm font-bold text-nothing-white transition-all duration-300 hover:shadow-[0_0_30px_rgba(255,0,60,0.25)] disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            {status === "sending" ? (
                              <>
                                <svg
                                  className="h-4 w-4 animate-spin"
                                  fill="none"
                                  viewBox="0 0 24 24"
                                >
                                  <circle
                                    className="opacity-25"
                                    cx="12"
                                    cy="12"
                                    r="10"
                                    stroke="currentColor"
                                    strokeWidth="4"
                                  />
                                  <path
                                    className="opacity-75"
                                    fill="currentColor"
                                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                                  />
                                </svg>
                                Sending...
                              </>
                            ) : (
                              <>
                                <span>Send Message</span>
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
                                    d="M9 5l7 7-7 7"
                                  />
                                </svg>
                              </>
                            )}
                          </button>
                        </ScaleHover>

                        {status === "error" && (
                          <motion.p
                            initial={{ opacity: 0, y: 5 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="text-xs text-nothing-error text-center"
                          >
                            Something went wrong. Please email us directly at{" "}
                            {EMAILS.hello}
                          </motion.p>
                        )}
                      </motion.form>
                    )}
                  </AnimatePresence>
                </div>
              </motion.div>

              {/* Sidebar Info */}
              <motion.div
                className="md:col-span-2 space-y-6"
                initial={{ opacity: 0, x: 30 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{
                  duration: 0.7,
                  delay: 0.5,
                  ease: [0.16, 1, 0.3, 1] as const,
                }}
              >
                {/* Quick contact card */}
                <div className="rounded-2xl border border-nothing-border bg-nothing-surface p-6">
                  <h3 className="text-xs font-mono text-nothing-text-tertiary tracking-wider mb-4">
                    QUICK CONTACT
                  </h3>
                  <div className="space-y-4">
                    <a
                      href={`mailto:${EMAILS.hello}`}
                      className="flex items-center gap-3 group"
                    >
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-nothing-border bg-nothing-black group-hover:border-nothing-text-secondary transition-colors duration-200">
                        <svg
                          className="h-4 w-4 text-nothing-text-secondary"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                          strokeWidth={1.5}
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            d="M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75"
                          />
                        </svg>
                      </div>
                      <div>
                        <p className="text-xs text-nothing-text-tertiary font-mono tracking-wider">
                          EMAIL
                        </p>
                        <p className="text-sm text-nothing-white group-hover:text-neon-red transition-colors duration-200">
                          {EMAILS.hello}
                        </p>
                      </div>
                    </a>

                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-nothing-border bg-nothing-black">
                        <svg
                          className="h-4 w-4 text-nothing-text-secondary"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                          strokeWidth={1.5}
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 017.843 4.582M12 3a8.997 8.997 0 00-7.843 4.582m15.686 0A11.953 11.953 0 0112 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0121 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0112 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 013 12c0-1.605.42-3.113 1.157-4.418"
                          />
                        </svg>
                      </div>
                      <div>
                        <p className="text-xs text-nothing-text-tertiary font-mono tracking-wider">
                          RESPONSE TIME
                        </p>
                        <p className="text-sm text-nothing-white">
                          Within 24 hours
                        </p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Social links */}
                <div className="rounded-2xl border border-nothing-border bg-nothing-surface p-6">
                  <h3 className="text-xs font-mono text-nothing-text-tertiary tracking-wider mb-4">
                    FOLLOW US
                  </h3>
                  <div className="flex flex-wrap gap-3">
                    {SOCIAL_LINKS.map((link) => (
                      <a
                        key={link.name}
                        href={link.href}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-2 rounded-lg border border-nothing-border bg-nothing-black px-4 py-2.5 text-xs font-medium text-nothing-text-secondary hover:text-nothing-white hover:border-nothing-text-secondary transition-all duration-200"
                        title={link.name}
                      >
                        {link.icon}
                        <span className="hidden sm:inline">{link.name}</span>
                      </a>
                    ))}
                  </div>
                </div>

                {/* Status card */}
                <div className="rounded-2xl border border-nothing-border bg-nothing-surface p-6">
                  <div className="flex items-center gap-3">
                    <StatusDot active />
                    <div>
                      <p className="text-xs font-mono text-nothing-text-tertiary tracking-wider">
                        SYSTEM STATUS
                      </p>
                      <p className="text-sm text-nothing-success font-medium">
                        All systems operational
                      </p>
                    </div>
                  </div>
                </div>
              </motion.div>
            </div>
          </div>
        </section>

        {/* ── FAQ Section ── */}
        <section className="relative px-6 py-16 sm:py-20">
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
              <div className="text-center mb-12">
                <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-nothing-border bg-nothing-surface/80 backdrop-blur-sm px-4 py-1.5 text-xs font-mono text-nothing-text-secondary tracking-wider">
                  <StatusDot active />
                  FAQ
                </div>
                <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-nothing-white">
                  Frequently Asked{" "}
                  <span className="text-neon-red">Questions</span>
                </h2>
                <p className="mt-3 text-sm text-nothing-text-secondary max-w-lg mx-auto">
                  Can&apos;t find what you&apos;re looking for? Reach out to us
                  directly.
                </p>
              </div>

              <div className="space-y-3">
                {FAQ_ITEMS.map((item, i) => (
                  <FAQItem
                    key={i}
                    question={item.q}
                    answer={item.a}
                    index={i}
                  />
                ))}
              </div>
            </AnimatedSection>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}

function FAQItem({
  question,
  answer,
  index,
}: {
  question: string;
  answer: string;
  index: number;
}) {
  const [open, setOpen] = useState(false);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-40px" }}
      transition={{
        duration: 0.5,
        delay: index * 0.1,
        ease: [0.16, 1, 0.3, 1] as const,
      }}
      className="rounded-xl border border-nothing-border bg-nothing-surface overflow-hidden"
    >
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left transition-colors duration-200 hover:bg-nothing-white/[0.02]"
      >
        <span className="text-sm font-medium text-nothing-white">
          {question}
        </span>
        <motion.svg
          animate={{ rotate: open ? 180 : 0 }}
          transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] as const }}
          className="h-4 w-4 shrink-0 text-nothing-text-tertiary"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M19 9l-7 7-7-7"
          />
        </motion.svg>
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            key="content"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] as const }}
            className="overflow-hidden"
          >
            <div className="px-5 pb-4 pt-0">
              <p className="text-sm leading-relaxed text-nothing-text-secondary">
                {answer}
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
