"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import { StatusDot } from "@/components/Logo";

export default function LTDFailurePage() {
  return (
    <>
      <head>
        <meta name="robots" content="noindex, nofollow" />
      </head>
      <Suspense
        fallback={
          <div className="min-h-screen bg-nothing-black flex items-center justify-center">
            <div className="animate-pulse text-nothing-text-secondary text-sm">
              Loading...
            </div>
          </div>
        }
      >
        <LTDFailureContent />
      </Suspense>
    </>
  );
}

function LTDFailureContent() {
  const searchParams = useSearchParams();
  const errorMsg =
    searchParams.get("Error") ||
    searchParams.get("error") ||
    "Payment was cancelled or failed.";

  return (
    <main className="min-h-screen bg-nothing-black flex flex-col items-center justify-center px-4 py-20">
      <div className="w-full max-w-md">
        <div className="mb-6 text-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-nothing-border bg-nothing-surface px-4 py-1.5 text-xs font-mono text-nothing-text-secondary tracking-wider">
            <StatusDot />
            <span>PAYMENT_FAILED</span>
          </div>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-2xl border border-nothing-border bg-nothing-surface p-8 text-center"
        >
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-neon-red/20"
          >
            <svg
              className="h-8 w-8 text-neon-red"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </motion.div>

          <h1 className="font-heading text-2xl sm:text-3xl font-extrabold tracking-tight text-nothing-white mb-2">
            Payment Failed
          </h1>
          <p className="text-nothing-text-secondary mb-6 text-sm leading-relaxed">
            {errorMsg}
          </p>

          <div className="flex flex-col gap-3">
            <Link
              href="/#pricing"
              className="inline-flex items-center justify-center gap-2 rounded-full bg-neon-red px-6 py-3 text-sm font-bold text-nothing-white transition-opacity hover:opacity-90"
            >
              Try Again
            </Link>
            <Link
              href="/contact"
              className="inline-flex items-center justify-center gap-2 rounded-full border border-nothing-border px-6 py-3 text-sm font-bold text-nothing-white transition-opacity hover:opacity-90"
            >
              Contact Support
            </Link>
          </div>
        </motion.div>

        <p className="mt-6 text-center text-xs text-nothing-text-tertiary">
          Need help? Email{" "}
          <a
            href="mailto:support@cookdai.site"
            className="underline underline-offset-2 hover:text-nothing-white transition-colors"
          >
            support@cookdai.site
          </a>
        </p>
      </div>
    </main>
  );
}
