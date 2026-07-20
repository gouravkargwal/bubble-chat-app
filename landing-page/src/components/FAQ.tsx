"use client";

import React, { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { StatusDot } from "./Logo";
import { AnimatedSection } from "./Animations";
import posthog from "posthog-js";

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
    q: "Which messaging apps does Cookd support?",
    a: "Cookd works with any chat-based app — Instagram DM, WhatsApp, Telegram, and many others. If you can screenshot it, Cookd can analyze it.",
  },
  {
    q: "Is there a free plan?",
    a: "Yes! Every user gets 2 free conversations per day (up to 60 per month) plus 10 bonus conversations on signup. No credit card needed. It's enough to try it out and see the difference.",
  },
  {
    q: "How accurate is the AI?",
    a: "Our AI picks up on subtle cues like tone, engagement level, and personality signals that most people miss. Users report a 2-3x improvement in reply rates.",
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
  onOpen,
  onClose,
}: {
  question: string;
  answer: string;
  isOpen: boolean;
  onToggle: () => void;
  onOpen: () => void;
  onClose: () => void;
}) {
  const handleToggle = useCallback(() => {
    if (isOpen) {
      onClose();
    } else {
      onOpen();
    }
    onToggle();
  }, [isOpen, onOpen, onClose, onToggle]);

  return (
    <div className="border-b border-nothing-border last:border-b-0">
      <h3>
        <button
          onClick={handleToggle}
          className="flex w-full items-center justify-between py-5 text-left transition-colors duration-200"
          aria-expanded={isOpen}
        >
          <span className="text-sm font-bold text-nothing-white hover:text-neon-red transition-colors duration-200">
            {question}
          </span>
          <motion.svg
            className="h-4 w-4 flex-shrink-0 ml-4 text-nothing-white"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2.5}
            animate={{ rotate: isOpen ? 45 : 0 }}
            transition={{ duration: 0.2 }}
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 4.5v15m7.5-7.5h-15"
            />
          </motion.svg>
        </button>
      </h3>
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

  const handleOpen = useCallback((index: number, question: string) => {
    posthog.capture("faq_opened", { question, index });
  }, []);

  const handleClose = useCallback((index: number, question: string) => {
    posthog.capture("faq_closed", { question, index });
  }, []);

  const handleToggle = useCallback(
    (i: number) => {
      setOpenIndex(openIndex === i ? null : i);
    },
    [openIndex]
  );

  return (
    <section
      id="faq"
      className="relative px-6 py-24 sm:py-32 overflow-hidden"
      aria-labelledby="faq-heading"
    >
      {/* Background grid */}
      <div
        className="absolute inset-0 opacity-[0.02] pointer-events-none"
        style={{
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)",
          backgroundSize: "40px 40px",
        }}
        aria-hidden="true"
      />

      <AnimatedSection className="mx-auto max-w-2xl text-center mb-16">
        <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-nothing-border bg-nothing-surface px-4 py-1.5 text-xs font-mono text-nothing-text-secondary tracking-wider">
          <StatusDot active />
          FAQ
        </div>
        <h2
          id="faq-heading"
          className="font-heading text-3xl sm:text-4xl md:text-5xl font-extrabold tracking-tight text-nothing-white"
        >
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
              onToggle={() => handleToggle(i)}
              onOpen={() => handleOpen(i, faq.q)}
              onClose={() => handleClose(i, faq.q)}
            />
          ))}
        </div>
      </AnimatedSection>
    </section>
  );
}
