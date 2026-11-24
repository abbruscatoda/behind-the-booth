"use client";

import HeaderNavLink from "./HeaderNavLink";
import { useRef, useState } from "react";
import BrandLogo from "./BrandLogo";
import AdminHeaderLink from "./AdminHeaderLink";

export default function SiteHeader() {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuButton = useRef<HTMLButtonElement>(null);

  return (
    <>
      <div className="brand-announcement">Independent insight. Better markets.</div>
      <header className="brand-header">
        <nav aria-label="Main navigation" className="brand-navigation" onClick={event => {
          if ((event.target as HTMLElement).closest("a")) setMenuOpen(false);
        }} onKeyDown={event => {
          if (event.key === "Escape" && menuOpen) {
            setMenuOpen(false);
            menuButton.current?.focus();
          }
        }}>
          <BrandLogo />
          <button ref={menuButton} type="button" className="brand-menu-toggle"
            aria-expanded={menuOpen} aria-controls="site-navigation-links"
            onClick={() => setMenuOpen(open => !open)}>
            {menuOpen ? "Close" : "Menu"}
            <span aria-hidden="true">{menuOpen ? "×" : "☰"}</span>
          </button>
          <div id="site-navigation-links" className={`brand-nav-links${menuOpen ? " is-open" : ""}`}>
            <HeaderNavLink href="/markets" className="brand-nav-link">Explore Markets</HeaderNavLink>
            <HeaderNavLink href="/opportunities" className="brand-nav-link">Find Vendor Opportunities</HeaderNavLink>
            <HeaderNavLink href="/suggest-market" className="brand-nav-link">Suggest a Market</HeaderNavLink>
            <HeaderNavLink href="/#about" className="brand-nav-link">Our Mission</HeaderNavLink>
            <AdminHeaderLink />
            <HeaderNavLink href="/login" className="brand-account-link">My Account <svg aria-hidden="true" width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M4 12 12 4M4 4h8v8" /></svg></HeaderNavLink>
          </div>
        </nav>
      </header>
    </>
  );
}
