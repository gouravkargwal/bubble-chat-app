"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { StatusDot } from "./Logo";
import { AnimatedSection } from "./Animations";

const FAQS = [
  {
    q: "How does Cookd work?",
    a: "You share screenshots of your conversations, and our AI analyzes the chat dynamics, her personality cues, and the context. Then it generates multiple response options tailored to the situation — from playful to direct, depending on what's needed.",
  },
  {
    q: "Is my chat data private?",
    a: "Absolutely. Your conversations are encrypted in transit and at rest. We never store your screenshots longer than needed to generate a response, and we never share your chat data with anyone. You can delete your data anytime from settings.",
  },
  {
    q: "Which dating apps does Cookd support?",
    a: "Cookd works with any chat-based app — Hinge, Bumble, Tinder, Instagram DM, WhatsApp, Telegram, you name it. If you can screenshot it, Cookd can analyze it.",
  },
  {
    q: "Is there a free plan?",
    a: "Yes! Every user gets 2 free conversations per day (up to 60 per month) plus 10 bonus conversations on signup. No credit card needed. It's enough to try it out and see the difference.",
  },
  {
    q: "How accurate is the AI?",
    a: "Our AI is powered by Google Gemini Pro and has been trained on thousands of successful dating conversations. It picks up on subtle cues like tone, engagement level, and personality signals that most people miss. Users report a 2-3x improvement in reply rates.",
  },
  {
    q: "Can I cancel my subscription anytime?",
    a: "Yes. All paid plans are month-to-month or weekly with no lock-in. Cancel anytime from the app settings, and you'll keep access until the end of your billing period.",
  },
];

function FAQItem({
  question,
  answer,
  isOpen,
  onToggle,
}: {
  question: string;
  answer: string;
  isOpen: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="border-b border-nothing-border last:border-b-0">
      <button
        onClick={onToggle}
        className="flex w-full items-center justify-between py-5 text-left text-sm font-bold text-nothing-white hover:text-neon-red transition-colors duration-200"
        aria-expanded={isOpen}
      >
        <span>{question}</span>
        <motion.svg
          className="h-4 w-4 flex-shrink-0 ml-4"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2.5}
          animate={{ rotate: isOpen ? 45 : 0 }}
          transition={{ duration: 0.2 }}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M12 4.5v15m7.5-7.5h-15"
          />
        </motion.svg>
      </button>
      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            key="content"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
            className="overflow-hidden"
          >
            <p className="pb-5 text-sm leading-relaxed text-nothing-text-secondary">
              {answer}
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export function FAQ() {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  return (
    <section id="faq" className="relative px-6 py-24 sm:py-32 overflow-hidden">
      {/* Background grid */}
      <div
        className="absolute inset-0 opacity-[0.02] pointer-events-none"
        style={{
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)",
          backgroundSize: "40px 40px",
        }}
      />

      <AnimatedSection className="mx-auto max-w-2xl text-center mb-16">
        <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-nothing-border bg-nothing-surface px-4 py-1.5 text-xs font-mono text-nothing-text-secondary tracking-wider">
          <StatusDot active />
          FAQ
        </div>
        <h2 className="text-3xl sm:text-4xl md:text-5xl font-extrabold tracking-tight text-nothing-white">
          Got Questions?{" "}
          <span className="text-neon-red">We{"'"}ve Got Answers</span>.
        </h2>
      </AnimatedSection>

      <AnimatedSection className="mx-auto max-w-2xl">
        <div className="rounded-xl border border-nothing-border bg-nothing-surface/40 backdrop-blur-sm px-6">
          {FAQS.map((faq, i) => (
            <FAQItem
              key={i}
              question={faq.q}
              answer={faq.a}
              isOpen={openIndex === i}
              onToggle={() => setOpenIndex(openIndex === i ? null : i)}
            />
          ))}
        </div>
      </AnimatedSection>
    </section>
  );
}
