import React from 'react'
import { AlertTriangle, RefreshCw, Home, LogOut } from 'lucide-react'

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null, errorInfo: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error('[ErrorBoundary caught error]:', error, errorInfo)
    this.setState({ errorInfo })

    // If dynamic chunk failed to load (e.g. following a fresh build deployment), auto reload once
    if (
      error?.name === 'ChunkLoadError' ||
      error?.message?.includes('Failed to fetch dynamically imported module') ||
      error?.message?.includes('Importing a module script failed')
    ) {
      const storageKey = 'ls_chunk_reload_ts'
      const lastReload = parseInt(sessionStorage.getItem(storageKey) || '0', 10)
      const now = Date.now()
      if (now - lastReload > 10000) {
        sessionStorage.setItem(storageKey, now.toString())
        window.location.reload()
      }
    }
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null })
  }

  handleReload = () => {
    window.location.reload()
  }

  handleGoHome = () => {
    window.location.href = '/'
  }

  handleHardReset = () => {
    try {
      localStorage.clear()
      sessionStorage.clear()
    } catch {}
    window.location.href = '/'
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }

      return (
        <div className="min-h-screen bg-[var(--bg)] text-[var(--text)] flex items-center justify-center p-6">
          <div className="max-w-md w-full bg-[var(--surface)] border border-[var(--border-strong)] rounded-2xl p-7 shadow-xl text-center space-y-5 animate-fadeIn">
            <div className="w-14 h-14 mx-auto rounded-2xl bg-[var(--error-soft)] text-[var(--error)] flex items-center justify-center">
              <AlertTriangle size={30} />
            </div>

            <div className="space-y-1.5">
              <h2 className="text-xl font-extrabold tracking-tight">Portal Display Notice</h2>
              <p className="text-xs text-[var(--text-soft)] leading-relaxed">
                An unexpected interface error occurred. You can safely reload the portal or return to the sign-in screen without losing your account data.
              </p>
            </div>

            {this.state.error?.message && (
              <div className="p-3 bg-[var(--surface-alt)] border border-[var(--border)] rounded-xl text-left">
                <div className="text-[11px] font-bold text-[var(--text-faint)] uppercase tracking-wider mb-1">
                  Error Details
                </div>
                <div className="text-xs font-mono text-[var(--error)] break-words">
                  {this.state.error.message}
                </div>
              </div>
            )}

            <div className="flex flex-col gap-2 pt-2">
              <button
                onClick={this.handleReload}
                className="w-full py-2.5 px-4 rounded-xl bg-[var(--accent)] text-white font-bold text-xs hover:opacity-90 transition-opacity flex items-center justify-center gap-2 cursor-pointer shadow-sm"
              >
                <RefreshCw size={14} />
                <span>Reload Portal</span>
              </button>

              <button
                onClick={this.handleGoHome}
                className="w-full py-2.5 px-4 rounded-xl border border-[var(--border-strong)] bg-[var(--surface)] font-bold text-xs hover:bg-[var(--surface-alt)] transition-colors flex items-center justify-center gap-2 cursor-pointer"
              >
                <Home size={14} />
                <span>Return to Home</span>
              </button>

              <button
                onClick={this.handleHardReset}
                className="w-full py-2 px-3 text-[11px] text-[var(--text-faint)] hover:text-[var(--error)] transition-colors flex items-center justify-center gap-1.5 cursor-pointer mt-1"
              >
                <LogOut size={12} />
                <span>Clear Local Cache & Sign In</span>
              </button>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
