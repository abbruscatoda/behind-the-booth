"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Suspense, useEffect, useState, type ReactNode } from "react";

type Props = { href: string; className: string; children: ReactNode; prefetch?: boolean };

function CurrentHeaderLink({ href, className, children, prefetch }: Props) {
  const pathname = usePathname();
  const [hash, setHash] = useState("");
  const [targetPath, targetHash] = href.split("#");

  useEffect(() => {
    if (!targetHash) return;
    const sync = () => setHash(window.location.hash);
    const followLink = (event: MouseEvent) => {
      if (event.button !== 0 || event.metaKey || event.ctrlKey || event.altKey || event.shiftKey || !(event.target instanceof Element)) return;
      const anchor = event.target.closest("a");
      if (!anchor || (anchor.target && anchor.target !== "_self")) return;
      const destination = new URL(anchor.href);
      if (destination.origin === window.location.origin) setHash(destination.hash);
    };
    sync();
    window.addEventListener("hashchange", sync);
    window.addEventListener("popstate", sync);
    // Next can change a same-page hash through history without a hashchange event.
    window.addEventListener("click", followLink);
    return () => {
      window.removeEventListener("hashchange", sync);
      window.removeEventListener("popstate", sync);
      window.removeEventListener("click", followLink);
    };
  }, [pathname, targetHash]);

  const exact = pathname === targetPath;
  const active = targetHash
    ? exact && hash === `#${targetHash}`
    : exact || pathname.startsWith(`${targetPath}/`);

  return <Link href={href} prefetch={prefetch} className={className}
    aria-current={active ? (exact && !targetHash ? "page" : "location") : undefined}>
    {children}
  </Link>;
}

/** Unknown dynamic market slugs must not suspend the rest of the header. */
export default function HeaderNavLink(props: Props) {
  return <Suspense fallback={<Link {...props} />}><CurrentHeaderLink {...props} /></Suspense>;
}
