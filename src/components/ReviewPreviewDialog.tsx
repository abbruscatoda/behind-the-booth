"use client";

import { useEffect, useId, useRef, type ReactNode } from "react";

export default function ReviewPreviewDialog({ children, busy, error, onClose, onSubmit }: {
  children: ReactNode;
  busy: boolean;
  error: string;
  onClose: () => void;
  onSubmit: () => void;
}) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  const descriptionId = useId();

  useEffect(() => {
    const dialog = dialogRef.current;
    const previousOverflow = document.body.style.overflow;
    const previousFocus = document.activeElement;
    document.body.style.overflow = "hidden";
    if (dialog && !dialog.open) dialog.showModal();
    return () => {
      if (dialog?.open) dialog.close();
      document.body.style.overflow = previousOverflow;
      if (previousFocus instanceof HTMLElement && previousFocus.isConnected && !previousFocus.matches(":disabled")) {
        previousFocus.focus({ preventScroll: true });
      }
    };
  }, []);

  function close() {
    if (!busy) dialogRef.current?.close();
  }

  return (
    <dialog ref={dialogRef} aria-labelledby={titleId} aria-describedby={descriptionId} aria-busy={busy}
      onClose={event => { if (!event.currentTarget.open) onClose(); }}
      onCancel={event => { if (busy) event.preventDefault(); }}
      onClick={event => { if (event.target === event.currentTarget) close(); }}
      className="fixed inset-0 m-auto h-[90dvh] max-h-[90dvh] w-[calc(100%-2rem)] max-w-3xl overflow-hidden rounded-sm border border-[#252521]/30 bg-[#FFFCF6] p-0 text-[#252521] shadow-2xl backdrop:bg-[#252521]/60 open:flex open:flex-col">
      <div className="review-preview-dialog-header grid shrink-0 grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-2 border-b border-[#252521]/20 px-4 py-3 sm:px-7 sm:py-4">
        <p className="heritage-label">Review preview</p>
        <button type="button" onClick={close} disabled={busy} aria-label="Close review preview"
          className="min-h-11 rounded-sm border border-[#252521]/25 px-3 py-2 text-sm font-semibold text-[#07472B] hover:bg-[#E9E7DA] disabled:cursor-wait disabled:opacity-50">
          Close <span aria-hidden="true">×</span>
        </button>
        <h2 id={titleId} className="review-preview-dialog-title col-span-2 font-serif text-xl font-bold leading-tight sm:text-3xl">Review your entries</h2>
        <p id={descriptionId} className="col-span-2 text-xs text-[#626C57]">Not submitted. Check your answers before sending.</p>
      </div>

      <div tabIndex={0} role="region" aria-label="Your review entries"
        className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 py-5 [overflow-wrap:anywhere] sm:px-7 sm:py-6">
        {children}
      </div>

      <div className="review-preview-dialog-footer shrink-0 border-t border-[#252521]/20 px-4 py-3 sm:px-7 sm:py-4">
        {error && <p role="alert" className="mb-3 border-l-2 border-[#9B3E35] bg-[#F4F0E6] px-3 py-2 text-sm text-[#9B3E35]">{error}</p>}
        <div className="grid gap-3 sm:flex sm:items-center sm:justify-between">
          <button type="button" onClick={close} disabled={busy}
            className="min-h-11 rounded-sm border border-[#07472B] px-4 py-2 text-sm font-semibold text-[#07472B] hover:bg-[#E9E7DA] disabled:cursor-wait disabled:opacity-50">Back to editing</button>
          <button type="button" onClick={onSubmit} disabled={busy} className="heritage-button min-h-11 disabled:cursor-wait disabled:opacity-50">
            {busy ? "Submitting..." : "Submit for moderation"}
          </button>
        </div>
      </div>
    </dialog>
  );
}
