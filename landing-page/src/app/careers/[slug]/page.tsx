"use client";

import React from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { StatusDot } from "@/components/Logo";
import { AnimatedSection } from "@/components/Animations";
import { JOBS, SITE } from "@/app/constants";
import posthog from "posthog-js";

const EASE_OUT = [0.16, 1, 0.3, 1] as const;

export default function JobDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const resolved = React.use(params);
  const job = JOBS.find((j) => j.slug === resolved.slug);

  if (!job) {
    notFound();
  }

  const isOpen = job.status === "open";

  return (
    <>
      <head>
        <title>
          {job.title} — Careers | {SITE.name}
        </title>
        <meta
          name="description"
          content={`${job.title} at ${SITE.name}. ${job.description}`}
        />
      </head>
      <Header />
      <main className="min-h-screen pt-24">
        {/* ── Hero Section ── */}
        <section className="relative px-6 pb-8 pt-12 overflow-hidden">
          {/* Background grid */}
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
              transition={{ duration: 0.5, ease: EASE_OUT }}
            >
              {/* Badge */}
              <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-nothing-border bg-nothing-black/50 px-4 py-1.5 text-xs font-mono text-nothing-text-secondary tracking-wider">
                <StatusDot active={isOpen} />
                <span>{isOpen ? "NOW HIRING" : "COMING SOON"}</span>
              </div>

              {/* Title */}
              <h1 className="font-heading text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-nothing-white leading-[1.1]">
                {job.title.includes("Intern") ? (
                  <>
                    {job.title.split(" Intern")[0]}
                    <br />
                    <span className="text-neon-red">Intern</span>
                  </>
                ) : (
                  job.title
                )}
              </h1>

              {/* Stipend / Salary */}
              {(job.stipend || job.salary) && (
                <p className="mt-6 text-lg sm:text-xl font-semibold text-nothing-white/80">
                  {job.stipend || job.salary}{" "}
                  {job.stipend && (
                    <span className="text-sm font-mono text-nothing-text-secondary tracking-wider">
                      / MONTH
                    </span>
                  )}
                </p>
              )}

              {/* Meta chips */}
              <div className="mt-4 flex flex-wrap justify-center gap-2">
                <span className="inline-flex items-center gap-1 rounded-full border border-nothing-border px-3 py-1 text-xs font-mono text-nothing-text-secondary">
                  {job.location}
                </span>
                <span className="inline-flex items-center gap-1 rounded-full border border-nothing-border px-3 py-1 text-xs font-mono text-nothing-text-secondary">
                  {job.type}
                </span>
                <span className="inline-flex items-center gap-1 rounded-full border border-nothing-border px-3 py-1 text-xs font-mono text-nothing-text-secondary">
                  {job.department}
                </span>
              </div>

              <p className="mt-6 text-base leading-relaxed text-nothing-text-secondary max-w-xl mx-auto">
                {job.description}
              </p>
            </motion.div>
          </div>
        </section>

        {/* ── Role Details ── */}
        <section className="px-6 py-16 sm:py-20">
          <div className="mx-auto max-w-4xl space-y-16">
            {job.details.map((section) => (
              <AnimatedSection key={section.title} direction="up" delay={0.1}>
                <div>
                  <h2 className="font-heading text-xl sm:text-2xl font-bold text-nothing-white mb-6 tracking-tight">
                    {section.title}
                  </h2>
                  <ul className="space-y-3">
                    {section.items.map((item) => (
                      <li
                        key={item}
                        className="flex items-start gap-3 text-sm sm:text-base text-nothing-text-secondary leading-relaxed"
                      >
                        <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-neon-red shrink-0" />
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              </AnimatedSection>
            ))}
          </div>
        </section>

        {/* ── Application Section ── */}
        {isOpen && job.formUrl && (
          <section className="relative px-6 py-16 sm:py-20 overflow-hidden">
            {/* Background accent */}
            <div
              className="absolute inset-0 opacity-[0.02] pointer-events-none"
              style={{
                backgroundImage:
                  "linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)",
                backgroundSize: "60px 60px",
              }}
            />

            <div className="relative z-10 mx-auto max-w-3xl">
              <AnimatedSection direction="up" delay={0.1}>
                <div className="text-center mb-12">
                  <h2 className="font-heading text-2xl sm:text-3xl font-extrabold tracking-tight text-nothing-white mb-4">
                    The Application
                  </h2>
                  <p className="text-sm sm:text-base text-nothing-text-secondary leading-relaxed max-w-xl mx-auto">
                    We believe in seeing what you can make, not just what you can
                    write. Complete the task below and submit your CV along with
                    it via the Google Form. That&rsquo;s your application.
                  </p>
                </div>
              </AnimatedSection>

              {/* Task Card */}
              <AnimatedSection direction="up" delay={0.2}>
                <div className="rounded-xl border border-nothing-border bg-nothing-black/30 p-6 sm:p-8 mb-10">
                  <div className="flex items-center gap-3 mb-4">
                    <span className="inline-flex items-center justify-center h-8 w-8 rounded-full bg-neon-red/10 text-neon-red text-sm font-bold font-mono">
                      1
                    </span>
                    <h3 className="font-heading text-lg font-bold text-nothing-white">
                      The Task
                    </h3>
                  </div>
                  <p className="text-sm sm:text-base text-nothing-text-secondary leading-relaxed mb-4">
                    <strong className="text-nothing-white">
                      Download Cookd from Google Play,
                    </strong>{" "}
                    use it to generate a &ldquo;rizz&rdquo; response for a
                    conversation, and create a{" "}
                    <strong className="text-nothing-white">
                      15-second TikTok or Instagram Reel hook
                    </strong>{" "}
                    featuring the result. Show us how you&rsquo;d make this go
                    viral.
                  </p>
                  <div className="flex flex-wrap gap-2 mt-4">
                    <span className="inline-flex items-center gap-1 rounded-full border border-nothing-border px-3 py-1 text-xs font-mono text-nothing-text-secondary">
                      TikTok
                    </span>
                    <span className="inline-flex items-center gap-1 rounded-full border border-nothing-border px-3 py-1 text-xs font-mono text-nothing-text-secondary">
                      Instagram Reel
                    </span>
                    <span className="inline-flex items-center gap-1 rounded-full border border-nothing-border px-3 py-1 text-xs font-mono text-nothing-text-secondary">
                      Short-form Video
                    </span>
                    <span className="inline-flex items-center gap-1 rounded-full border border-nothing-border px-3 py-1 text-xs font-mono text-nothing-text-secondary">
                      Viral Hook
                    </span>
                  </div>
                </div>
              </AnimatedSection>

              {/* CTA Button */}
              <AnimatedSection direction="up" delay={0.3}>
                <div className="text-center">
                  <a
                    href={job.formUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={() =>
                      posthog.capture("careers_apply_clicked", {
                        slug: job.slug,
                        title: job.title,
                      })
                    }
                    className="inline-flex items-center gap-2 rounded-full bg-neon-red px-8 py-4 text-sm font-bold text-nothing-white transition-all duration-200 hover:bg-neon-red/90 hover:scale-[1.02] animate-neon-pulse"
                  >
                    <svg
                      className="h-4 w-4"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth={2}
                      aria-hidden="true"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M4 16v3a3 3 0 003 3h10a3 3 0 003-3v-3M16 12l-4 4m0 0l-4-4m4 4V4"
                      />
                    </svg>
                    Apply Now — Submit Your CV
                  </a>
                  <p className="mt-4 text-xs font-mono text-nothing-text-tertiary tracking-wider">
                    Upload your CV so we can get to know you better.
                  </p>
                </div>
              </AnimatedSection>
            </div>
          </section>
        )}

        {/* ── Coming Soon placeholder ── */}
        {!isOpen && (
          <section className="px-6 py-16 sm:py-20">
            <div className="mx-auto max-w-3xl text-center">
              <AnimatedSection direction="up" delay={0.1}>
                <div className="rounded-xl border border-dashed border-nothing-border/50 bg-nothing-black/10 p-8">
                  <h2 className="font-heading text-xl sm:text-2xl font-bold text-nothing-white mb-4">
                    This role isn&rsquo;t open yet
                  </h2>
                  <p className="text-sm sm:text-base text-nothing-text-secondary leading-relaxed mb-6 max-w-md mx-auto">
                    We&rsquo;re growing fast — check back soon for updates.
                  </p>
                  <span className="inline-flex items-center gap-1.5 rounded-full border border-nothing-border px-4 py-2 text-xs font-mono text-nothing-text-secondary">
                    Coming Soon
                  </span>
                </div>
              </AnimatedSection>
            </div>
          </section>
        )}

        {/* ── Back to Careers ── */}
        <section className="px-6 pb-16">
          <div className="mx-auto max-w-3xl text-center">
            <Link
              href="/careers"
              className="inline-flex items-center gap-1.5 text-sm text-nothing-text-secondary hover:text-nothing-white transition-colors duration-200"
            >
              <svg
                className="h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M15 19l-7-7 7-7"
                />
              </svg>
              View all positions
            </Link>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
