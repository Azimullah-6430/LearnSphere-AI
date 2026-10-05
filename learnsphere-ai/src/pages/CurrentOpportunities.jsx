import { useState, useEffect } from 'react'
import { PageHead, Card, Button, Badge } from '../components/ui/Primitives.jsx'
import { getFactCheckedFeed, currentUpdatesData, opportunitiesData } from '../data/opportunitiesData.js'
import { useApp } from '../context/AppContext.jsx'
import { api } from '../services/api.js'
import {
  Globe,
  Trophy,
  Newspaper,
  Bookmark,
  BookmarkCheck,
  Search,
  ExternalLink,
  Calendar,
  MapPin,
  Clock,
  Sparkles,
  Award,
  Zap,
  Filter,
  CheckCircle2,
  Building2,
  UserCheck,
  RefreshCw,
  Sliders,
  ShieldCheck,
  GraduationCap
} from 'lucide-react'

export default function CurrentOpportunities() {
  const { user, recordActivity } = useApp()
  const activeProfile = user
  // HARD SEPARATION: If role is school_student or level is school, isCollege MUST be false
  const isSchool = activeProfile?.role === 'school_student' || activeProfile?.level === 'school'
  const isCollege = !isSchool && (activeProfile?.role === 'college_student' || activeProfile?.level === 'college')

  // Credentials / Location state derived from user account creation
  const [userCity, setUserCity] = useState(activeProfile?.city || '')
  const [userState, setUserState] = useState(activeProfile?.state || '')
  const [userCountry, setUserCountry] = useState(activeProfile?.country || 'India')
  const [showLocationEditor, setShowLocationEditor] = useState(false)

  // Live Sync & Fact-Check State
  const [lastSyncedDate, setLastSyncedDate] = useState('September 20, 2026')
  const [isSyncing, setIsSyncing] = useState(false)

  // Tab State
  const [activeTab, setActiveTab] = useState('updates') // 'updates' | 'competitions' | 'saved'
  const [searchQuery, setSearchQuery] = useState('')
  const [activeScope, setActiveScope] = useState('All') // 'All' | 'City' | 'State' | 'India' | 'Global' | 'Online'
  const [activeCategory, setActiveCategory] = useState('All')
  const [presetFilter, setPresetFilter] = useState('All') // 'All' | 'Recommended' | 'ClosingSoon' | 'NearYou'

  // User-scoped storage key for saved / bookmarked items
  const userStorageKey = useMemo(() => {
    const uid = activeProfile?.id || activeProfile?._id || (activeProfile?.email ? activeProfile.email.toLowerCase().replace(/[^a-z0-9]/g, '_') : null)
    return uid ? `learnsphere_saved_opps_${uid}` : null
  }, [activeProfile])

  const [savedIds, setSavedIds] = useState([])

  // Re-hydrate bookmarks whenever the authenticated user changes
  useEffect(() => {
    if (!userStorageKey) {
      setSavedIds([])
      return
    }
    try {
      const stored = localStorage.getItem(userStorageKey)
      setSavedIds(stored ? JSON.parse(stored) : [])
    } catch {
      setSavedIds([])
    }
  }, [userStorageKey])

  useEffect(() => {
    if (!userStorageKey) return
    try {
      localStorage.setItem(userStorageKey, JSON.stringify(savedIds))
    } catch (e) {
      console.error(e)
    }
  }, [savedIds, userStorageKey])

  const toggleBookmark = (id) => {
    setSavedIds((prev) => {
      const isSaved = prev.includes(id)
      const next = isSaved ? prev.filter((item) => item !== id) : [...prev, id]
      if (!isSaved) {
        recordActivity('opportunity', `Saved opportunity: ${id}`)
      }
      return next
    })
  }

  // Handle Live Daily Feed Sync
  const handleDailySync = async () => {
    setIsSyncing(true)
    try {
      const res = await api.getOpportunities({
        level: isCollege ? 'college' : 'school',
        city: userCity,
        state: userState,
        country: userCountry,
        department: isCollege ? (activeProfile?.department || 'Computer Science & AI') : (activeProfile?.board || 'CBSE')
      })
      if (res && res.last_updated) {
        setLastSyncedDate(res.last_updated)
      } else {
        setLastSyncedDate(new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' }))
      }
    } catch (err) {
      console.error('Sync error:', err)
    } finally {
      setTimeout(() => setIsSyncing(false), 500)
    }
  }

  // Fetch Fact-Checked Feed
  const { news: factCheckedNews, opps: factCheckedOpps } = getFactCheckedFeed(activeProfile, {
    city: userCity,
    state: userState,
    country: userCountry
  })

  // Filter News Updates
  const filteredUpdates = factCheckedNews.filter((item) => {
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      const matchText = (item.title + item.summary + item.source + (item.tags || []).join(' ')).toLowerCase()
      if (!matchText.includes(q)) return false
    }

    if (activeCategory !== 'All' && item.category !== activeCategory) return false
    if (presetFilter === 'Recommended' && !item.isRecommended) return false
    if (presetFilter === 'NearYou' && !item.isLocationMatch) return false

    return true
  })

  // Filter Competitions / Hackathons
  const filteredCompetitions = factCheckedOpps.filter((item) => {
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      const matchText = (item.title + item.organizer + item.description + item.locationName + item.category).toLowerCase()
      if (!matchText.includes(q)) return false
    }

    if (activeScope !== 'All') {
      if (activeScope === 'Online' && !item.isOnline) return false
      if (activeScope === 'City' && !item.isCityMatch) return false
      if (activeScope === 'State' && !item.isStateMatch) return false
      if (activeScope === 'Global' && item.locationScope !== 'Global') return false
      if (activeScope === 'India' && item.locationScope !== 'India' && item.locationScope !== 'State' && !item.isCityMatch) return false
    }

    if (activeCategory !== 'All' && item.category !== activeCategory) return false

    if (presetFilter === 'Recommended' && !item.isRecommended) return false
    if (presetFilter === 'ClosingSoon' && !item.isClosingSoon) return false
    if (presetFilter === 'NearYou' && !(item.isCityMatch || item.isStateMatch || item.isNearYou)) return false

    return true
  })

  // Saved list combined
  const allCombined = [...factCheckedNews, ...factCheckedOpps]
  const savedItems = allCombined.filter((item) => savedIds.includes(item.id))

  const departmentName = isCollege
    ? activeProfile?.domain || activeProfile?.department || 'College Program'
    : (activeProfile?.grade_level ? `Class ${activeProfile.grade_level}` : (activeProfile?.board ? `${activeProfile.board} Board` : 'School Program'))

  return (
    <>
      <PageHead
        title="Current & Opportunities"
        subtitle={
          isCollege
            ? `Fact-Checked Industry News, Tech Trends, Hackathons & Scholarships matched to your domain (${departmentName}) and location.`
            : `Age-Appropriate Education News, Board Updates, Olympiads & Competitions matched to your curriculum (${departmentName}) and location.`
        }
      />

      {/* ─── CREDENTIALS & LOCATION MATCHING BAR ────────────────────────────── */}
      <div className="mb-6 p-4 rounded-2xl bg-gradient-to-r from-[var(--accent-soft)] via-[var(--surface-alt)] to-[var(--surface)] border border-[var(--accent)] shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="flex items-center gap-3 flex-wrap">
            <div className="w-10 h-10 rounded-xl bg-[var(--accent)] text-white flex items-center justify-center font-bold shrink-0">
              <ShieldCheck size={22} />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-[13.5px] font-extrabold text-[var(--text)]">Personalized Credentials Matcher</span>
                <span className="px-2 py-0.5 rounded-full text-[10.5px] font-bold bg-[var(--success-soft)] text-[var(--success)] flex items-center gap-1 border border-[var(--success)]">
                  <CheckCircle2 size={12} /> 100% Fact-Checked Daily Feed
                </span>
              </div>
              <div className="text-[12.5px] text-[var(--text-soft)] mt-0.5 flex items-center gap-2 flex-wrap">
                <span><strong>Role:</strong> {isCollege ? 'College Student' : 'School Student'}</span>
                <span>•</span>
                <span><strong>Domain/Board:</strong> {departmentName}</span>
                <span>•</span>
                <span><strong>Location:</strong> <span className="text-[var(--accent)] font-bold">{userCity}, {userState}, {userCountry}</span></span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2 self-start md:self-auto">
            <button
              onClick={() => setShowLocationEditor(!showLocationEditor)}
              className="px-3 py-1.5 rounded-lg text-[12px] font-bold border border-[var(--accent)] bg-[var(--surface)] text-[var(--accent)] hover:bg-[var(--accent-soft)] transition-all flex items-center gap-1.5"
            >
              <Sliders size={14} />
              <span>{showLocationEditor ? 'Close Location Editor' : 'Edit Location Credentials'}</span>
            </button>

            <button
              onClick={handleDailySync}
              disabled={isSyncing}
              className="px-3.5 py-1.5 rounded-lg text-[12px] font-bold bg-[var(--accent)] text-white hover:opacity-90 transition-opacity flex items-center gap-1.5 shadow-sm"
            >
              <RefreshCw size={14} className={isSyncing ? 'animate-spin' : ''} />
              <span>{isSyncing ? 'Syncing...' : 'Sync Daily Feed'}</span>
            </button>
          </div>
        </div>

        {/* Expandable Location Customizer */}
        {showLocationEditor && (
          <div className="mt-4 pt-3 border-t border-[var(--border)] grid grid-cols-1 md:grid-cols-3 gap-3 text-[12px]">
            <div>
              <label className="block font-bold text-[var(--text-soft)] mb-1">City (Local News & Competitions):</label>
              <select
                value={userCity}
                onChange={(e) => setUserCity(e.target.value)}
                className="w-full px-3 py-1.5 rounded-lg border border-[var(--border-strong)] bg-[var(--surface)] font-semibold text-[var(--text)]"
              >
                <option value="Chennai">Chennai</option>
                <option value="Bengaluru">Bengaluru</option>
                <option value="Mumbai">Mumbai</option>
                <option value="New Delhi">New Delhi</option>
                <option value="Hyderabad">Hyderabad</option>
                <option value="Pune">Pune</option>
                <option value="Kolkata">Kolkata</option>
              </select>
            </div>

            <div>
              <label className="block font-bold text-[var(--text-soft)] mb-1">State (State Competitions):</label>
              <select
                value={userState}
                onChange={(e) => setUserState(e.target.value)}
                className="w-full px-3 py-1.5 rounded-lg border border-[var(--border-strong)] bg-[var(--surface)] font-semibold text-[var(--text)]"
              >
                <option value="Tamil Nadu">Tamil Nadu</option>
                <option value="Karnataka">Karnataka</option>
                <option value="Maharashtra">Maharashtra</option>
                <option value="Delhi">Delhi / NCR</option>
                <option value="Telangana">Telangana</option>
                <option value="West Bengal">West Bengal</option>
              </select>
            </div>

            <div>
              <label className="block font-bold text-[var(--text-soft)] mb-1">Country / Scope:</label>
              <select
                value={userCountry}
                onChange={(e) => setUserCountry(e.target.value)}
                className="w-full px-3 py-1.5 rounded-lg border border-[var(--border-strong)] bg-[var(--surface)] font-semibold text-[var(--text)]"
              >
                <option value="India">India</option>
                <option value="Worldwide">Worldwide / Global</option>
              </select>
            </div>
          </div>
        )}
      </div>

      {/* Top Navigation Tabs */}
      <div className="flex flex-col md:flex-row justify-between md:items-center gap-4 mb-6">
        <div className="flex gap-2 p-1 bg-[var(--surface-alt)] rounded-xl border border-[var(--border)] self-start">
          <button
            onClick={() => setActiveTab('updates')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-[13px] font-bold transition-all ${
              activeTab === 'updates'
                ? 'bg-[var(--surface)] text-[var(--accent)] shadow-sm'
                : 'text-[var(--text-soft)] hover:text-[var(--text)]'
            }`}
          >
            <Newspaper size={16} />
            <span>Current Updates</span>
            <span className="ml-1 px-1.5 py-0.2 text-[10.5px] rounded-full bg-[var(--accent-soft)] text-[var(--accent)] font-extrabold">
              {filteredUpdates.length}
            </span>
          </button>

          <button
            onClick={() => setActiveTab('competitions')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-[13px] font-bold transition-all ${
              activeTab === 'competitions'
                ? 'bg-[var(--surface)] text-[var(--accent)] shadow-sm'
                : 'text-[var(--text-soft)] hover:text-[var(--text)]'
            }`}
          >
            <Trophy size={16} />
            <span>Hackathons & Competitions</span>
            <span className="ml-1 px-1.5 py-0.2 text-[10.5px] rounded-full bg-[var(--accent-soft)] text-[var(--accent)] font-extrabold">
              {filteredCompetitions.length}
            </span>
          </button>

          <button
            onClick={() => setActiveTab('saved')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-[13px] font-bold transition-all ${
              activeTab === 'saved'
                ? 'bg-[var(--surface)] text-[var(--accent)] shadow-sm'
                : 'text-[var(--text-soft)] hover:text-[var(--text)]'
            }`}
          >
            <Bookmark size={16} />
            <span>Saved ({savedItems.length})</span>
          </button>
        </div>

        {/* Search Bar */}
        <div className="relative min-w-[280px]">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-faint)]" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search news, hackathons, scholarships..."
            className="w-full pl-9 pr-3 py-2 rounded-lg border border-[var(--border-strong)] text-[13px] bg-[var(--surface)] text-[var(--text)] focus:outline-none focus:border-[var(--accent)]"
          />
        </div>
      </div>

      {/* Filter Presets & Controls (Only for Updates or Competitions) */}
      {activeTab !== 'saved' && (
        <div className="space-y-3 mb-6 p-3 bg-[var(--surface-alt)] rounded-xl border border-[var(--border)]">
          {/* Presets */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[11px] font-bold uppercase tracking-wider text-[var(--text-faint)] mr-1">Quick View:</span>
            {[
              { id: 'All', label: 'All Items' },
              { id: 'Recommended', label: '✨ Recommended for You' },
              { id: 'ClosingSoon', label: '⚡ Closing Soon' },
              { id: 'NearYou', label: `📍 Near You (${userCity} / ${userState})` }
            ].map(({ id, label }) => (
              <button
                key={id}
                onClick={() => setPresetFilter(id)}
                className={`px-3 py-1 rounded-full text-[12px] font-bold border transition-all ${
                  presetFilter === id
                    ? 'bg-[var(--accent)] text-white border-[var(--accent)]'
                    : 'bg-[var(--surface)] border-[var(--border)] text-[var(--text-soft)] hover:border-[var(--accent-dim)]'
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Location Scope & Category Selectors */}
          <div className="flex flex-wrap gap-4 pt-2 border-t border-[var(--border)] text-[12px]">
            {activeTab === 'competitions' && (
              <div className="flex items-center gap-2">
                <Globe size={14} className="text-[var(--accent)]" />
                <span className="font-bold text-[var(--text-faint)]">Location Filter:</span>
                <select
                  value={activeScope}
                  onChange={(e) => setActiveScope(e.target.value)}
                  className="px-2.5 py-1 rounded-lg border border-[var(--border-strong)] bg-[var(--surface)] text-[var(--text)] font-semibold focus:outline-none"
                >
                  <option value="All">All Locations</option>
                  <option value="City">City Level ({userCity})</option>
                  <option value="State">State Level ({userState})</option>
                  <option value="India">National (India)</option>
                  <option value="Global">Global / Abroad</option>
                  <option value="Online">Online Only</option>
                </select>
              </div>
            )}

            <div className="flex items-center gap-2">
              <Filter size={14} className="text-[var(--accent)]" />
              <span className="font-bold text-[var(--text-faint)]">Category:</span>
              <select
                value={activeCategory}
                onChange={(e) => setActiveCategory(e.target.value)}
                className="px-2.5 py-1 rounded-lg border border-[var(--border-strong)] bg-[var(--surface)] text-[var(--text)] font-semibold focus:outline-none"
              >
                <option value="All">All Categories</option>
                {isCollege ? (
                  <>
                    <option value="Hackathons">Hackathons</option>
                    <option value="Coding & AI">Coding & AI</option>
                    <option value="City & State Competitions">City & State Competitions</option>
                    <option value="Scholarships & Grants">Scholarships & Grants</option>
                    <option value="Research & Innovation">Research & Innovation</option>
                    <option value="Technology">Technology Trends</option>
                  </>
                ) : (
                  <>
                    <option value="Olympiads & Science">Olympiads & Science</option>
                    <option value="Coding & AI">Coding & AI</option>
                    <option value="City & State Competitions">City & State Competitions</option>
                    <option value="Scholarships & Grants">Scholarships & Grants</option>
                    <option value="Curriculum & Education">Curriculum & Board Updates</option>
                  </>
                )}
              </select>
            </div>
          </div>
        </div>
      )}

      {/* ─── TAB 1: CURRENT UPDATES ─────────────────────────────────────────── */}
      {activeTab === 'updates' && (
        <div className="space-y-4 max-w-[840px]">
          {filteredUpdates.length === 0 ? (
            <Card className="text-center py-12">
              <Newspaper size={40} className="mx-auto text-[var(--text-faint)] mb-3" />
              <div className="font-bold text-[15px]">No updates match your current filters.</div>
              <p className="text-xs text-[var(--text-soft)] mt-1 mb-4">Try clearing your search query or setting Quick View to "All Items".</p>
              <Button onClick={() => { setSearchQuery(''); setPresetFilter('All'); setActiveCategory('All'); }}>Reset Filters</Button>
            </Card>
          ) : (
            filteredUpdates.map((item) => {
              const isSaved = savedIds.includes(item.id)
              return (
                <Card key={item.id} className="relative transition-all hover:border-[var(--accent-dim)]">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2 flex-wrap">
                        <Badge tone="accent">{item.category}</Badge>
                        {item.isRecommended && <Badge tone="warning">✨ Recommended for {departmentName}</Badge>}
                        {item.isLocationMatch && (
                          <Badge tone="neutral">📍 {item.city || item.scope}</Badge>
                        )}
                        <span className="text-[11.5px] text-[var(--text-faint)] font-medium flex items-center gap-1">
                          <Calendar size={12} /> Date: {lastSyncedDate}
                        </span>
                      </div>

                      <h3 className="text-[16px] font-extrabold text-[var(--text)] mb-2 leading-snug">
                        {item.title}
                      </h3>

                      <p className="text-[13.5px] leading-relaxed text-[var(--text-soft)] mb-4">
                        {item.summary}
                      </p>

                      <div className="flex items-center justify-between pt-3 border-t border-[var(--border)] flex-wrap gap-2">
                        <div className="flex items-center gap-1.5 text-[12px] text-[var(--text-soft)] font-semibold">
                          <Building2 size={13} className="text-[var(--accent)]" />
                          <span>Official Source: <strong className="text-[var(--text)]">{item.source}</strong></span>
                        </div>

                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => toggleBookmark(item.id)}
                            className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-[12px] font-semibold border transition-colors ${
                              isSaved
                                ? 'bg-[var(--accent-soft)] text-[var(--accent)] border-[var(--accent)]'
                                : 'border-[var(--border)] text-[var(--text-soft)] hover:bg-[var(--surface-alt)]'
                            }`}
                          >
                            {isSaved ? <BookmarkCheck size={14} /> : <Bookmark size={14} />}
                            {isSaved ? 'Saved' : 'Save'}
                          </button>

                          <a
                            href={item.link}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center gap-1 px-3.5 py-1.5 rounded-lg text-[12px] font-bold bg-[var(--accent)] text-white hover:opacity-90 transition-opacity"
                          >
                            <span>Read Verified Source</span>
                            <ExternalLink size={13} />
                          </a>
                        </div>
                      </div>
                    </div>
                  </div>
                </Card>
              )
            })
          )}
        </div>
      )}

      {/* ─── TAB 2: HACKATHONS & COMPETITIONS ─────────────────────────────── */}
      {activeTab === 'competitions' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredCompetitions.length === 0 ? (
            <Card className="col-span-2 text-center py-12">
              <Trophy size={40} className="mx-auto text-[var(--text-faint)] mb-3" />
              <div className="font-bold text-[15px]">No opportunities match your current filters.</div>
              <p className="text-xs text-[var(--text-soft)] mt-1 mb-4">Try clearing filters or switching location filter to "All Locations".</p>
              <Button onClick={() => { setSearchQuery(''); setPresetFilter('All'); setActiveScope('All'); setActiveCategory('All'); }}>Reset Filters</Button>
            </Card>
          ) : (
            filteredCompetitions.map((item) => {
              const isSaved = savedIds.includes(item.id)
              return (
                <Card key={item.id} className="flex flex-col justify-between transition-all hover:border-[var(--accent-dim)]">
                  <div>
                    <div className="flex items-center justify-between gap-2 mb-2">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <Badge tone="accent">{item.category}</Badge>
                        <Badge tone="neutral">
                          {item.isCityMatch ? `📍 ${item.city}` : item.isStateMatch ? `📍 ${item.state}` : item.locationScope}
                        </Badge>
                        {item.isClosingSoon && <Badge tone="error">⚡ Closing Soon</Badge>}
                      </div>
                      <button
                        onClick={() => toggleBookmark(item.id)}
                        className={`p-1.5 rounded-lg border transition-colors ${
                          isSaved
                            ? 'bg-[var(--accent-soft)] text-[var(--accent)] border-[var(--accent)]'
                            : 'border-[var(--border)] text-[var(--text-faint)] hover:text-[var(--text)]'
                        }`}
                      >
                        {isSaved ? <BookmarkCheck size={16} /> : <Bookmark size={16} />}
                      </button>
                    </div>

                    <h3 className="text-[15.5px] font-extrabold text-[var(--text)] mb-1 leading-snug">
                      {item.title}
                    </h3>

                    <div className="text-[12px] font-semibold text-[var(--text-soft)] mb-3 flex items-center gap-1">
                      <Building2 size={13} className="text-[var(--accent)]" />
                      <span>{item.organizer}</span>
                    </div>

                    <p className="text-[12.5px] leading-relaxed text-[var(--text-soft)] mb-4">
                      {item.description}
                    </p>

                    <div className="space-y-2 mb-4 bg-[var(--surface-alt)] p-3 rounded-lg text-[12px]">
                      <div className="flex items-center gap-2">
                        <UserCheck size={13} className="text-[var(--text-faint)]" />
                        <span><strong>Eligibility:</strong> {item.eligibility}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <MapPin size={13} className="text-[var(--text-faint)]" />
                        <span><strong>Location:</strong> {item.locationName}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Clock size={13} className="text-[var(--warning)]" />
                        <span><strong>Deadline:</strong> <span className="text-[var(--warning)] font-bold">{item.deadline}</span></span>
                      </div>
                      {item.prizePool && (
                        <div className="flex items-center gap-2 text-[var(--success)]">
                          <Award size={13} />
                          <span><strong>Reward / Scholarship:</strong> {item.prizePool}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-3 border-t border-[var(--border)]">
                    <span className="text-[11px] text-[var(--text-faint)] font-medium">Source: {item.source}</span>
                    <a
                      href={item.link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-[12px] font-bold bg-[var(--accent)] text-white hover:opacity-90 transition-opacity"
                    >
                      <span>Apply / View Official Page</span>
                      <ExternalLink size={12} />
                    </a>
                  </div>
                </Card>
              )
            })
          )}
        </div>
      )}

      {/* ─── TAB 3: SAVED BOOKMARKS ─────────────────────────────────────────── */}
      {activeTab === 'saved' && (
        <div className="space-y-4 max-w-[840px]">
          {savedItems.length === 0 ? (
            <Card className="text-center py-12">
              <Bookmark size={40} className="mx-auto text-[var(--text-faint)] mb-3" />
              <div className="font-bold text-[15px]">You haven't saved any opportunities yet.</div>
              <p className="text-xs text-[var(--text-soft)] mt-1 mb-4">Click the "Save" button on any news item or hackathon to bookmark it here for quick access.</p>
            </Card>
          ) : (
            savedItems.map((item) => (
              <Card key={item.id} className="relative">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <Badge tone="accent">{item.category}</Badge>
                      <Badge tone="neutral">{item.level === 'college' ? 'College' : 'School'}</Badge>
                      {item.deadline && <Badge tone="warning">Deadline: {item.deadline}</Badge>}
                    </div>

                    <h3 className="text-[16px] font-extrabold mb-1">{item.title}</h3>
                    <p className="text-[13px] text-[var(--text-soft)] mb-3">{item.summary || item.description}</p>

                    <div className="flex items-center justify-between pt-2 border-t border-[var(--border)]">
                      <span className="text-[11.5px] text-[var(--text-faint)] font-medium">Source: {item.source}</span>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => toggleBookmark(item.id)}
                          className="px-3 py-1 rounded-lg text-[12px] border border-[var(--error)] text-[var(--error)] hover:bg-[var(--error-soft)] font-semibold"
                        >
                          Remove Bookmark
                        </button>
                        <a
                          href={item.link}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-1 px-3 py-1 rounded-lg text-[12px] font-bold bg-[var(--accent)] text-white"
                        >
                          <span>Open Official Link</span>
                          <ExternalLink size={12} />
                        </a>
                      </div>
                    </div>
                  </div>
                </div>
              </Card>
            ))
          )}
        </div>
      )}
    </>
  )
}
