import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, PageHead, Badge, Button } from '../components/ui/Primitives.jsx'
import { useApp } from '../context/AppContext.jsx'
import { api } from '../services/api.js'
import {
  Bell,
  CheckCheck,
  Trash2,
  ExternalLink,
  Flame,
  Award,
  Sparkles,
  BookOpen,
  AlertTriangle,
  Info,
  CheckCircle2,
  RefreshCw
} from 'lucide-react'

function formatRelativeTime(dateInput) {
  if (!dateInput) return 'Recently'
  try {
    const d = new Date(dateInput)
    if (isNaN(d.getTime())) return 'Recently'
    const now = new Date()
    const diffSec = Math.floor((now - d) / 1000)
    if (diffSec < 45) return 'Just now'
    if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`
    if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`
    if (diffSec < 172800) return 'Yesterday'
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
  } catch {
    return 'Recently'
  }
}

function getNotificationIcon(category) {
  switch (category) {
    case 'streak':
    case 'flame':
      return <Flame size={16} className="text-amber-500" />
    case 'success':
    case 'evaluation':
      return <Award size={16} className="text-emerald-500" />
    case 'warning':
      return <AlertTriangle size={16} className="text-amber-500" />
    case 'opportunity':
      return <Sparkles size={16} className="text-indigo-500" />
    case 'curriculum':
      return <BookOpen size={16} className="text-blue-500" />
    default:
      return <Info size={16} className="text-[var(--accent)]" />
  }
}

