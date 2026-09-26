export default function RouteLoader() {
  return (
    <div className="min-h-[50vh] flex items-center justify-center">
      <div
        className="w-6 h-6 rounded-full border-[2.5px] border-[var(--border-strong)] border-t-[var(--accent)] animate-spin"
        role="status"
        aria-label="Loading"
      />
    </div>
  )
}
