"use client";

/* eslint-disable @next/next/no-img-element -- private storage signed URLs and local previews */
import { useEffect, useId, useRef, useState } from "react";
import { createClient } from "../lib/supabase/client";
import { REVIEW_PHOTO_BUCKET, type ReviewPhoto } from "../lib/reviewPhotos";
import ConfirmationDialog from "./ConfirmationDialog";

type GalleryPhoto = ReviewPhoto & { preview?: string };

function PhotoViewer({ photo, url, onClose }: { photo: GalleryPhoto; url: string; onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const title = useId();
  useEffect(() => {
    const element = dialog.current;
    const focus = document.activeElement;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    if (element && !element.open) element.showModal();
    return () => {
      element?.close(); document.body.style.overflow = overflow;
      if (focus instanceof HTMLElement && focus.isConnected) focus.focus({ preventScroll: true });
    };
  }, []);
  return <dialog ref={dialog} aria-labelledby={title} onClose={event => { if (!event.currentTarget.open) onClose(); }}
    onClick={event => { if (event.target === event.currentTarget) dialog.current?.close(); }}
    className="fixed inset-0 m-auto max-h-[94dvh] w-[calc(100%-1rem)] max-w-4xl overflow-y-auto rounded-sm border border-[#252521]/25 bg-[#FFFCF6] p-3 text-[#252521] shadow-xl backdrop:bg-[#252521]/75 sm:p-5">
    <div className="mb-3 flex items-center justify-between gap-3"><h2 id={title} className="text-sm font-bold">Market photo</h2><button type="button" autoFocus onClick={() => dialog.current?.close()} className="min-h-11 border border-[#07472B]/40 px-4 text-sm font-semibold text-[#07472B]">Close ×</button></div>
    <img src={url} alt={photo.caption || "Photo shared with this vendor review"} width={photo.width} height={photo.height} className="max-h-[72dvh] w-full object-contain" />
    {photo.caption && <p className="mt-3 break-words text-sm">{photo.caption}</p>}
  </dialog>;
}

export default function ReviewPhotoGallery({ photos = [], moderation = false, disabled = false, onModerated }: {
  photos?: GalleryPhoto[];
  moderation?: boolean;
  disabled?: boolean;
  onModerated?: () => void;
}) {
  const [urls, setUrls] = useState<Record<string, string>>({});
  const [loadError, setLoadError] = useState("");
  const [reload, setReload] = useState(0);
  const [selected, setSelected] = useState<GalleryPhoto | null>(null);
  const [decision, setDecision] = useState<GalleryPhoto | null>(null);
  const [overrides, setOverrides] = useState<Record<string, boolean>>({});
  const [busy, setBusy] = useState(false);
  const [decisionError, setDecisionError] = useState("");
  const lock = useRef(false);
  const remotePaths = JSON.stringify(photos.filter(photo => !photo.preview).map(photo => photo.path));
  useEffect(() => {
    let active = true;
    const paths: string[] = JSON.parse(remotePaths);
    if (!paths.length) return;
    async function load() {
      try {
        const { data, error } = await createClient().storage.from(REVIEW_PHOTO_BUCKET).createSignedUrls(paths, 300);
        if (error || data?.some(item => item.error || !item.signedUrl)) throw error || new Error("Photo unavailable");
        if (active) { setUrls(Object.fromEntries((data || []).map(item => [item.path!, item.signedUrl!]))); setLoadError(""); }
      } catch { if (active) setLoadError("Photos couldn't load. Try again."); }
    }
    void load();
    // Renew short-lived links while the page stays open.
    const renewal = setInterval(() => void load(), 240_000);
    return () => { active = false; clearInterval(renewal); };
  }, [remotePaths, reload]);
  const hidden = (photo: GalleryPhoto) => overrides[photo.id] ?? photo.hidden;
  async function confirm() {
    if (!decision || lock.current || disabled) return;
    lock.current = true; setBusy(true); setDecisionError("");
    try {
      const { error } = await createClient().rpc("btb_admin_set_review_photo_visibility", {
        p_photo_id: decision.id, p_hidden: !hidden(decision), p_expected_hidden: hidden(decision),
      });
      if (error) throw error;
      setOverrides(previous => ({ ...previous, [decision.id]: !hidden(decision) }));
      setDecision(null);
      onModerated?.();
    } catch { setDecisionError("Couldn't save the photo decision. Refresh the queue before retrying if someone else changed it."); }
    finally { lock.current = false; setBusy(false); }
  }
  if (!photos.length) return null;
  return <section className="mt-6" aria-label="Review photos">
    <h4 className="text-sm font-semibold">Market photos <span className="font-normal text-[#626C57]">({photos.length})</span></h4>
    {loadError && <p role="alert" className="mt-2 text-sm text-[#9B3E35]">{loadError} <button type="button" onClick={() => { setLoadError(""); setReload(value => value + 1); }} className="min-h-11 font-semibold underline">Reload photos</button></p>}
    <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">{photos.map((photo, index) => {
      const url = photo.preview || urls[photo.path];
      return <figure key={photo.id} className="min-w-0">
        <button type="button" disabled={!url || disabled} onClick={() => setSelected(photo)} aria-label={`Enlarge market photo ${index + 1}${photo.caption ? `: ${photo.caption}` : ""}`}
          className={`block aspect-[4/3] w-full overflow-hidden border border-[#252521]/25 bg-[#E9E7DA] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#07472B] ${hidden(photo) ? "opacity-50" : ""}`}>
          {url ? <img src={url} alt={photo.caption || `Market photo ${index + 1}`} width={photo.width} height={photo.height} loading="lazy" referrerPolicy="no-referrer" onError={() => setLoadError("Photos couldn't load. Try again.")} className="h-full w-full object-cover" /> : <span className="text-xs text-[#626C57]">{loadError ? "Photo unavailable" : "Loading photo…"}</span>}
        </button>
        {photo.caption && <figcaption className="mt-2 break-words text-xs leading-relaxed text-[#55554E]">{photo.caption}</figcaption>}
        {hidden(photo) && <p className="mt-1 text-xs font-semibold text-[#9B3E35]">Hidden from readers</p>}
        {moderation && <button type="button" disabled={busy || disabled} onClick={() => { setDecisionError(""); setDecision(photo); }} className="mt-1 min-h-11 text-xs font-semibold text-[#07472B] underline disabled:opacity-50">{hidden(photo) ? "Restore photo" : "Hide photo"}</button>}
      </figure>;
    })}</div>
    {selected && <PhotoViewer photo={selected} url={selected.preview || urls[selected.path]} onClose={() => setSelected(null)} />}
    {decision && <ConfirmationDialog title={hidden(decision) ? "Restore this photo?" : "Hide this photo?"} description={hidden(decision) ? "This photo will be visible to readers when its review is approved." : "This photo will be hidden from readers. The written review and ratings stay available for moderation."}
      confirmLabel={hidden(decision) ? "Restore photo" : "Hide photo"} busy={busy} error={decisionError} onConfirm={() => void confirm()} onCancel={() => setDecision(null)}>
      {urls[decision.path] && <img src={urls[decision.path]} alt={decision.caption || "Photo selected for moderation"} className="max-h-72 w-full object-contain" />}
      {decision.caption && <p className="mt-3 break-words text-sm">{decision.caption}</p>}
    </ConfirmationDialog>}
  </section>;
}
