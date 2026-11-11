import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import SiteHeader from "../components/SiteHeader";
import SiteFooter from "../components/SiteFooter";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: { default: "Behind the Booth | Know the market before you book", template: "%s | Behind the Booth" },
  description: "Discover markets around Raleigh and the Triangle. Read anonymous reviews from verified vendors about booth value, foot traffic, organization, and more.",
  applicationName: "Behind the Booth",
  icons: { icon: "/icon.png", apple: "/icon.png" },
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col">
        <a href="#site-content" className="brand-skip-link">Skip to content</a>
        <SiteHeader />
        <div id="site-content" className="brand-site-content">{children}</div>
        <SiteFooter />
      </body>
    </html>
  );
}
