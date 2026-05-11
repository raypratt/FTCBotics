import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "FTC Stats",
  description: "EPA-based statistics for FIRST Tech Challenge 2025-26",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col bg-background text-foreground">
        <header className="border-b border-border sticky top-0 z-50 bg-background/95 backdrop-blur">
          <div className="max-w-7xl mx-auto px-4 h-14 flex items-center gap-6">
            <Link href="/" className="font-bold text-lg tracking-tight">
              FTC<span className="text-blue-500">Stats</span>
            </Link>
            <nav className="flex gap-4 text-sm text-muted-foreground">
              <Link href="/" className="hover:text-foreground transition-colors">Teams</Link>
              <Link href="/events" className="hover:text-foreground transition-colors">Events</Link>
            </nav>
          </div>
        </header>
        <main className="flex-1 max-w-7xl mx-auto w-full px-4 py-8">
          {children}
        </main>
        <footer className="border-t border-border py-4 text-center text-xs text-muted-foreground">
          FTC Stats · Data from FIRST Tech Challenge API · Not affiliated with FIRST
        </footer>
      </body>
    </html>
  );
}
