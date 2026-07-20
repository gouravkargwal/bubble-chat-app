import Link from "next/link";
import type { Metadata } from "next";
import { BLOG_ARTICLES } from "./metadata";
import { SITE } from "@/app/constants";

export const metadata: Metadata = {
  title: `Blog | ${SITE.name}`,
  description:
    "Conversation tips, AI guides, and strategies to get better replies across any messaging app.",
  openGraph: {
    title: `${SITE.name} Blog — Conversation Tips & AI Guides`,
    description:
      "Learn how to get better replies, craft engaging messages, and master conversations with AI-powered insights.",
  },
};

export default function BlogListPage() {
  return (
    <main className="min-h-screen pt-24 pb-16 px-6 bg-brand-black">
      <div className="mx-auto max-w-4xl">
        {/* Header */}
        <div className="mb-12 text-center">
          <h1 className="font-heading text-3xl sm:text-4xl md:text-5xl font-extrabold tracking-tight text-brand-white">
            Conversation Tips &{" "}
            <span className="text-brand-primary">AI Guides</span>
          </h1>
          <p className="mt-4 text-brand-muted text-sm sm:text-base max-w-xl mx-auto leading-relaxed">
            Data-driven advice to improve your conversations and get
            more responses across any messaging app.
          </p>
        </div>

        {/* Articles grid */}
        <div className="space-y-8">
          {BLOG_ARTICLES.map((article) => (
            <Link
              key={article.slug}
              href={`/blog/${article.slug}`}
              className="group block rounded-xl border border-brand-border bg-brand-surface p-6 sm:p-8 transition-all duration-300 hover:border-brand-primary/40 hover:bg-brand-surface/80"
            >
              <div className="flex flex-col gap-3">
                {/* Meta */}
                <div className="flex items-center gap-3 text-xs font-mono text-brand-muted tracking-wider">
                  <span>{article.category}</span>
                  <span className="text-brand-muted/50">&bull;</span>
                  <time dateTime={article.date}>{article.date}</time>
                  <span className="text-brand-muted/50">&bull;</span>
                  <span>{article.readTime}</span>
                </div>

                {/* Title */}
                <h2 className="font-heading text-xl sm:text-2xl font-bold text-brand-white group-hover:text-brand-primary transition-colors duration-200">
                  {article.title}
                </h2>

                {/* Description */}
                <p className="text-sm text-brand-muted leading-relaxed max-w-2xl">
                  {article.description}
                </p>

                {/* Read more */}
                <span className="mt-2 inline-flex items-center gap-1.5 text-xs font-bold text-brand-primary tracking-wider uppercase group-hover:gap-2 transition-all duration-200">
                  Read Article
                  <svg
                    className="h-3 w-3"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2.5}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M9 5l7 7-7 7"
                    />
                  </svg>
                </span>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </main>
  );
}
