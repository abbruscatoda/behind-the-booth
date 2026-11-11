import Image from "next/image";
import Link from "next/link";
import wordmark from "../assets/brand/logo-black.png";
import whiteIcon from "../assets/brand/icon-white.png";

export default function BrandLogo({ inverse = false }: { inverse?: boolean }) {
  return (
    <Link href="/" aria-label="Behind the Booth home" className={inverse ? "brand-lockup brand-lockup-inverse" : "brand-lockup"}>
      {inverse ? (
        <>
          <Image src={whiteIcon} alt="" width={56} height={56} className="brand-footer-icon" />
          <span className="brand-footer-name">Behind<br />the Booth<span className="brand-footer-dot">.</span></span>
        </>
      ) : (
        <Image src={wordmark} alt="Behind the Booth" priority sizes="(max-width: 640px) 218px, 270px" className="brand-wordmark" />
      )}
    </Link>
  );
}
