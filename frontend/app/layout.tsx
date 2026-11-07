import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import Link from "next/link";
import { SITE_URL } from "@/lib/site";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono" });

export const metadata: Metadata = {
  metadataBase: SITE_URL ? new URL(SITE_URL) : undefined,
  title: "PatchPilot: prove the bug before you fix it",
  description:
    "Paste a public GitHub issue link. PatchPilot reproduces the bug in a Docker sandbox and returns a reproduction script, a failing test, and a suggested fix diff, with the logs as proof.",
  openGraph: {
    title: "PatchPilot: prove the bug before you fix it",
    description:
      "Paste a public GitHub issue link. PatchPilot reproduces the bug in a Docker sandbox and returns a reproduction script, a failing test, and a suggested fix diff, with the logs as proof.",
    type: "website",
  },
  twitter: {
    card: "summary",
    title: "PatchPilot: prove the bug before you fix it",
    description:
      "Paste a public GitHub issue link. PatchPilot reproduces the bug in a Docker sandbox and returns a reproduction script, a failing test, and a suggested fix diff, with the logs as proof.",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${mono.variable}`}>
      <body>
        <header className="site">
          <div className="wrap">
            <Link href="/" className="logo">
              Patch<span>Pilot</span>
            </Link>
            <nav className="site">
              <Link href="/#how-it-works">How it works</Link>
              <Link href="/#samples">Sample reports</Link>
              <Link href="/case-study">Case study</Link>
              <Link href="/terms">Terms</Link>
            </nav>
          </div>
        </header>
        <main className="wrap">{children}</main>
        <footer className="site">
          <div className="wrap">
            <p>
              PatchPilot is a demonstration tool. Reports disclose that an AI
              agent produced them and separate what was verified from what was
              suggested. Nothing is posted to any repository.
            </p>
            <p>
              <Link href="/terms">Terms</Link>
              <Link href="/acceptable-use">Acceptable Use</Link>
              <Link href="/privacy">Privacy</Link>
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
