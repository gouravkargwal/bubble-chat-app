"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Logo, StatusDot } from "./Logo";
import { APP_URLS } from "@/app/constants";
import posthog from "posthog-js";

const NAV_LINKS = [
  { label: "Features", href: "/#features" },
  { label: "How It Works", href: "/#how-it-works" },
  { label: "Pricing", href: "/#pricing" },
  { label: "FAQ", href: "/#faq" },
  { label: "Blog", href: "/blog" },
  { label: "Contact", href: "/contact" },
];

export function Header() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled
          ? "bg-nothing-black/90 backdrop-blur-md border-b border-nothing-border"
          : "bg-transparent"
      }`}
    >
      {/* Main nav bar */}
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4 sm:px-8">
        {/* Logo + Brand */}
        <Link
          href="/"
          className="flex items-center gap-3 group"
          aria-label="Cookd Home"
        >
          <Logo size={36} />
          <div className="flex items-center gap-3">
            <span className="font-heading text-lg font-extrabold tracking-tight text-nothing-white whitespace-nowrap">
              COOKD
            </span>
            <span className="hidden sm:inline-block">
              <StatusDot active />
            </span>
          </div>
        </Link>

        {/* Desktop Nav */}
        <nav
          className="hidden md:flex items-center gap-8"
          aria-label="Main navigation"
        >
          {NAV_LINKS.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="text-sm font-medium text-nothing-text-secondary hover:text-nothing-white transition-colors duration-200 tracking-wide"
            >
              {link.label}
            </a>
          ))}
        </nav>

        {/* Desktop CTA */}
        <div className="hidden md:flex items-center gap-4">
          <a
            href={APP_URLS.googlePlay}
            target="_blank"
            rel="noopener noreferrer"
            onClick={() =>
              posthog.capture("app_download_clicked", {
                source: "header",
                platform: "google_play",
              })
            }
            className="inline-flex items-center gap-1.5 rounded-full border border-nothing-border px-4 py-2 text-xs font-bold text-nothing-white transition-all duration-200 hover:bg-nothing-white/5 btn-secondary-accent"
            aria-label="Download Cookd from Google Play"
          >
            <svg
              className="h-3.5 w-3.5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M10.5 1.5H8.25A2.25 2.25 0 006 3.75v16.5a2.25 2.25 0 002.25 2.25h7.5A2.25 2.25 0 0018 20.25V3.75a2.25 2.25 0 00-2.25-2.25H13.5m-3 0V3h3V1.5m-3 0h3m-1.5 15v.01M12 12v7.5"
              />
            </svg>
            Google Play
          </a>
        </div>

        {/* Mobile Hamburger */}
        <button
          onClick={() => setMobileOpen(!mobileOpen)}
          className="md:hidden flex flex-col gap-1.5 p-2"
          aria-label={mobileOpen ? "Close menu" : "Open menu"}
          aria-expanded={mobileOpen}
        >
          <span
            className={`block h-0.5 w-5 bg-nothing-white transition-transform duration-200 ${
              mobileOpen ? "translate-y-2 rotate-45" : ""
            }`}
          />
          <span
            className={`block h-0.5 w-5 bg-nothing-white transition-opacity duration-200 ${
              mobileOpen ? "opacity-0" : ""
            }`}
          />
          <span
            className={`block h-0.5 w-5 bg-nothing-white transition-transform duration-200 ${
              mobileOpen ? "-translate-y-2 -rotate-45" : ""
            }`}
          />
        </button>
      </div>

      {/* Mobile Menu */}
      <div
        className={`md:hidden overflow-hidden transition-all duration-300 ${
          mobileOpen ? "max-h-96" : "max-h-0"
        }`}
        role="region"
        aria-label="Mobile navigation"
      >
        <div className="border-t border-nothing-border bg-nothing-black px-6 py-4 space-y-4">
          {NAV_LINKS.map((link) => (
            <a
              key={link.href}
              href={link.href}
              onClick={() => setMobileOpen(false)}
              className="block text-sm font-medium text-nothing-text-secondary hover:text-nothing-white transition-colors duration-200"
            >
              {link.label}
            </a>
          ))}
          <a
            href="https://play.google.com/store/apps/details?id=com.cookd.mobile"
            target="_blank"
            rel="noopener noreferrer"
            onClick={() => {
              setMobileOpen(false);
              posthog.capture("app_download_clicked", {
                source: "mobile_menu",
                platform: "google_play",
              });
            }}
            className="block w-full rounded-full border border-nothing-border px-4 py-2.5 text-center text-xs font-bold text-nothing-white mt-4 transition-all duration-200 hover:bg-nothing-white/5"
            aria-label="Download Cookd from Google Play"
          >
            <span className="inline-flex items-center justify-center gap-1.5">
              <svg
                className="h-3.5 w-3.5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M10.5 1.5H8.25A2.25 2.25 0 006 3.75v16.5a2.25 2.25 0 002.25 2.25h7.5A2.25 2.25 0 0018 20.25V3.75a2.25 2.25 0 00-2.25-2.25H13.5m-3 0V3h3V1.5m-3 0h3m-1.5 15v.01M12 12v7.5"
                />
              </svg>
              Google Play
            </span>
          </a>
        </div>
      </div>
    </header>
  );
}
