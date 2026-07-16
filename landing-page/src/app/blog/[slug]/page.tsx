import Link from "next/link";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getArticleBySlug, getAllSlugs, BLOG_ARTICLES } from "../metadata";
import { SITE, APP_URLS } from "@/app/constants";

// ── Static generation ──
export const dynamicParams = false;

export function generateStaticParams() {
  return getAllSlugs().map((slug) => ({ slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const article = getArticleBySlug(slug);
  if (!article) return {};

  return {
    title: `${article.title} | ${SITE.name} Blog`,
    description: article.description,
    alternates: {
      canonical: `${APP_URLS.website}/blog/${slug}`,
    },
    openGraph: {
      title: article.title,
      description: article.description,
      url: `${APP_URLS.website}/blog/${slug}`,
      type: "article",
      publishedTime: article.date,
      modifiedTime: article.modifiedDate ?? article.date,
      authors: [article.author],
      section: article.category,
      images: [
        {
          url: `${APP_URLS.website}/logo.svg`,
          width: 512,
          height: 512,
          alt: article.title,
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      title: article.title,
      description: article.description,
    },
  };
}

export default async function BlogArticlePage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const article = getArticleBySlug(slug);

  if (!article) {
    notFound();
  }

  // Related articles (same category, exclude current)
  const related = BLOG_ARTICLES.filter(
    (a) => a.category === article.category && a.slug !== article.slug
  ).slice(0, 3);

  return (
    <main className="min-h-screen pt-24 pb-16 px-6 bg-brand-black">
      <article className="mx-auto max-w-3xl">
        {/* Back link */}
        <Link
          href="/blog"
          className="mb-8 inline-flex items-center gap-1.5 text-xs font-mono text-brand-muted hover:text-brand-white transition-colors tracking-wider uppercase"
        >
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
              d="M15 19l-7-7 7-7"
            />
          </svg>
          Back to Blog
        </Link>

        {/* Meta header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 text-xs font-mono text-brand-muted tracking-wider mb-4">
            <span className="rounded-full border border-brand-border px-3 py-1">
              {article.category}
            </span>
            <span className="text-brand-muted/50">&bull;</span>
            <time dateTime={article.date}>{article.date}</time>
            <span className="text-brand-muted/50">&bull;</span>
            <span>{article.readTime}</span>
          </div>

          <h1 className="font-heading text-3xl sm:text-4xl md:text-5xl font-extrabold tracking-tight text-brand-white leading-tight">
            {article.title}
          </h1>

          <p className="mt-4 text-brand-muted text-sm sm:text-base leading-relaxed">
            by <span className="text-brand-white">{article.author}</span>
          </p>
        </div>

        {/* Article body */}
        <div className="prose prose-invert max-w-none">
          {article.body.split("\n\n").map((paragraph, i) => (
            <p
              key={i}
              className="text-sm sm:text-base leading-relaxed text-brand-muted mb-4"
            >
              {paragraph}
            </p>
          ))}
        </div>

        {/* Author CTA */}
        <div className="mt-12 rounded-xl border border-brand-border bg-brand-surface p-6 sm:p-8 text-center">
          <h2 className="font-heading text-xl sm:text-2xl font-bold text-brand-white mb-3">
            Get Better Replies Instantly
          </h2>
          <p className="text-sm text-brand-muted mb-6 max-w-md mx-auto leading-relaxed">
            Download Cookd — the AI dating coach that analyzes your chats and
            crafts winning replies in seconds.
          </p>
          <a
            href={APP_URLS.googlePlay}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 rounded-full bg-brand-primary px-8 py-3 text-sm font-bold text-brand-white transition-all duration-300 hover:shadow-[0_0_30px_rgba(225,29,72,0.3)]"
          >
            <svg
              className="h-4 w-4"
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
            Download Cookd on Google Play
          </a>
        </div>

        {/* Related articles */}
        {related.length > 0 && (
          <div className="mt-12">
            <h2 className="font-heading text-xl font-bold text-brand-white mb-6">
              More {article.category} Articles
            </h2>
            <div className="grid gap-4 sm:grid-cols-2">
              {related.map((r) => (
                <Link
                  key={r.slug}
                  href={`/blog/${r.slug}`}
                  className="rounded-xl border border-brand-border bg-brand-surface p-5 transition-all duration-300 hover:border-brand-primary/40 hover:bg-brand-surface/80"
                >
                  <h3 className="font-heading text-sm font-bold text-brand-white mb-2 leading-snug">
                    {r.title}
                  </h3>
                  <p className="text-xs text-brand-muted">{r.readTime}</p>
                </Link>
              ))}
            </div>
          </div>
        )}
      </article>
    </main>
  );
}
