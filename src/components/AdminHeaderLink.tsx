"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { createClient } from "../lib/supabase/client";

export default function AdminHeaderLink() {
  const identity = useRef<string | null>(null);
  const [userId, setUserId] = useState<string | null>(null);
  const [allowedUserId, setAllowedUserId] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);

  useEffect(() => {
    let active = true;
    let authChanged = false;
    const client = createClient();
    function accept(id: string | null) {
      if (!active) return;
      if (identity.current !== id) {
        identity.current = id;
        setAllowedUserId(null);
        setUserId(id);
      }
    }
    // Keep this callback synchronous; database checks run in the separate effect.
    const { data: { subscription } } = client.auth.onAuthStateChange((event, session) => {
      authChanged = true;
      accept(session?.user.id ?? null);
      if (active && (event === "SIGNED_IN" || event === "TOKEN_REFRESHED" || event === "USER_UPDATED")) {
        setRevision(value => value + 1);
      }
    });
    void client.auth.getUser().then(({ data, error }) => {
      if (active && !authChanged) accept(error ? null : data.user?.id ?? null);
    }).catch(() => {
      if (active && !authChanged) accept(null);
    });
    return () => {
      active = false;
      subscription.unsubscribe();
    };
  }, []);

  useEffect(() => {
    if (!userId) return;
    let active = true;
    setAllowedUserId(null);
    void (async () => {
      try {
        const { data, error } = await createClient().rpc("btb_is_admin");
        if (active && identity.current === userId) {
          setAllowedUserId(!error && data === true ? userId : null);
        }
      } catch {
        if (active && identity.current === userId) setAllowedUserId(null);
      }
    })();
    return () => { active = false; };
  }, [userId, revision]);

  if (!userId || allowedUserId !== userId) return null;
  return <Link href="/admin" prefetch={false} className="brand-nav-link">Admin</Link>;
}
