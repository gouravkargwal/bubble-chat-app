"use client";

import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { StatusDot } from "./Logo";
import {
  AnimatedSection,
  StaggerContainer,
  StaggerItem,
  ScaleHover,
} from "./Animations";
import { LtdCheckoutModal } from "./LtdCheckoutModal";
import { APP_URLS, PRICING, API_URLS } from "@/app/constants";
import posthog from "posthog-js";

const PLANS = [
  {
    id: "crush",
    name: "Crush Pass",
    price: String(PRICING.plans.crush.price),
    currency: PRICING.plans.crush.currency,
    period: PRICING.plans.crush.period,
    description: "For when you need a quick, short-term edge.",
    credits: `${PRICING.plans.crush.credits} conversations / week`,
    label: "WEEKLY PASS",
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
    name: "Match Pro",
    price: String(PRICING.plans.match.price),
    currency: PRICING.plans.match.currency,
    period: PRICING.plans.match.period,
    description: "The standard blueprint for dating control.",
    credits: `${PRICING.plans.match.credits} conversations / month`,
    label: "MOST POPULAR ⭐",
    highlighted: false,
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
    id: "launch",
    name: "Launch LTD",
    price: String(PRICING.plans.ltd.price),
    currency: PRICING.plans.ltd.currency,
    period: PRICING.plans.ltd.period,
    description:
      "Pay once, own it forever. Unlimited conversations. No subscription loops.",
    credits: "Unlimited",
    label: "FOUNDER'S EDITION",
    highlighted: true,
    features: [
      { text: "All 9 conversation directions", included: true },
      { text: "Max screenshots allowed*", included: true },
      { text: "Max context messages*", included: true },
      { text: "Custom hints (1000 chars)", included: true },
      { text: "Chemistry tracking", included: true },
      { text: "Coach reasoning", included: true },
      { text: "Profile blueprints", included: true },
      { text: "Get Number / Ask Out", included: true },
      { text: "Priority server allocation", included: true },
      { text: "Early access to feature updates", included: true },
      { text: "Lifetime system updates", included: true },
    ],
  },
];

function CheckIcon({ highlighted }: { highlighted?: boolean }) {
  return (
    <svg
      className={`h-3.5 w-3.5 flex-shrink-0 ${
        highlighted ? "text-neon-red" : "text-nothing-text-secondary"
      }`}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2.5}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M4.5 12.75l6 6 9-13.5"
      />
    </svg>
  );
}

