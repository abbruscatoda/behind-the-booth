import Link from "next/link";
import type { ReactNode } from "react";

export default function AdminLayout({ children }: { children: ReactNode }) {
  return <>
    <nav aria-label="Admin sections" className="mx-auto flex w-full max-w-6xl flex-wrap gap-x-6 gap-y-3 border-b border-[#252521]/15 px-6 py-5 text-sm font-semibold text-[#07472B]">
      <Link href="/admin" className="underline-offset-4 hover:underline">Moderation queues</Link>
      <Link href="/admin/markets" className="underline-offset-4 hover:underline">Manage Markets →</Link>
    </nav>
    {children}
  </>;
}
