import { CircleCheck, Inbox, LoaderCircle, TriangleAlert, X } from "lucide-react";

export function ErrorBanner({ message, onClose }: { message: string | null; onClose?: () => void }) {
  if (!message) return null;
  return (
    <div className="animate-fade-in mb-5 flex items-start gap-3 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-800 ring-1 ring-red-600/10">
      <TriangleAlert className="mt-0.5 size-4 shrink-0 text-red-500" />
      <span className="flex-1">{message}</span>
      {onClose && (
        <button className="text-red-400 hover:text-red-700" onClick={onClose} aria-label="Zamknij">
          <X className="size-4" />
        </button>
      )}
    </div>
  );
}

export function InfoBanner({ message, onClose }: { message: string | null; onClose?: () => void }) {
  if (!message) return null;
  return (
    <div className="animate-fade-in mb-5 flex items-start gap-3 rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-800 ring-1 ring-emerald-600/10">
      <CircleCheck className="mt-0.5 size-4 shrink-0 text-emerald-500" />
      <span className="flex-1">{message}</span>
      {onClose && (
        <button className="text-emerald-400 hover:text-emerald-700" onClick={onClose} aria-label="Zamknij">
          <X className="size-4" />
        </button>
      )}
    </div>
  );
}

export function Loading() {
  return (
    <div className="flex items-center justify-center gap-2 py-16 text-sm text-zinc-500">
      <LoaderCircle className="size-4 animate-spin" /> Ładowanie…
    </div>
  );
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-14 text-center">
      <div className="mb-3 flex size-11 items-center justify-center rounded-xl bg-zinc-100 text-zinc-400">
        <Inbox className="size-5" />
      </div>
      <div className="text-sm font-medium text-zinc-700">{title}</div>
      {hint && <div className="mt-1 text-sm text-zinc-500">{hint}</div>}
    </div>
  );
}

export function PageHeader({ title, subtitle, children }: { title: string; subtitle?: string; children?: React.ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-zinc-900">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-zinc-500">{subtitle}</p>}
      </div>
      <div className="flex flex-wrap items-center gap-2">{children}</div>
    </div>
  );
}
