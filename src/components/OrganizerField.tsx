"use client";

import { useEffect, useState } from "react";
import { createClient } from "../lib/supabase/client";
import { organizerOptions } from "../lib/marketOrganizers";

export default function OrganizerField({ id, value, onChange, disabled = false, hint }: {
  id: string; value: string; onChange: (value: string) => void; disabled?: boolean; hint?: string;
}) {
  const [options, setOptions] = useState<string[]>([]);
  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const { data, error } = await createClient().from("markets").select("organizer").not("organizer", "is", null);
        if (!error && active) setOptions(organizerOptions((data ?? []).map(row => row.organizer)));
      } catch { /* The optional suggestions may fail; typing remains available. */ }
    })();
    return () => { active = false; };
  }, []);
  return <div>
    <label htmlFor={id} className="block text-sm font-semibold">Market organizer (optional)</label>
    <input id={id} list={`${id}-options`} value={value} onChange={e => onChange(e.target.value)}
      disabled={disabled} maxLength={120} autoComplete="off" aria-describedby={`${id}-hint`}
      className="mt-2 w-full rounded-sm border border-[#252521]/25 bg-[#FFFCF6] px-3 py-2.5 text-sm outline-none focus:border-[#07472B] disabled:opacity-60"
      placeholder="e.g. The MAKRS Society or Hummingbird Market" />
    <datalist id={`${id}-options`}>{options.map(name => <option key={name} value={name} />)}</datalist>
    <p id={`${id}-hint`} className="mt-2 text-xs leading-relaxed text-[#626C57]">{hint ?? "Choose an existing name or type a new organizer. Use the same name across its markets. Leave blank if unknown; clear the field to remove the tag. Verify the organizer using an official source."}</p>
  </div>;
}
