import type { Metadata } from "next";
import { Fraunces, Geist, Geist_Mono } from "next/font/google";
import SiteHeader from "../components/SiteHeader";
import SiteFooter from "../components/SiteFooter";
import "./globals.css";
import { SITE_URL, SITE_DESCRIPTION, pageMetadata } from "../lib/siteMetadata";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });
const fraunces = Fraunces({ variable: "--font-fraunces", subsets: ["latin"], display: "swap" });

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  openGraph: pageMetadata("Know the market before you book", SITE_DESCRIPTION, "/").openGraph,
  twitter: pageMetadata("Know the market before you book", SITE_DESCRIPTION, "/").twitter,
  title: { default: "Behind the Booth | Know the market before you book", template: "%s | Behind the Booth" },
  description: "Discover markets around Raleigh and the Triangle. Read anonymous reviews from verified vendors about booth value, foot traffic, organization, and more.",
  applicationName: "Behind the Booth",
  icons: { icon: "/icon.png", apple: "/icon.png" },
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} ${fraunces.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col">
        <a href="#site-content" className="brand-skip-link">Skip to content</a>
        <SiteHeader />
        <div id="site-content" className="brand-site-content">{children}</div>
        <SiteFooter />
      </body>
    </html>
  );
}
