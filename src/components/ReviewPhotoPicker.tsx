"use client";

/* eslint-disable @next/next/no-img-element -- local, re-encoded object URLs */
import { useEffect, useId, useRef, useState } from "react";
import { MAX_REVIEW_PHOTOS, prepareReviewPhoto, type DraftReviewPhoto } from "../lib/reviewPhotos";

export default function ReviewPhotoPicker({ photos, onChange, onPreparing }: {
  photos: DraftReviewPhoto[];
  onChange: (photos: DraftReviewPhoto[]) => void;
  onPreparing: (preparing: boolean) => void;
}) {
  const id = useId();
  const input = useRef<HTMLInputElement>(null);
  const lock = useRef(false);
  const mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  const [preparing, setPreparing] = useState(false);
  const [error, setError] = useState("");
  async function add(files: FileList | null) {
    if (!files?.length || lock.current) return;
    setError("");
    if (files.length + photos.length > MAX_REVIEW_PHOTOS) {
      setError("You can add up to 4 photos. Choose fewer photos or remove one first.");
      if (input.current) input.current.value = "";
      return;
    }
    lock.current = true; setPreparing(true); onPreparing(true);
    const prepared: DraftReviewPhoto[] = [];
    try {
      for (const file of Array.from(files)) prepared.push(await prepareReviewPhoto(file));
      if (!mounted.current) { prepared.forEach(photo => URL.revokeObjectURL(photo.preview)); return; }
      onChange([...photos, ...prepared]);
    } catch (cause) {
      prepared.forEach(photo => URL.revokeObjectURL(photo.preview));
      setError(cause instanceof Error ? cause.message : "Couldn't prepare these photos. Please try again.");
    } finally {
      if (input.current) input.current.value = "";
      lock.current = false; setPreparing(false); onPreparing(false);
    }
  }
  return <fieldset className="mt-8 border-t border-[#252521]/15 pt-6" disabled={preparing}>
    <legend className="font-serif text-xl font-bold">Market photos <span className="font-sans text-xs font-normal text-[#626C57]">Optional</span></legend>
    <p id={`${id}-help`} className="mt-2 text-sm leading-relaxed text-[#55554E]">Add up to 4 photos you took at this market. Photos appear with your approved review; choose images you’re comfortable sharing.</p>
    <label htmlFor={id} className="mt-4 block text-sm font-semibold">Add photos</label>
    <input ref={input} id={id} type="file" accept="image/jpeg,image/png,image/webp,image/heic,image/heif" multiple
      disabled={preparing || photos.length >= MAX_REVIEW_PHOTOS} aria-describedby={`${id}-help ${id}-status`}
      onChange={event => void add(event.target.files)} className="mt-2 block min-h-11 w-full min-w-0 max-w-full text-sm file:mr-3 file:min-h-11 file:border file:border-[#07472B]/40 file:bg-[#FFFCF6] file:px-4 file:font-semibold file:text-[#07472B] disabled:opacity-60" />
    <p id={`${id}-status`} role="status" className="mt-2 text-xs text-[#626C57]">{preparing ? "Preparing photos…" : `${photos.length} of 4 photos selected. JPG, PNG, WebP; up to 20 MB each before resizing.`}</p>
    {error && <p role="alert" className="mt-3 text-sm text-[#9B3E35]">{error}</p>}
    {photos.length > 0 && <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">{photos.map((photo, index) => <div key={photo.id} className="min-w-0 border border-[#252521]/20 bg-[#FFFCF6] p-2">
      <img src={photo.preview} alt={`Selected market photo ${index + 1}`} width={photo.width} height={photo.height} className="aspect-[4/3] w-full object-cover" />
      <label htmlFor={`${id}-${photo.id}`} className="mt-2 block text-xs font-semibold">Caption <span className="font-normal">(optional)</span></label>
      <input id={`${id}-${photo.id}`} value={photo.caption} maxLength={160} onChange={event => onChange(photos.map(item => item.id === photo.id ? { ...item, caption: event.target.value } : item))}
        className="mt-1 min-h-11 w-full min-w-0 border border-[#252521]/25 p-2 text-sm" />
      <button type="button" onClick={() => { URL.revokeObjectURL(photo.preview); onChange(photos.filter(item => item.id !== photo.id)); }} className="mt-1 min-h-11 text-xs font-semibold text-[#9B3E35] underline" aria-label={`Remove photo ${index + 1}`}>Remove photo</button>
    </div>)}</div>}
  </fieldset>;
}