function MinusIcon() {
  return (
    <svg
      className="h-3.5 w-3.5 flex-shrink-0 text-nothing-text-tertiary opacity-50"
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
  const [ltdConfig, setLtdConfig] = useState<{
    spotsRemaining: number;
    totalSpots: number;
  } | null>(null);
  const [showLtdModal, setShowLtdModal] = useState(false);

  // Fetch real scarcity count from backend
  useEffect(() => {
    fetch(API_URLS.ltdBannerConfig)
      .then((res) => res.json())
      .then((data) => {
        if (data.enabled && data.spots_remaining !== undefined) {
          setLtdConfig({
            spotsRemaining: data.spots_remaining,
            totalSpots: data.total_spots,
          });
        }
      })
      .catch(() => {
        // Fallback to hardcoded PRICING.ltdSpots on error
      });
  }, []);

  const spotsLeft =
    ltdConfig?.spotsRemaining ??
    PRICING.ltdSpots.total - PRICING.ltdSpots.claimed;
  const totalSpots = ltdConfig?.totalSpots ?? PRICING.ltdSpots.total;

  return (
    <section
      id="pricing"
      className="relative px-6 py-24 sm:py-32 overflow-hidden"
    >
      <div
        className="absolute inset-0 opacity-[0.02] pointer-events-none"
        style={{
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)",
          backgroundSize: "40px 40px",
        }}
      />

      <AnimatedSection className="mx-auto max-w-2xl text-center mb-16 sm:mb-20">
        <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-nothing-border bg-nothing-surface px-4 py-1.5 text-xs font-mono text-nothing-text-secondary tracking-wider">
          <StatusDot active />
          PRICING
        </div>
        <h2 className="font-heading text-3xl sm:text-4xl md:text-5xl font-extrabold tracking-tight text-nothing-white">
          Pick Your <span className="text-neon-red">Edge</span>.
        </h2>
        <p className="mt-4 text-nothing-text-secondary text-sm sm:text-base leading-relaxed max-w-lg mx-auto">
          Start accelerating your chat conversion rate today. Own the platform
          outright or pay as you go.
        </p>
        <p className="mt-2 text-xs font-mono text-nothing-text-tertiary tracking-wider">
          Start free — no credit card needed
        </p>
        <p className="mt-2 text-xs font-mono text-nothing-text-tertiary tracking-wider">
          ₹249/mo &bull;{" "}
          <span className="text-neon-red">
            ₹999 Lifetime = 4 months of Match Pro
          </span>
        </p>
      </AnimatedSection>

      {/* Trust bar */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        className="mx-auto mb-12 flex flex-wrap items-center justify-center gap-x-8 gap-y-3 text-xs font-mono text-nothing-text-secondary tracking-wider"
      >
        <span className="inline-flex items-center gap-1.5">
          <svg
            className="h-3.5 w-3.5 text-nothing-success"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z"
            />
          </svg>
          End-to-End Encrypted
        </span>
        <span className="inline-flex items-center gap-1.5">
          <svg
            className="h-3.5 w-3.5 text-nothing-success"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0"
            />
          </svg>
          Auto-Delete Screenshots
        </span>
        <span className="inline-flex items-center gap-1.5">
          <svg
            className="h-3.5 w-3.5 text-nothing-success"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"
            />
          </svg>
          No Data Stored
        </span>
      </motion.div>

      <StaggerContainer className="mx-auto max-w-6xl" staggerDelay={0.1}>
        <div className="grid gap-6 lg:gap-8 sm:grid-cols-1 lg:grid-cols-3 items-center">
          {PLANS.map((plan) => (
            <StaggerItem
              key={plan.id}
              distance={60}
              className={plan.highlighted ? "order-first lg:order-none" : ""}
            >
              <ScaleHover scale={plan.highlighted ? 1.02 : 1.01}>
                <div
                  className={`relative flex flex-col p-6 sm:p-8 transition-all duration-300 rounded-xl ${
                    plan.highlighted
                      ? "bg-nothing-black lg:-my-8 lg:py-12 border-2 border-neon-red z-20"
                      : "bg-nothing-black border border-nothing-border hover:border-neon-red/30 hover:bg-nothing-surface z-10"
                  }`}
                >
                  <span
                    className={`inline-block font-mono text-[10px] tracking-[0.15em] mb-4 ${
                      plan.highlighted
                        ? "text-neon-red font-bold"
                        : "text-nothing-text-tertiary"
                    }`}
                  >
                    [ {plan.label} ]
                  </span>

                  <h3
                    className={`font-heading text-xl font-bold mb-1 ${
                      plan.highlighted
                        ? "text-nothing-white"
                        : "text-nothing-text-secondary"
                    }`}
                  >
                    {plan.name}
                  </h3>
                  <p className="text-xs text-nothing-text-tertiary mb-4 leading-relaxed">
                    {plan.description}
                  </p>

                  <div className="mb-2">
                    <motion.span
                      className={`text-3xl font-extrabold inline-block ${
                        plan.highlighted
                          ? "text-nothing-white"
                          : "text-nothing-text-secondary"
                      }`}
                      initial={{ opacity: 0, scale: 0.5 }}
                      whileInView={{ opacity: 1, scale: 1 }}
                      viewport={{ once: true }}
                      transition={{
                        type: "spring",
                        stiffness: 200,
                        damping: 15,
                        delay: 0.2,
                      }}
                    >
                      {plan.currency}
                      {plan.price}
                    </motion.span>
                    <span className="text-sm text-nothing-text-tertiary ml-1 font-mono">
                      {plan.period}
                    </span>
                  </div>

                  <div className="text-xs font-mono text-nothing-text-tertiary mb-6 tracking-wider">
                    <span
                      className={
                        plan.highlighted
                          ? "text-nothing-white"
                          : "text-nothing-text-secondary"
                      }
                    >
                      {plan.credits}
                    </span>
                  </div>

                  {plan.highlighted && (
                    <motion.div
                      initial={{ opacity: 0, y: -8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.5 }}
                      className="mb-4 flex items-center gap-2 rounded-lg border border-neon-red/20 bg-neon-red/10 px-3 py-2"
                    >
                      <motion.span
                        className="h-2 w-2 rounded-full bg-neon-red"
                        animate={{ scale: [1, 1.3, 1], opacity: [0.6, 1, 0.6] }}
                        transition={{
                          duration: 1.2,
                          repeat: Infinity,
                        }}
                      />
                      <span className="text-[10px] font-mono text-neon-red tracking-wider font-bold">
                        {spotsLeft} of {totalSpots} founder licenses remaining
                      </span>
                    </motion.div>
                  )}

                  {plan.id === "launch" ? (
                    <motion.button
                      onClick={() => {
                        setShowLtdModal(true);
                        posthog.capture("ltd_checkout_opened");
                      }}
                      className={`mb-6 inline-flex items-center justify-center gap-1.5 rounded-full px-4 py-2 text-xs font-bold transition-all duration-200 ${
                        plan.highlighted
                          ? "bg-neon-red text-nothing-white hover:bg-red-600"
                          : "border border-nothing-border text-nothing-text-secondary hover:bg-nothing-white/5 hover:text-nothing-white"
                      }`}
                      whileHover={{ scale: 1.04 }}
                      whileTap={{ scale: 0.97 }}
                    >
                      <svg
                        className="h-3 w-3"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth={2}
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M10.5 1.5H8.25A2.25 2.25 0 006 3.75v16.5a2.25 2.25 0 002.25 2.25h7.5A2.25 2.25 0 0018 20.25V3.75a2.25 2.25 0 00-2.25-2.25H13.5m-3 0V3h3V1.5m-3 0h3m-1.5 15v.01M12 12v7.5"
                        />
                      </svg>
                      Claim Lifetime License
                    </motion.button>
                  ) : (
                    <motion.a
                      href={APP_URLS.googlePlay}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={() => posthog.capture("pricing_plan_cta_clicked", { plan: plan.id, plan_name: plan.name })}
                      className={`mb-6 inline-flex items-center justify-center gap-1.5 rounded-full px-4 py-2 text-xs font-bold transition-all duration-200 ${
                        plan.highlighted
                          ? "bg-neon-red text-nothing-white hover:bg-red-600"
                          : "border border-nothing-border text-nothing-text-secondary hover:bg-nothing-white/5 hover:text-nothing-white"
                      }`}
                      whileHover={{ scale: 1.04 }}
                      whileTap={{ scale: 0.97 }}
                    >
                      <svg
                        className="h-3 w-3"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth={2}
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M10.5 1.5H8.25A2.25 2.25 0 006 3.75v16.5a2.25 2.25 0 002.25 2.25h7.5A2.25 2.25 0 0018 20.25V3.75a2.25 2.25 0 00-2.25-2.25H13.5m-3 0V3h3V1.5m-3 0h3m-1.5 15v.01M12 12v7.5"
                        />
                      </svg>
                      Download App
                    </motion.a>
                  )}

                  {plan.highlighted && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: 0.8 }}
                      className="mb-4 rounded-lg border border-nothing-border bg-nothing-surface/50 px-3 py-2.5 text-center"
                    >
                      <p className="text-[10px] font-mono text-nothing-text-secondary tracking-wider leading-relaxed">
                        ₹249/mo × 12 ={" "}
                        <span className="text-nothing-white">₹2,988/yr</span>
                        <br />
                        <span className="text-neon-red">
                          ₹999 LTD pays for itself in 4 months
                        </span>
                      </p>
                      <p className="mt-2 text-[9px] font-mono text-nothing-text-tertiary tracking-wider">
                        * Fair usage policy applies. See Terms of Service.
                      </p>
                    </motion.div>
                  )}

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
                        {feature.included ? (
                          <CheckIcon highlighted={plan.highlighted} />
                        ) : (
                          <MinusIcon />
                        )}
                        <span
                          className={`text-xs leading-relaxed ${
                            feature.included
                              ? plan.highlighted
                                ? "text-nothing-white"
                                : "text-nothing-text-secondary"
                              : "text-nothing-text-tertiary opacity-50"
                          }`}
                        >
                          {feature.text}
                        </span>
                      </motion.li>
                    ))}
                  </ul>
                </div>
              </ScaleHover>
            </StaggerItem>
          ))}
        </div>
      </StaggerContainer>

      {/* LTD checkout modal */}
      <LtdCheckoutModal
        isOpen={showLtdModal}
        onClose={() => setShowLtdModal(false)}
      />
    </section>
  );
}
