"use client";

import React from "react";
import { motion } from "framer-motion";
import { StatusDot } from "./Logo";
import { AnimatedSection, StaggerContainer, StaggerItem, ScaleHover } from "./Animations";

const PLANS = [
  {
    id: "free",
    name: "Free",
    price: "0",
    currency: "",
    period: "forever",
    description: "Perfect for testing the waters.",
    credits: "2 / day",
    signupCredits: "+15 on signup",
    label: "STARTER",
    highlighted: false,
    features: [
      { text: "4 conversation directions", included: true },
      { text: "2 screenshots per request", included: true },
      { text: "10 context messages", included: true },
      { text: "Basic chat generation", included: true },
      { text: "Custom hints", included: false },
      { text: "Chemistry tracking", included: false },
      { text: "Coach reasoning", included: false },
      { text: "Photo audit", included: false },
    ],
  },
  {
    id: "crush",
    name: "Crush",
    price: "99",
    currency: "₹",
    period: "/week",
    description: "For when you want an edge.",
    credits: "60 credits",
    signupCredits: "",
    label: "POPULAR",
    highlighted: false,
    features: [
      { text: "7 conversation directions", included: true },
      { text: "5 screenshots per request", included: true },
      { text: "20 context messages", included: true },
      { text: "Custom hints (300 chars)", included: true },
      { text: "Chemistry tracking", included: true },
      { text: "Coach reasoning", included: true },
      { text: "Advanced languages", included: true },
      { text: "Photo audit (6 photos)", included: true },
    ],
  },
  {
    id: "match",
    name: "Match",
    price: "179",
    currency: "₹",
    period: "/month",
    description: "The sweet spot. Most users choose this.",
    credits: "150 credits",
    signupCredits: "",
    label: "BEST VALUE",
    highlighted: true,
    features: [
      { text: "All 9 conversation directions", included: true },
      { text: "5 screenshots per request", included: true },
      { text: "25 context messages", included: true },
      { text: "Custom hints (300 chars)", included: true },
      { text: "Chemistry tracking", included: true },
      { text: "Coach reasoning", included: true },
      { text: "Profile blueprints", included: true },
      { text: "Get Number / Ask Out", included: true },
    ],
  },
  {
    id: "rizz",
    name: "Rizz",
    price: "299",
    currency: "₹",
    period: "/month",
    description: "Maximum firepower. Unlimited potential.",
    credits: "250 credits",
    signupCredits: "",
    label: "ULTIMATE",
    highlighted: false,
    features: [
      { text: "All 9 conversation directions", included: true },
      { text: "7 screenshots per request", included: true },
      { text: "40 context messages", included: true },
      { text: "Custom hints (500 chars)", included: true },
      { text: "Chemistry tracking", included: true },
      { text: "Coach reasoning", included: true },
      { text: "Profile blueprints", included: true },
      { text: "Max limits on everything", included: true },
    ],
  },
];

function CheckIcon() {
  return (
    <svg
      className="h-3.5 w-3.5 flex-shrink-0 text-neon-red"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2.5}
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
    </svg>
  );
}

function MinusIcon() {
  return (
    <svg
      className="h-3.5 w-3.5 flex-shrink-0 text-nothing-text-tertiary"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 12h-15" />
    </svg>
  );
}

