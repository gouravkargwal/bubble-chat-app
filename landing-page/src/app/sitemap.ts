import type { MetadataRoute } from "next";
import { APP_URLS } from "./constants";
import { getAllSlugs } from "./blog/metadata";

const routes = [
  { path: "/", priority: 1.0, changeFrequency: "weekly" as const },
  { path: "/blog", priority: 0.8, changeFrequency: "weekly" as const },
  { path: "/contact", priority: 0.5, changeFrequency: "monthly" as const },
  { path: "/privacy", priority: 0.3, changeFrequency: "monthly" as const },
  { path: "/terms", priority: 0.3, changeFrequency: "monthly" as const },
];

export default function sitemap(): MetadataRoute.Sitemap {
  const blogRoutes = getAllSlugs().map((slug) => ({
    url: `${APP_URLS.website}/blog/${slug}`,
    lastModified: new Date(),
    changeFrequency: "monthly" as const,
    priority: 0.7 as const,
  }));

  return [
    ...routes.map(({ path, priority, changeFrequency }) => ({
      url: `${APP_URLS.website}${path}`,
      lastModified: new Date(),
      changeFrequency,
      priority,
    })),
    ...blogRoutes,
  ];
}
