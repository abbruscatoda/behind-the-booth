import Link from "next/link";
import BrandLogo from "./BrandLogo";

export default function SiteFooter() {
  return (
    <footer className="brand-footer">
      <div className="brand-footer-inner">
        <div>
          <BrandLogo inverse />
          <p className="brand-footer-tagline">A better view from behind the booth.</p>
        </div>
        <div className="brand-footer-right">
          <nav aria-label="Footer navigation" className="brand-footer-links">
            <Link href="/markets">Explore Markets</Link>
            <Link href="/login">My Account</Link>
            <Link href="/verify">Vendor Verification</Link>
            <Link href="/community-guidelines">Community Guidelines</Link>
          </nav>
          <p>© 2026 Behind the Booth. · Raleigh, North Carolina</p>
          <p className="brand-footer-note">Independent reviews. Shared experience.</p>
        </div>
      </div>
    </footer>
  );
}
