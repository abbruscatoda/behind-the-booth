"use client";

import { useEffect, useId, useRef, type ReactNode } from "react";

export default function ConfirmationDialog({ title, description, children, confirmLabel, busy, error, onConfirm, onCancel }: {
  title: string;
  description: string;
  children: ReactNode;
  confirmLabel: string;
  busy: boolean;
  error: string;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const cancelRef = useRef<HTMLButtonElement>(null);
  const titleId = useId();
  const descriptionId = useId();

  useEffect(() => {
    const dialog = dialogRef.current;
    const previousOverflow = document.body.style.overflow;
    const previousFocus = document.activeElement;
    document.body.style.overflow = "hidden";
    if (dialog && !dialog.open) dialog.showModal();
    cancelRef.current?.focus({ preventScroll: true });
    return () => {
      if (dialog?.open) dialog.close();
      document.body.style.overflow = previousOverflow;
      if (previousFocus instanceof HTMLElement && previousFocus.isConnected && !previousFocus.matches(":disabled")) {
        previousFocus.focus({ preventScroll: true });
      }
    };
  }, []);

  function cancel() {
    if (!busy) dialogRef.current?.close();
  }

  return (
    <dialog ref={dialogRef} role="alertdialog" aria-labelledby={titleId} aria-describedby={descriptionId} aria-busy={busy}
      onClose={event => { if (!event.currentTarget.open) onCancel(); }}
      onCancel={event => { if (busy) event.preventDefault(); }}
      onClick={event => { if (event.target === event.currentTarget) cancel(); }}
      className="fixed inset-0 m-auto max-h-[90dvh] w-[calc(100%-2rem)] max-w-2xl overflow-hidden rounded-sm border border-[#252521]/30 bg-[#FFFCF6] p-0 text-[#252521] shadow-2xl backdrop:bg-[#252521]/60 open:flex open:flex-col">
      <div className="confirmation-dialog-header grid shrink-0 grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-2 border-b border-[#252521]/20 px-4 py-3 sm:px-7 sm:py-4">
        <p className="heritage-label">Confirmation</p>
        <button type="button" onClick={cancel} disabled={busy} aria-label="Close confirmation"
          className="min-h-11 rounded-sm border border-[#252521]/25 px-3 py-2 text-sm font-semibold text-[#07472B] hover:bg-[#E9E7DA] disabled:cursor-wait disabled:opacity-50">Close <span aria-hidden="true">×</span></button>
        <h2 id={titleId} className="confirmation-dialog-title col-span-2 font-serif text-xl font-bold leading-tight sm:text-3xl">{title}</h2>
      </div>

      <div tabIndex={0} role="region" aria-label="Decision details"
        className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 py-5 [overflow-wrap:anywhere] sm:px-7 sm:py-6">
        <p id={descriptionId} className="text-sm leading-relaxed text-[#55554E]">{description}</p>
        <div className="mt-4">{children}</div>
      </div>

      <div className="confirmation-dialog-footer shrink-0 border-t border-[#252521]/20 px-4 py-3 sm:px-7 sm:py-4">
        {error && <p role="alert" className="mb-3 border-l-2 border-[#9B3E35] bg-[#F4F0E6] px-3 py-2 text-sm text-[#9B3E35]">{error}</p>}
        <div className="grid gap-3 sm:flex sm:items-center sm:justify-between">
          <button ref={cancelRef} type="button" onClick={cancel} disabled={busy}
            className="min-h-11 rounded-sm border border-[#07472B] px-4 py-2 text-sm font-semibold text-[#07472B] hover:bg-[#E9E7DA] disabled:cursor-wait disabled:opacity-50">Cancel</button>
          <button type="button" onClick={onConfirm} disabled={busy} className="heritage-button min-h-11 disabled:cursor-wait disabled:opacity-50">{busy ? "Saving…" : confirmLabel}</button>
        </div>
      </div>
    </dialog>
  );
}
