// Canonical public URL of the deployed frontend. Set
// NEXT_PUBLIC_SITE_URL in the Vercel project when the site is deployed;
// until then it is undefined and the SEO routes stay empty rather than
// publishing a guessed domain.
export const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || undefined;
