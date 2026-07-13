import type { MetadataRoute } from "next";
import { APP_URLS } from "./constants";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/ltd/success", "/ltd/failure"],
    },
    sitemap: `${APP_URLS.website}/sitemap.xml`,
  };
}
