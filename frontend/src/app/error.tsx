"use client";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="data-card p-8 max-w-md text-center">
        <div
          className="w-10 h-10 rounded-full mx-auto mb-4 flex items-center justify-center"
          style={{
            background: "rgba(191,88,88,0.15)",
            border: "1px solid rgba(191,88,88,0.25)",
          }}
        >
          <span className="text-[var(--accent-red)] text-lg font-bold">!</span>
        </div>
        <h2
          className="text-lg font-semibold mb-2"
          style={{ color: "var(--text-primary)" }}
        >
          Something went wrong
        </h2>
        <p className="text-sm text-[var(--text-secondary)] mb-4">
          {error.message || "An unexpected error occurred"}
        </p>
        <button
          onClick={reset}
          className="px-4 py-2 text-sm font-medium rounded-lg transition-colors"
          style={{
            background: "var(--brand-primary)",
            color: "var(--bg-primary)",
          }}
        >
          Try again
        </button>
      </div>
    </div>
  );
}
