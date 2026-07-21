import type { MetadataRoute } from "next";
import { APP_URLS } from "./constants";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: [],
    },
    sitemap: `${APP_URLS.website}/sitemap.xml`,
  };
}
