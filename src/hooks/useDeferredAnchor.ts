"use client";

import { useEffect, useRef } from "react";

// Profile sections are rendered after asynchronous access/data checks. Let the
// requested section finish rendering before following a URL fragment. Following
// only once prevents later auth refreshes from pulling the reader back down.
export function useDeferredAnchor(id: string, ready: boolean, identity: string) {
  const followed = useRef("");
  useEffect(() => {
    let firstFrame = 0;
    let secondFrame = 0;
    const follow = () => {
      window.cancelAnimationFrame(firstFrame);
      window.cancelAnimationFrame(secondFrame);
      const fragment = window.location.hash;
      let hash: string;
      try { hash = decodeURIComponent(fragment.slice(1)); }
      catch { followed.current = ""; return; }
      if (hash !== id) { followed.current = ""; return; }
      const key = `${identity}:${hash}`;
      if (!ready || followed.current === key) return;
      firstFrame = window.requestAnimationFrame(() => {
        secondFrame = window.requestAnimationFrame(() => {
          const target = document.getElementById(id);
          if (!target || window.location.hash !== fragment) return;
          target.scrollIntoView({ block: "start", behavior: "instant" });
          target.focus({ preventScroll: true });
          followed.current = key;
        });
      });
    };
    follow();
    window.addEventListener("hashchange", follow);
    window.addEventListener("popstate", follow);
    return () => {
      window.cancelAnimationFrame(firstFrame);
      window.cancelAnimationFrame(secondFrame);
      window.removeEventListener("hashchange", follow);
      window.removeEventListener("popstate", follow);
    };
  }, [id, ready, identity]);
}
