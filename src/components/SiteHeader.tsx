import Link from "next/link";
import BrandLogo from "./BrandLogo";

export default function SiteHeader() {
  return (
    <>
      <div className="brand-announcement">Independent insight. Better markets.</div>
      <header className="brand-header">
        <nav aria-label="Main navigation" className="brand-navigation">
          <BrandLogo />
          <div className="brand-nav-links">
            <Link href="/markets" className="brand-nav-link">Explore Markets</Link>
            <Link href="/#about" className="brand-nav-link">Our Mission</Link>
            <Link href="/login" className="brand-account-link">My Account <svg aria-hidden="true" width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M4 12 12 4M4 4h8v8" /></svg></Link>
          </div>
        </nav>
      </header>
    </>
  );
}
