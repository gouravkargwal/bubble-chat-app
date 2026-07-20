"use client";

import React from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { StatusDot } from "@/components/Logo";
import { AnimatedSection } from "@/components/Animations";
import { JOBS, SITE } from "@/app/constants";
import posthog from "posthog-js";

const EASE_OUT = [0.16, 1, 0.3, 1] as const;

export default function CareersPage() {
  const openJobs = JOBS.filter((j) => j.status === "open");
  const comingSoonJobs = JOBS.filter((j) => j.status === "coming_soon");

  return (
    <>
      <head>
        <title>Careers — Join the Team | {SITE.name}</title>
        <meta
          name="description"
          content={`Join ${SITE.name} — we're hiring for internships and more. Task-based applications, no fluff.`}
        />
      </head>
      <Header />
      <main className="min-h-screen pt-24">
        {/* ── Hero Section ── */}
        <section className="relative px-6 pb-8 pt-12 overflow-hidden">
          {/* Background grid (same style as contact/careers pages) */}
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
                <StatusDot active />
                <span>NOW HIRING</span>
              </div>

              {/* Title */}
              <h1 className="font-heading text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-nothing-white leading-[1.1]">
                Join the
                <br />
                <span className="text-neon-red">Team</span>
              </h1>

              <p className="mt-6 text-base leading-relaxed text-nothing-text-secondary max-w-xl mx-auto">
                We build in public and hire the same way. Task-based
                applications — show us what you can make.
              </p>
            </motion.div>
          </div>
        </section>

        {/* ── Open Positions ── */}
        <section className="px-6 py-16 sm:py-20">
          <div className="mx-auto max-w-6xl">
            <AnimatedSection direction="up" delay={0.1}>
              <h2 className="font-heading text-2xl sm:text-3xl font-extrabold tracking-tight text-nothing-white mb-2">
                Open Positions
              </h2>
              <p className="text-sm text-nothing-text-secondary mb-10">
                {openJobs.length} role{openJobs.length !== 1 ? "s" : ""} — all
                remote, all task-based
              </p>
            </AnimatedSection>

            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {openJobs.map((job, i) => (
                <AnimatedSection key={job.slug} direction="up" delay={0.1 * i}>
                  <Link
                    href={`/careers/${job.slug}`}
                    onClick={() =>
                      posthog.capture("careers_card_clicked", {
                        slug: job.slug,
                        title: job.title,
                        status: "open",
                      })
                    }
                    className="group block rounded-xl border border-nothing-border bg-nothing-black/30 p-6 transition-all duration-200 hover:border-neon-red/40 hover:bg-nothing-black/50"
                  >
                    {/* Card top: dot + type */}
                    <div className="flex items-center justify-between mb-4">
                      <span className="inline-flex items-center gap-1.5 rounded-full border border-nothing-border px-3 py-1 text-xs font-mono text-nothing-text-secondary">
                        <span className="h-1.5 w-1.5 rounded-full bg-nothing-success" />
                        {job.type}
                      </span>
                      <span className="text-xs font-mono text-nothing-text-secondary">
                        {job.department}
                      </span>
                    </div>

                    {/* Title */}
                    <h3 className="font-heading text-lg font-bold text-nothing-white mb-2 group-hover:text-neon-red transition-colors duration-200">
                      {job.title}
                    </h3>

                    {/* Description */}
                    <p className="text-sm text-nothing-text-secondary leading-relaxed mb-4 line-clamp-3">
                      {job.description}
                    </p>

                    {/* Meta row */}
                    <div className="flex items-center justify-between text-xs font-mono text-nothing-text-secondary tracking-wider">
                      <span>{job.location}</span>
                      {job.stipend && <span>{job.stipend}</span>}
                    </div>
                  </Link>
                </AnimatedSection>
              ))}
            </div>
          </div>
        </section>

        {/* ── Coming Soon ── */}
        {comingSoonJobs.length > 0 && (
          <section className="px-6 pb-20">
            <div className="mx-auto max-w-6xl">
              <AnimatedSection direction="up" delay={0.2}>
                <h2 className="font-heading text-xl sm:text-2xl font-extrabold tracking-tight text-nothing-white mb-2">
                  Coming Soon
                </h2>
                <p className="text-sm text-nothing-text-secondary mb-10">
                  We're growing fast — more roles on the way.
                </p>
              </AnimatedSection>

              <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
                {comingSoonJobs.map((job, i) => (
                  <AnimatedSection
                    key={job.slug}
                    direction="up"
                    delay={0.1 * i}
                  >
                    <div className="block rounded-xl border border-dashed border-nothing-border/50 bg-nothing-black/10 p-6 opacity-60">
                      {/* Card top: dot + type */}
                      <div className="flex items-center justify-between mb-4">
                        <span className="inline-flex items-center gap-1.5 rounded-full border border-nothing-border/30 px-3 py-1 text-xs font-mono text-nothing-text-secondary">
                          <span className="h-1.5 w-1.5 rounded-full bg-nothing-text-tertiary" />
                          {job.type}
                        </span>
                        <span className="text-xs font-mono text-nothing-text-secondary">
                          {job.department}
                        </span>
                      </div>

                      {/* Title */}
                      <h3 className="font-heading text-lg font-bold text-nothing-white mb-2">
                        {job.title}
                      </h3>

                      {/* Description */}
                      <p className="text-sm text-nothing-text-secondary leading-relaxed mb-4 line-clamp-3">
                        {job.description}
                      </p>

                      {/* Coming Soon badge */}
                      <div className="inline-flex items-center gap-1.5 rounded-full border border-nothing-border/30 px-3 py-1 text-xs font-mono text-nothing-text-secondary">
                        Coming Soon
                      </div>
                    </div>
                  </AnimatedSection>
                ))}
              </div>
            </div>
          </section>
        )}

        {/* ── Back link ── */}
        <section className="px-6 pb-16">
          <div className="mx-auto max-w-3xl text-center">
            <Link
              href="/"
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
              Back to home
            </Link>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
