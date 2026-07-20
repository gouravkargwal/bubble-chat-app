"use client";

import React from "react";
import { Logo } from "./Logo";
import { EMAILS, SOCIAL_LINKS } from "@/app/constants";
import posthog from "posthog-js";

const FOOTER_LINKS = {
  Product: [
    { label: "Features", href: "#features" },
    { label: "How It Works", href: "#how-it-works" },
    { label: "Pricing", href: "#pricing" },
    { label: "FAQ", href: "#faq" },
    { label: "Blog", href: "/blog" },
    { label: "Contact", href: "/contact" },
  ],
  Company: [
    { label: "Careers", href: "/careers" },
  ],
  Legal: [
    { label: "Privacy Policy", href: "/privacy" },
    { label: "Terms of Service", href: "/terms" },
  ],
  Connect: [
    { label: "Twitter / X", href: SOCIAL_LINKS.twitter },
    { label: "Instagram", href: SOCIAL_LINKS.instagram },
    { label: "YouTube", href: SOCIAL_LINKS.youtube },
  ],
};

function trackFooterClick(category: string, label: string) {
  posthog.capture("footer_link_clicked", { category, label });
}

export function Footer() {
  return (
    <footer className="border-t border-nothing-border px-6 py-12 sm:py-16">
      <div className="mx-auto max-w-6xl">
        {/* Top section */}
        <div className="flex flex-col lg:flex-row justify-between gap-12">
          {/* Brand */}
          <div className="max-w-xs">
            <div className="flex items-center gap-2 mb-4">
              <Logo size={32} />
              <span className="font-heading text-base font-extrabold tracking-tight text-nothing-white">
                COOKD
              </span>
            </div>
            <p className="text-sm leading-relaxed text-nothing-text-secondary">
              AI-powered conversation assistant that helps you craft winning messages.
              Stop guessing. Start connecting.
            </p>
          </div>

          {/* Links */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-8 sm:gap-12">
            {Object.entries(FOOTER_LINKS).map(([category, links]) => (
              <div key={category}>
                <h2 className="text-xs font-mono tracking-[0.15em] text-nothing-text-secondary mb-4 uppercase">
                  {category}
                </h2>
                <ul className="space-y-3">
                  {links.map((link) => (
                    <li key={link.label}>
                      <a
                        href={link.href}
                        onClick={() => trackFooterClick(category, link.label)}
                        className="text-sm text-nothing-text-secondary hover:text-nothing-white transition-colors duration-200"
                      >
                        {link.label}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        {/* Bottom bar */}
        <div className="mt-12 pt-8 border-t border-nothing-border flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-xs font-mono text-nothing-text-secondary tracking-wider">
            &copy; {new Date().getFullYear()} COOKD. ALL RIGHTS RESERVED.
          </p>
          <div className="flex items-center gap-3 text-xs font-mono text-nothing-text-secondary tracking-wider">
            <span className="text-nothing-success">▲</span>
            <span>v2.0 // SYSTEM_ONLINE</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