export function Pricing() {
  return (
    <section id="pricing" className="relative px-6 py-24 sm:py-32 overflow-hidden">
      {/* Background grid */}
      <div
        className="absolute inset-0 opacity-[0.02] pointer-events-none"
        style={{
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)",
          backgroundSize: "40px 40px",
        }}
      />

      {/* Section header */}
      <AnimatedSection className="mx-auto max-w-2xl text-center mb-16 sm:mb-20">
        <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-nothing-border bg-nothing-surface px-4 py-1.5 text-xs font-mono text-nothing-text-secondary tracking-wider">
          <StatusDot active />
          PRICING
        </div>
        <h2 className="text-3xl sm:text-4xl md:text-5xl font-extrabold tracking-tight text-nothing-white">
          One Plan. Three <span className="text-neon-red">Edges</span>.
        </h2>
        <p className="mt-4 text-nothing-text-secondary text-sm sm:text-base leading-relaxed max-w-lg mx-auto">
          Start free. Upgrade when you&apos;re ready to take control.
        </p>
      </AnimatedSection>

      {/* Pricing cards */}
      <StaggerContainer className="mx-auto max-w-7xl" staggerDelay={0.1}>
        <div className="grid gap-px bg-nothing-border sm:grid-cols-2 lg:grid-cols-4">
          {PLANS.map((plan) => (
            <StaggerItem key={plan.id} distance={60}>
              <ScaleHover scale={plan.highlighted ? 1.03 : 1.02}>
                <motion.div
                  className={`relative flex flex-col bg-nothing-black p-6 sm:p-8 transition-all duration-300 ${
                    plan.highlighted
                      ? "lg:-mt-4 lg:mb-[-1px] lg:pt-12 lg:pb-8 border-2 border-neon-red z-10"
                      : "border-0 hover:bg-nothing-surface"
                  }`}
                  animate={
                    plan.highlighted
                      ? {
                          boxShadow: [
                            "0 0 20px rgba(255,0,60,0.1)",
                            "0 0 40px rgba(255,0,60,0.2)",
                            "0 0 20px rgba(255,0,60,0.1)",
                          ],
                        }
                      : undefined
                  }
                  transition={
                    plan.highlighted
                      ? { duration: 3, repeat: Infinity, ease: "easeInOut" }
                      : undefined
                  }
                >
                  {/* Label */}
                  <span
                    className={`inline-block font-mono text-[10px] tracking-[0.15em] mb-4 ${
                      plan.highlighted ? "text-neon-red" : "text-nothing-text-tertiary"
                    }`}
                  >
                    [ {plan.label} ]
                  </span>

                  {/* Plan name */}
                  <h3 className="text-xl font-bold text-nothing-white mb-1">
                    {plan.name}
                  </h3>
                  <p className="text-xs text-nothing-text-secondary mb-4 leading-relaxed">
                    {plan.description}
                  </p>

                  {/* Price */}
                  <div className="mb-2">
                    <motion.span
                      className="text-3xl font-extrabold text-nothing-white inline-block"
                      initial={{ opacity: 0, scale: 0.5 }}
                      whileInView={{ opacity: 1, scale: 1 }}
                      viewport={{ once: true }}
                      transition={{ type: "spring", stiffness: 200, damping: 15, delay: 0.2 }}
                    >
                      {plan.currency}{plan.price}
                    </motion.span>
                    <span className="text-sm text-nothing-text-secondary ml-1 font-mono">
                      {plan.period}
                    </span>
                  </div>

                  {/* Credits */}
                  <div className="text-xs font-mono text-nothing-text-tertiary mb-6 tracking-wider">
                    <span className="text-nothing-white">{plan.credits}</span>
                    {plan.signupCredits && (
                      <>
                        <span className="mx-1.5">•</span>
                        <span className="text-nothing-success">{plan.signupCredits}</span>
                      </>
                    )}
                  </div>

                  {/* CTA — Open in Google Play */}
                  <motion.a
                    href="https://play.google.com/store/apps/details?id=com.cookd.mobile"
                    target="_blank"
                    rel="noopener noreferrer"
                    className={`mb-6 inline-flex items-center justify-center gap-1.5 rounded-full px-4 py-2 text-xs font-bold transition-all duration-200 ${
                      plan.highlighted
                        ? "bg-neon-red text-nothing-white hover:shadow-[0_0_20px_rgba(255,0,60,0.3)]"
                        : "border border-nothing-border text-nothing-white hover:bg-nothing-white/5"
                    }`}
                    whileHover={{ scale: 1.04 }}
                    whileTap={{ scale: 0.97 }}
                  >
                    <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 1.5H8.25A2.25 2.25 0 006 3.75v16.5a2.25 2.25 0 002.25 2.25h7.5A2.25 2.25 0 0018 20.25V3.75a2.25 2.25 0 00-2.25-2.25H13.5m-3 0V3h3V1.5m-3 0h3m-1.5 15v.01M12 12v7.5" />
                    </svg>
                    Google Play
                  </motion.a>

                  {/* Feature list */}
                  <ul className="space-y-3 mt-auto">
                    {plan.features.map((feature, fi) => (
                      <motion.li
                        key={feature.text}
                        initial={{ opacity: 0, x: -10 }}
                        whileInView={{ opacity: 1, x: 0 }}
                        viewport={{ once: true }}
                        transition={{ delay: 0.3 + fi * 0.05 }}
                        className="flex items-start gap-2.5"
                      >
                        {feature.included ? <CheckIcon /> : <MinusIcon />}
                        <span
                          className={`text-xs leading-relaxed ${
                            feature.included
                              ? "text-nothing-white"
                              : "text-nothing-text-tertiary"
                          }`}
                        >
                          {feature.text}
                        </span>
                      </motion.li>
                    ))}
                  </ul>
                </motion.div>
              </ScaleHover>
            </StaggerItem>
          ))}
        </div>
      </StaggerContainer>
    </section>
  );
}