export default function Notifications() {
  const { user, role } = useApp()
  const navigate = useNavigate()
  const [notifications, setNotifications] = useState([])
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [filter, setFilter] = useState('ALL')
  const [toastMessage, setToastMessage] = useState('')

  const showToast = (msg) => {
    setToastMessage(msg)
    setTimeout(() => setToastMessage(''), 3000)
  }

  const loadNotifications = async () => {
    setLoading(true)
    try {
      const res = await api.getNotifications(role || 'all', user?.name || '')
      if (res && res.success && Array.isArray(res.notifications)) {
        setNotifications(res.notifications)
      } else {
        setNotifications([])
      }
    } catch {
      setNotifications([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadNotifications()
  }, [user, role])

  const handleMarkAsRead = async (notifId, e) => {
    if (e) e.stopPropagation()
    if (!notifId) return
    try {
      const res = await api.markNotificationRead(notifId)
      if (res && res.success) {
        setNotifications((prev) =>
          prev.map((n) => ((n.id || n._id || n.notification_id) === notifId ? { ...n, is_read: true } : n))
        )
      }
    } catch {
      // ignore
    }
  }

  const handleMarkAllRead = async () => {
    setActionLoading(true)
    try {
      const res = await api.markAllNotificationsRead()
      if (res && res.success) {
        setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })))
        showToast('All notifications marked as read.')
      }
    } catch {
      showToast('Failed to mark notifications as read.')
    } finally {
      setActionLoading(false)
    }
  }

  const handleDeleteNotification = async (notifId, e) => {
    if (e) e.stopPropagation()
    if (!notifId) return
    try {
      const res = await api.deleteNotification(notifId)
      if (res && res.success) {
        setNotifications((prev) => prev.filter((n) => (n.id || n._id || n.notification_id) !== notifId))
        showToast('Notification deleted.')
      }
    } catch {
      showToast('Failed to delete notification.')
    }
  }

  const handleClearAll = async () => {
    if (!window.confirm('Are you sure you want to clear all notifications?')) return
    setActionLoading(true)
    try {
      const res = await api.clearNotifications()
      if (res && res.success) {
        setNotifications([])
        showToast('All notifications cleared.')
      }
    } catch {
      showToast('Failed to clear notifications.')
    } finally {
      setActionLoading(false)
    }
  }

  const handleNotificationClick = (n) => {
    const notifId = n.id || n._id || n.notification_id
    if (!n.is_read && notifId) {
      handleMarkAsRead(notifId)
    }
    if (n.action_url) {
      navigate(n.action_url)
    }
  }

  const unreadCount = notifications.filter((n) => !n.is_read).length

  const filteredNotes = notifications.filter((n) => {
    if (filter === 'UNREAD') return !n.is_read
    if (filter === 'READ') return n.is_read
    return true
  })

  return (
    <>
      <PageHead
        title="Notifications"
        action={
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={loadNotifications}
              disabled={loading}
              title="Refresh Notifications"
            >
              <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
              <span className="hidden sm:inline ml-1">Refresh</span>
            </Button>
            {unreadCount > 0 && (
              <Button
                variant="secondary"
                size="sm"
                onClick={handleMarkAllRead}
                disabled={actionLoading}
              >
                <CheckCheck size={14} className="mr-1.5 text-emerald-500" />
                Mark All Read
              </Button>
            )}
            {notifications.length > 0 && (
              <Button
                variant="secondary"
                size="sm"
                onClick={handleClearAll}
                disabled={actionLoading}
                className="text-red-500 hover:text-red-600 hover:bg-red-500/10 border-red-500/30"
              >
                <Trash2 size={14} className="mr-1.5" />
                Clear All
              </Button>
            )}
          </div>
        }
      />

      {toastMessage && (
        <div className="mb-4 px-4 py-2.5 rounded-lg bg-[var(--accent)] text-white text-xs font-semibold shadow-md flex items-center justify-between animate-fadeIn">
          <span>{toastMessage}</span>
          <button onClick={() => setToastMessage('')} className="ml-3 opacity-80 hover:opacity-100">✕</button>
        </div>
      )}

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 mb-4">
        <button
          onClick={() => setFilter('ALL')}
          className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-colors ${
            filter === 'ALL'
              ? 'bg-[var(--accent)] text-white'
              : 'bg-[var(--surface)] text-[var(--text-soft)] border border-[var(--border)] hover:bg-[var(--surface-alt)]'
          }`}
        >
          All ({notifications.length})
        </button>
        <button
          onClick={() => setFilter('UNREAD')}
          className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-colors ${
            filter === 'UNREAD'
              ? 'bg-[var(--accent)] text-white'
              : 'bg-[var(--surface)] text-[var(--text-soft)] border border-[var(--border)] hover:bg-[var(--surface-alt)]'
          }`}
        >
          Unread ({unreadCount})
        </button>
        <button
          onClick={() => setFilter('READ')}
          className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-colors ${
            filter === 'READ'
              ? 'bg-[var(--accent)] text-white'
              : 'bg-[var(--surface)] text-[var(--text-soft)] border border-[var(--border)] hover:bg-[var(--surface-alt)]'
          }`}
        >
          Read ({notifications.length - unreadCount})
        </button>
      </div>

      {loading ? (
        <Card className="p-12 text-center my-6">
          <div className="w-8 h-8 border-3 border-[var(--accent)] border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <div className="text-xs text-[var(--text-faint)]">Loading real-time notifications...</div>
        </Card>
      ) : filteredNotes.length === 0 ? (
        <Card className="p-10 text-center my-6 border-dashed border-2">
          <Bell size={42} className="text-[var(--accent)] mx-auto mb-3 opacity-70" />
          <h3 className="text-base font-bold mb-1">
            {notifications.length === 0 ? 'No Notifications Yet' : 'No notifications in this filter'}
          </h3>
          <p className="text-xs text-[var(--text-soft)] max-w-md mx-auto leading-relaxed">
            {notifications.length === 0
              ? 'You are all caught up! Real-time alerts will appear here when evaluations complete, study streak milestones are reached, or matching competitions are announced.'
              : 'Switch to the All or Read tabs to view previous system notifications.'}
          </p>
        </Card>
      ) : (
        <Card className="p-0 overflow-hidden divide-y divide-[var(--border)]">
          {filteredNotes.map((n, i) => {
            const notifId = n.id || n._id || n.notification_id
            const isRead = !!n.is_read
            return (
              <div
                key={notifId || i}
                onClick={() => handleNotificationClick(n)}
                className={`flex items-start gap-3.5 p-4 transition-colors cursor-pointer group ${
                  isRead ? 'bg-[var(--surface)] hover:bg-[var(--surface-alt)]/60' : 'bg-[var(--accent-soft)]/30 hover:bg-[var(--accent-soft)]/50'
                }`}
              >
                {/* Indicator Dot & Category Icon */}
                <div className="relative shrink-0 mt-0.5">
                  <div className="w-9 h-9 rounded-xl bg-[var(--surface)] border border-[var(--border)] flex items-center justify-center shadow-xs">
                    {getNotificationIcon(n.category)}
                  </div>
                  {!isRead && (
                    <span className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-[var(--accent)] ring-2 ring-[var(--surface)]" />
                  )}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <h4 className={`text-[13.5px] leading-tight ${isRead ? 'font-semibold text-[var(--text)]' : 'font-bold text-[var(--text)]'}`}>
                      {n.title}
                    </h4>
                    <span className="text-[11px] text-[var(--text-faint)] whitespace-nowrap shrink-0">
                      {formatRelativeTime(n.created_at || n.timestamp)}
                    </span>
                  </div>

                  <p className="text-xs text-[var(--text-soft)] mt-1 leading-relaxed">
                    {n.message}
                  </p>

                  {n.action_url && (
                    <div className="mt-2 flex items-center gap-1 text-[11px] font-bold text-[var(--accent)] group-hover:underline">
                      <span>View details</span>
                      <ExternalLink size={12} />
                    </div>
                  )}
                </div>

                {/* Quick Action Controls */}
                <div className="flex items-center gap-1 shrink-0 opacity-80 group-hover:opacity-100 transition-opacity">
                  {!isRead && (
                    <button
                      onClick={(e) => handleMarkAsRead(notifId, e)}
                      title="Mark as read"
                      className="p-1.5 rounded-md text-[var(--text-faint)] hover:text-emerald-500 hover:bg-emerald-500/10 transition-colors"
                    >
                      <CheckCircle2 size={15} />
                    </button>
                  )}
                  <button
                    onClick={(e) => handleDeleteNotification(notifId, e)}
                    title="Delete notification"
                    className="p-1.5 rounded-md text-[var(--text-faint)] hover:text-red-500 hover:bg-red-500/10 transition-colors"
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
              </div>
            )
          })}
        </Card>
      )}
    </>
  )
}
