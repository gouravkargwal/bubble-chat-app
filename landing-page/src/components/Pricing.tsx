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

const TOTAL_SPOTS = 140;
const CLAIMED_BASE = 67;

const PLANS = [
  {
    id: "crush",
    name: "Crush Pass",
    price: "99",
    currency: "₹",
    period: "/week",
    description: "For when you need a quick, short-term edge.",
    credits: "50 credits",
    signupCredits: "",
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
    price: "249",
    currency: "₹",
    period: "/month",
    description: "The standard blueprint for dating control.",
    credits: "150 credits / month",
    signupCredits: "",
    label: "MOST FLEXIBLE",
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
    price: "999",
    currency: "₹",
    period: "/forever",
    description: "Pay once, own the ecosystem forever. No subscription loops.",
    credits: "Unlimited* Access",
    signupCredits: "",
    label: "🚨 LAUNCH EXCLUSIVE",
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
  const [spotsLeft, setSpotsLeft] = useState(TOTAL_SPOTS - CLAIMED_BASE);

  useEffect(() => {
    if (spotsLeft <= 0) return;
    const interval = setInterval(() => {
      if (Math.random() < 0.15) {
        setSpotsLeft((prev) => Math.max(0, prev - 1));
      }
    }, 45000);
    return () => clearInterval(interval);
  }, [spotsLeft]);

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
        <h2 className="text-3xl sm:text-4xl md:text-5xl font-extrabold tracking-tight text-nothing-white">
          Pick Your <span className="text-neon-red">Edge</span>.
        </h2>
        <p className="mt-4 text-nothing-text-secondary text-sm sm:text-base leading-relaxed max-w-lg mx-auto">
          Start accelerating your chat conversion rate today. Own the platform
          outright or pay as you go.
        </p>
        <p className="mt-2 text-xs font-mono text-nothing-text-tertiary tracking-wider">
          ₹99/wk &bull; ₹249/mo (Save 67%) &bull;{" "}
          <span className="text-neon-red">₹999 Lifetime (Best Value)</span>
        </p>
      </AnimatedSection>

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
                      ? "bg-nothing-black lg:-my-8 lg:py-12 border-2 border-neon-red z-20 shadow-2xl"
                      : plan.label === "WEEKLY PASS"
                      ? "bg-nothing-black/40 border border-nothing-border/30 opacity-70 hover:opacity-100 hover:bg-nothing-surface z-10"
                      : "bg-nothing-black border border-nothing-border hover:bg-nothing-surface z-10"
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
                    className={`text-xl font-bold mb-1 ${
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
                        {spotsLeft} of {TOTAL_SPOTS} launch licenses remaining
                      </span>
                    </motion.div>
                  )}

                  <motion.a
                    href="https://play.google.com/store/apps/details?id=com.cookd.mobile"
                    target="_blank"
                    rel="noopener noreferrer"
                    className={`mb-6 inline-flex items-center justify-center gap-1.5 rounded-full px-4 py-2 text-xs font-bold transition-all duration-200 ${
                      plan.highlighted
                        ? "bg-neon-red text-nothing-white hover:shadow-[0_0_20px_rgba(255,0,60,0.4)] hover:bg-red-600"
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
                    {plan.id === "launch"
                      ? "Claim Lifetime License"
                      : "Download App"}
                  </motion.a>

                  {plan.highlighted && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: 0.8 }}
                      className="mb-4 rounded-lg border border-nothing-border bg-nothing-surface/50 px-3 py-2.5 text-center"
                    >
                      <p className="text-[10px] font-mono text-nothing-text-secondary tracking-wider leading-relaxed">
                        Match Pro is ₹249/mo ={" "}
                        <span className="text-nothing-white">₹2,988/yr</span>
                        <br />
                        <span className="text-neon-red">
                          You save ₹1,989 in Year 1 alone with LTD
                        </span>
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
    </section>
  );
}
