import type { SupabaseClient } from "@supabase/supabase-js";

export const REVIEW_PHOTO_BUCKET = "review-photos";
export const MAX_REVIEW_PHOTOS = 4;
export const MAX_PHOTO_INPUT_BYTES = 20 * 1024 * 1024;
export const MAX_PHOTO_BYTES = 3 * 1024 * 1024;
export const MAX_PHOTO_EDGE = 2048;

export type DraftReviewPhoto = {
  id: string;
  blob: Blob;
  preview: string;
  width: number;
  height: number;
  caption: string;
};
export type ReviewPhoto = {
  id: string;
  path: string;
  width: number;
  height: number;
  caption: string;
  hidden: boolean;
};

export function photoDimensions(width: number, height: number) {
  if (!Number.isFinite(width) || !Number.isFinite(height) || width < 1 || height < 1) throw new Error("This photo could not be read.");
  const scale = Math.min(1, MAX_PHOTO_EDGE / Math.max(width, height));
  return { width: Math.max(1, Math.round(width * scale)), height: Math.max(1, Math.round(height * scale)) };
}

export function photoInputError(file: Pick<File, "type" | "size">) {
  if (!/^image\/(jpeg|png|webp|heic|heif)$/i.test(file.type)) return "Choose a JPG, PNG, or WebP photo. Convert HEIC photos if your browser cannot open them.";
  if (file.size === 0 || file.size > MAX_PHOTO_INPUT_BYTES) return "Each original photo must be under 20 MB.";
  return null;
}

/** Re-encode decoded pixels, discarding the original filename and EXIF/GPS. */
export async function prepareReviewPhoto(file: File): Promise<DraftReviewPhoto> {
  const error = photoInputError(file);
  if (error) throw new Error(error);
  const source = URL.createObjectURL(file);
  try {
    const image = new Image();
    image.src = source;
    try { await image.decode(); } catch { throw new Error("This photo couldn't be opened. Try saving it as JPG, PNG, or WebP first."); }
    const dimensions = photoDimensions(image.naturalWidth, image.naturalHeight);
    const canvas = document.createElement("canvas");
    Object.assign(canvas, dimensions);
    const context = canvas.getContext("2d");
    if (!context) throw new Error("Your browser couldn't prepare this photo. Try another browser.");
    context.fillStyle = "#FFFCF6";
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.drawImage(image, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise<Blob>((resolve, reject) => canvas.toBlob(
      result => result ? resolve(result) : reject(new Error("This photo couldn't be prepared. Please try another.")), "image/jpeg", 0.82));
    if (blob.size > MAX_PHOTO_BYTES) throw new Error("This photo is still too large. Choose a smaller image.");
    return { id: crypto.randomUUID(), blob, preview: URL.createObjectURL(blob), ...dimensions, caption: "" };
  } finally { URL.revokeObjectURL(source); }
}

export type ReviewUploadAttempt = { id: string; uploaded: Set<string> };

/** The same submission ID survives network retries. Files cannot replace an attached photo. */
export async function submitReviewWithPhotos(
  client: SupabaseClient, userId: string, values: Record<string, unknown>,
  photos: DraftReviewPhoto[], attempt: ReviewUploadAttempt, progress: (message: string) => void,
) {
  if (photos.length > MAX_REVIEW_PHOTOS) throw new Error("You can add up to 4 photos per review.");
  const existing = await client.from("reviews").select("id").eq("id", attempt.id).eq("vendor_id", userId).maybeSingle();
  if (existing.error) throw existing.error;
  if (existing.data) return; // The previous response may have been lost after commit.
  const bucket = client.storage.from(REVIEW_PHOTO_BUCKET);
  const paths = photos.map(photo => `${attempt.id}/${photo.id}.jpg`);
  // Clean old interrupted uploads through Storage's API, preserving this retry.
  const unused = await client.rpc("btb_my_unused_review_photos");
  const stale = ((unused.data || []) as string[]).filter(path => !paths.includes(path));
  if (stale.length) await bucket.remove(stale);
  const abandoned = [...attempt.uploaded].filter(path => !paths.includes(path));
  if (abandoned.length) {
    const cleanup = await bucket.remove(abandoned);
    if (!cleanup.error) abandoned.forEach(path => attempt.uploaded.delete(path));
  }
  for (const [index, photo] of photos.entries()) {
    const path = paths[index];
    if (attempt.uploaded.has(path)) continue;
    progress(`Uploading photo ${index + 1} of ${photos.length}…`);
    const uploaded = await bucket.upload(path, photo.blob, { contentType: "image/jpeg", upsert: false, cacheControl: "60" });
    if (uploaded.error) {
      // A successful upload's response may also have been lost. Only reuse an
      // existing object after the storage API verifies this user's read access.
      const check = await bucket.info(path);
      if (check.error) throw new Error("A photo couldn't upload. Your review is still here; try submitting again or remove that photo.");
    }
    attempt.uploaded.add(path);
  }
  progress("Submitting review…");
  const result = await client.rpc("btb_submit_vendor_review", {
    p_id: attempt.id, p_review: values,
    p_photos: photos.map((photo, index) => ({ path: paths[index], width: photo.width, height: photo.height, caption: photo.caption.trim() })),
  });
  if (result.error) {
    // Check for an already committed result before displaying a retry prompt.
    const confirmed = await client.from("reviews").select("id").eq("id", attempt.id).eq("vendor_id", userId).maybeSingle();
    if (confirmed.data) return;
    if (result.error.code === "23505") throw new Error("You already submitted a review for this market date or event occurrence. Check My Account for its status.");
    if (result.error.code === "42501") throw new Error("You don't currently have permission to submit. Refresh and check your vendor verification status.");
    if (!result.error.code || confirmed.error) throw new Error("We couldn't confirm submission. Your entries are still here. Try submitting again; we'll check for an existing submission first.");
    throw new Error(result.error.message);
  }
}
