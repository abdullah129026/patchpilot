import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/site";

const PATHS = [
  "/",
  "/case-study",
  "/terms",
  "/privacy",
  "/acceptable-use",
  "/report/sample-humanize-57",
  "/report/sample-pyflakes-764",
  "/report/sample-pyflakes-744",
];

export default function sitemap(): MetadataRoute.Sitemap {
  if (!SITE_URL) return [];
  return PATHS.map((path) => ({ url: `${SITE_URL}${path}` }));
}
