import type { MetadataRoute } from "next";
import { APP_URLS } from "./constants";

const routes = [
  { path: "/", priority: 1.0, changeFrequency: "weekly" as const },
  { path: "/contact", priority: 0.5, changeFrequency: "monthly" as const },
  { path: "/privacy", priority: 0.3, changeFrequency: "monthly" as const },
  { path: "/terms", priority: 0.3, changeFrequency: "monthly" as const },
];

export default function sitemap(): MetadataRoute.Sitemap {
  return routes.map(({ path, priority, changeFrequency }) => ({
    url: `${APP_URLS.website}${path}`,
    lastModified: new Date(),
    changeFrequency,
    priority,
  }));
}
