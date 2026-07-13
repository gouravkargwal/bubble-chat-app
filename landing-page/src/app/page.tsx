import { ClientShell } from "@/components/ClientShell";

/**
 * Landing page — Server Component.
 *
 * All interactive state is delegated to ClientShell.
 * This keeps the page server-renderable for better SEO (SSR meta, H1, etc.)
 * while still allowing the full interactive funnel experience.
 */
export default function Home() {
  return <ClientShell />;
}
