"use client";

import React, { useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { LockIcon, MobileIcon } from "./interactive-hero/icons";
import { APP_URLS, API_URLS } from "@/app/constants";

interface LtdCheckoutModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function LtdCheckoutModal({ isOpen, onClose }: LtdCheckoutModalProps) {
  const [email, setEmail] = useState("");
  const [firstName, setFirstName] = useState("");
  const [phone, setPhone] = useState("");
  const [step, setStep] = useState<"form" | "loading" | "success" | "error">(
    "form"
  );
  const [errorMsg, setErrorMsg] = useState("");
  const [ltdCode, setLtdCode] = useState("");
  const formRef = useRef<HTMLFormElement>(null);
  const payuFormRef = useRef<HTMLFormElement>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const trimmedEmail = email.trim();
    if (!trimmedEmail || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedEmail)) {
      setErrorMsg("Please enter a valid email address");
      return;
    }

    setStep("loading");
    setErrorMsg("");

    try {
      // 1. Get signed PayU form params from backend
      const res = await fetch(API_URLS.ltdCreateOrder, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: trimmedEmail,
          firstname: firstName.trim() || "Customer",
          phone: phone.trim(),
        }),
      });

      if (!res.ok) {
        throw new Error("Failed to create payment order");
      }

      const data = await res.json();

      // 2. Populate the hidden PayU form and submit it
      const form = payuFormRef.current;
      if (!form) throw new Error("Form not found");

      // Set form action to PayU
      form.action = data.payu_base_url + "/_payment";

      // Populate hidden inputs
      const fields: Record<string, string> = {
        key: data.key,
        txnid: data.txnid,
        amount: data.amount,
        productinfo: data.productinfo,
        firstname: data.firstname,
        email: data.email,
        phone: data.phone,
        surl: data.surl,
        furl: data.furl,
        hash: data.hash,
        udf1: data.udf1 || "ltd",
        udf2: data.udf2 || "",
        udf3: data.udf3 || "",
      };

      Object.entries(fields).forEach(([name, value]) => {
        const input = form.querySelector<HTMLInputElement>(
          `input[name="${name}"]`
        );
        if (input) input.value = value;
      });

      // 3. Submit — redirects to PayU
      form.submit();
    } catch (err) {
      setStep("error");
      setErrorMsg(
        err instanceof Error
          ? err.message
          : "Something went wrong. Please try again."
      );
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          className="fixed inset-0 z-[100] flex items-center justify-center p-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          {/* Backdrop */}
          <motion.div
            className="absolute inset-0 bg-black/80 backdrop-blur-sm"
            onClick={onClose}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          />

          {/* Modal */}
          <motion.div
            className="relative z-10 w-full max-w-md rounded-2xl border border-nothing-border bg-nothing-black p-6 sm:p-8"
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
          >
            {/* Close button */}
            <button
              onClick={onClose}
              className="absolute top-4 right-4 text-nothing-text-tertiary hover:text-nothing-white transition-colors"
              aria-label="Close"
            >
              <svg
                className="h-5 w-5"
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
            </button>

            {step === "form" && (
              <>
                {/* Header */}
                <div className="text-center mb-6">
                  <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-neon-red/30 px-3 py-1 text-[10px] font-mono text-neon-red tracking-wider">
                    LIMITED OFFER
                  </div>
                  <h2 className="text-2xl font-extrabold tracking-tight text-nothing-white">
                    Lifetime Access
                  </h2>
                  <p className="mt-2 text-sm text-nothing-text-secondary">
                    <span className="text-3xl font-extrabold text-nothing-white">
                      ₹999
                    </span>{" "}
                    <span className="line-through text-nothing-text-tertiary">
                      ₹4,799
                    </span>
                    <br />
                    Pay once. Own it forever. No subscription.
                  </p>
                </div>

                {/* Offer highlights */}
                <div className="mb-6 grid grid-cols-2 gap-2 text-[10px] font-mono text-nothing-text-secondary">
                  <div className="rounded-lg border border-nothing-border p-2.5 text-center">
                    <span className="text-nothing-white font-bold">∞</span>
                    <br />
                    unlimited
                  </div>
                  <div className="rounded-lg border border-nothing-border p-2.5 text-center">
                    <span className="text-nothing-white font-bold">9</span>
                    <br />
                    directions
                  </div>
                  <div className="rounded-lg border border-nothing-border p-2.5 text-center">
                    <span className="text-nothing-white font-bold">∞</span>
                    <br />
                    no expiry
                  </div>
                  <div className="rounded-lg border border-nothing-border p-2.5 text-center">
                    <span className="text-nothing-white font-bold">✓</span>
                    <br />
                    lifetime updates
                  </div>
                </div>

                {/* Form */}
                <form onSubmit={handleSubmit} className="space-y-3">
                  <div>
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => {
                        setEmail(e.target.value);
                        setErrorMsg("");
                      }}
                      placeholder="your@email.com"
                      className="w-full rounded-xl border border-nothing-border bg-nothing-surface px-4 py-3 text-sm text-nothing-white outline-none placeholder:text-nothing-text-tertiary font-mono transition-all duration-200 focus:border-neon-red focus:ring-1 focus:ring-neon-red/30"
                      required
                    />
                  </div>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={firstName}
                      onChange={(e) => setFirstName(e.target.value)}
                      placeholder="First name (optional)"
                      className="flex-1 rounded-xl border border-nothing-border bg-nothing-surface px-4 py-3 text-sm text-nothing-white outline-none placeholder:text-nothing-text-tertiary font-mono transition-all duration-200 focus:border-neon-red focus:ring-1 focus:ring-neon-red/30"
                    />
                    <input
                      type="tel"
                      value={phone}
                      onChange={(e) => setPhone(e.target.value)}
                      placeholder="Phone (optional)"
                      className="flex-1 rounded-xl border border-nothing-border bg-nothing-surface px-4 py-3 text-sm text-nothing-white outline-none placeholder:text-nothing-text-tertiary font-mono transition-all duration-200 focus:border-neon-red focus:ring-1 focus:ring-neon-red/30"
                    />
                  </div>

                  {errorMsg && (
                    <motion.p
                      initial={{ opacity: 0, y: -4 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="text-xs font-mono text-neon-red"
                    >
                      {">"} {errorMsg}
                    </motion.p>
                  )}

                  <motion.button
                    type="submit"
                    className="w-full rounded-xl bg-neon-red py-3.5 text-sm font-bold text-nothing-white transition-all duration-200 hover:shadow-[0_0_30px_rgba(255,0,60,0.25)]"
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                  >
                    <span className="flex items-center justify-center gap-2">
                      <LockIcon className="h-4 w-4" />
                      Pay ₹999 — Lifetime Access
                    </span>
                  </motion.button>
                </form>

                {/* Trust */}
                <div className="mt-4 flex items-center justify-center gap-4 text-[10px] font-mono text-nothing-text-tertiary">
                  <span>🔒 Secured by PayU</span>
                  <span>•</span>
                  <span>Instant code delivery</span>
                </div>

                <p className="mt-4 text-center text-[10px] font-mono text-nothing-text-tertiary">
                  By proceeding, you agree to our{" "}
                  <a href="/terms" className="underline">
                    Terms
                  </a>
                </p>
              </>
            )}

            {step === "loading" && (
              <div className="py-12 text-center">
                <motion.div
                  className="mx-auto mb-4 h-12 w-12 rounded-full border-2 border-neon-red border-t-transparent"
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                />
                <p className="text-sm font-bold text-nothing-white">
                  Redirecting to PayU...
                </p>
                <p className="mt-2 text-xs text-nothing-text-secondary">
                  Please don't close this page.
                </p>

                {/* Hidden PayU form — populated and submitted above */}
                <form
                  ref={payuFormRef}
                  method="POST"
                  action=""
                  style={{ display: "none" }}
                >
                  <input type="hidden" name="key" value="" />
                  <input type="hidden" name="txnid" value="" />
                  <input type="hidden" name="amount" value="" />
                  <input type="hidden" name="productinfo" value="" />
                  <input type="hidden" name="firstname" value="" />
                  <input type="hidden" name="email" value="" />
                  <input type="hidden" name="phone" value="" />
                  <input type="hidden" name="surl" value="" />
                  <input type="hidden" name="furl" value="" />
                  <input type="hidden" name="hash" value="" />
                  <input type="hidden" name="udf1" value="" />
                  <input type="hidden" name="udf2" value="" />
                  <input type="hidden" name="udf3" value="" />
                </form>
              </div>
            )}

            {step === "success" && (
              <div className="py-8 text-center">
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
                <h2 className="text-xl font-extrabold text-nothing-white mb-2">
                  Payment Successful! 🎉
                </h2>
                <p className="text-sm text-nothing-text-secondary mb-6">
                  Your LTD code has been sent to{" "}
                  <span className="text-nothing-white font-mono">{email}</span>
                </p>

                <div className="rounded-xl border border-nothing-border bg-nothing-surface p-4 mb-6">
                  <p className="text-[10px] font-mono text-nothing-text-tertiary tracking-wider mb-2">
                    YOUR CODE
                  </p>
                  <p className="text-2xl font-extrabold text-neon-red tracking-widest font-mono">
                    {ltdCode}
                  </p>
                </div>

                <div className="text-left text-xs text-nothing-text-secondary space-y-2 mb-6">
                  <p className="font-bold text-nothing-white">
                    How to activate:
                  </p>
                  <ol className="list-decimal list-inside space-y-1">
                    <li>Open the Cookd app on your Android device</li>
                    <li>Go to Settings → Redeem Lifetime Code</li>
                    <li>Enter the code shown above</li>
                    <li>Enjoy lifetime access! 🚀</li>
                  </ol>
                </div>

                <a
                  href={APP_URLS.googlePlay}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 rounded-full bg-nothing-white px-6 py-3 text-xs font-bold text-nothing-black transition-all duration-200 hover:bg-nothing-white/90"
                >
                  <MobileIcon className="h-3.5 w-3.5" />
                  Open Cookd App
                </a>
              </div>
            )}

            {step === "error" && (
              <div className="py-8 text-center">
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
                <h2 className="text-xl font-extrabold text-nothing-white mb-2">
                  Something went wrong
                </h2>
                <p className="text-sm text-nothing-text-secondary mb-6">
                  {errorMsg}
                </p>
                <button
                  onClick={() => setStep("form")}
                  className="rounded-full bg-neon-red px-6 py-3 text-xs font-bold text-nothing-white"
                >
                  Try Again
                </button>
              </div>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
