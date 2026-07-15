import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Carbon Credit Buyer Intelligence · Xynteo",
  description: "Search carbon projects, identify likely buyers, estimate volumes, and generate market intelligence.",
  icons: {
    icon: "/favicon-32x32.png",
    apple: "/apple-touch-icon.png",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-background text-foreground antialiased">
        {/* Xynteo brand bar — white logo on navy, vivid accent rule */}
        <header className="brand-bar sticky top-0 z-40">
          <div className="mx-auto flex h-14 max-w-[1400px] items-center px-4 md:px-6">
            <a href="/" className="flex items-center gap-3" title="Xynteo — home">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src="/xynteo-logo.svg" alt="Xynteo" width={110} height={28} className="h-7 w-auto" />
              <span className="hidden h-5 w-px bg-white/25 sm:block" />
              <span className="hidden text-sm font-medium tracking-tight text-white/85 sm:block">
                Carbon Credit Buyer Intelligence
              </span>
            </a>
          </div>
          <div className="brand-rule h-[3px] w-full" />
        </header>
        {children}
      </body>
    </html>
  );
}
