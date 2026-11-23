"use client";

import Image from "next/image";

export default function GoogleSignInButton({ busy, redirecting, onClick }: {
  busy: boolean;
  redirecting: boolean;
  onClick: () => void;
}) {
  return <button type="button" disabled={busy} onClick={onClick}
    className="flex min-h-12 w-full items-center justify-center gap-3 rounded border border-[#747775] bg-white px-4 py-3 text-sm font-medium text-[#1F1F1F] transition-colors hover:bg-[#F2F2F2] focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#07472B] disabled:cursor-wait disabled:opacity-60">
    <Image src="/google-g.png" alt="" width={20} height={20} unoptimized className="h-5 w-5 shrink-0" />
    <span aria-live="polite">{redirecting ? "Opening Google…" : "Continue with Google"}</span>
  </button>;
}
