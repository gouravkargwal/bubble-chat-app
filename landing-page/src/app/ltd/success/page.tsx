"use client";

import { Suspense, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { MobileIcon } from "@/components/interactive-hero/icons";
import { StatusDot } from "@/components/Logo";
import { APP_URLS, EMAILS } from "@/app/constants";
import posthog from "posthog-js";

export default function LTDSuccessPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-nothing-black flex items-center justify-center">
          <div className="animate-pulse text-nothing-text-secondary text-sm">
            Loading...
          </div>
        </div>
      }
    >
      <LTDSuccessContent />
    </Suspense>
  );
}

function LTDSuccessContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const code = searchParams.get("code") || "";
  const error = searchParams.get("error");
  const txnid = searchParams.get("txnid") || "";
  const amount = searchParams.get("amount") || "";

  useEffect(() => {
    if (error) {
      posthog.capture("ltd_payment_verification_failed", {
        error,
        txnid,
        amount,
      });
    } else {
      posthog.capture("ltd_payment_succeeded", {
        has_code: Boolean(code),
        txnid: txnid || undefined,
        amount: amount || undefined,
      });
    }
  }, [error, code, txnid, amount]);

  if (error) {
    return (
      <main className="min-h-screen bg-nothing-black flex flex-col items-center justify-center px-4 py-20">
        <div className="w-full max-w-md">
          <div className="mb-6 text-center">
            <div className="inline-flex items-center gap-2 rounded-full border border-nothing-border bg-nothing-surface px-4 py-1.5 text-xs font-mono text-nothing-text-secondary tracking-wider">
              <StatusDot />
              <span>VERIFICATION_FAILED</span>
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
            <h1 className="text-2xl font-extrabold text-nothing-white mb-2">
              Verification Failed
            </h1>
            <p className="text-sm text-nothing-text-secondary mb-6">
              Don't worry — if your payment was successful, your LTD code will
              be emailed to you. Contact{" "}
              <a
                href={`mailto:${EMAILS.support}`}
                className="underline text-neon-red"
              >
                {EMAILS.support}
              </a>{" "}
              for help.
            </p>
            <button
              onClick={() => router.push("/#pricing")}
              className="rounded-full bg-neon-red px-6 py-3 text-xs font-bold text-nothing-white"
            >
              Return to Pricing
            </button>
          </motion.div>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-nothing-black flex flex-col items-center justify-center px-4 py-20">
      <div className="w-full max-w-md">
        <div className="mb-6 text-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-nothing-border bg-nothing-surface px-4 py-1.5 text-xs font-mono text-nothing-text-secondary tracking-wider">
            <StatusDot active />
            <span>PAYMENT_CONFIRMED</span>
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
            transition={{ type: "spring", stiffness: 200, damping: 15 }}
            className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-nothing-success/20"
          >
            <svg
              className="h-8 w-8 text-nothing-success"
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
          </motion.div>

          <h1 className="text-2xl font-extrabold text-nothing-white mb-2">
            Payment Successful! 🎉
          </h1>
          <p className="text-sm text-nothing-text-secondary mb-6">
            Your Lifetime Deal is confirmed. Check your email for the redemption
            code.
          </p>

          {code && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="rounded-xl border border-nothing-border bg-nothing-black p-4 mb-6"
            >
              <p className="text-[10px] font-mono text-nothing-text-tertiary tracking-wider mb-2">
                YOUR REDEMPTION CODE
              </p>
              <p className="text-2xl font-extrabold text-neon-red tracking-widest font-mono">
                {code}
              </p>
            </motion.div>
          )}

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
            className="text-left text-xs text-nothing-text-secondary space-y-2 mb-6"
          >
            <p className="font-bold text-nothing-white">How to activate:</p>
            <ol className="list-decimal list-inside space-y-1">
              <li>Open the Cookd app on your Android device</li>
              <li>Go to Settings → Redeem Lifetime Code</li>
              <li>Enter the code shown above</li>
              <li>Enjoy lifetime access! 🚀</li>
            </ol>
          </motion.div>

          <div className="flex flex-col items-center gap-3 mt-6">
            <motion.a
              href={APP_URLS.googlePlay}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 rounded-full bg-nothing-white px-6 py-3 text-xs font-bold text-nothing-black transition-all duration-200 hover:bg-nothing-white/90"
              whileHover={{ scale: 1.05 }}
            >
              <MobileIcon className="h-3.5 w-3.5" />
              Open Cookd App
            </motion.a>

            <motion.button
              onClick={() => router.push("/")}
              className="inline-flex items-center gap-2 rounded-full border border-nothing-border px-6 py-3 text-xs font-bold text-nothing-white transition-all duration-200 hover:bg-nothing-white/5"
              whileHover={{ scale: 1.05 }}
            >
              Back to Home
            </motion.button>
          </div>
        </motion.div>
      </div>
    </main>
  );
}
