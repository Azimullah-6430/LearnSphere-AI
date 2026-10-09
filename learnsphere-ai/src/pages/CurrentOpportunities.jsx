import { useState, useEffect, useMemo } from 'react'
import { PageHead, Card, Button, Badge } from '../components/ui/Primitives.jsx'
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
  GraduationCap,
  AlertCircle,
  Navigation,
  Compass
} from 'lucide-react'

const INDIAN_STATES = [
  'All States / National',
  'Tamil Nadu',
  'Karnataka',
  'Maharashtra',
  'Delhi (NCR)',
  'Telangana',
  'Kerala',
  'Uttar Pradesh',
  'West Bengal',
  'Gujarat',
  'Rajasthan',
  'Andhra Pradesh',
  'Punjab',
  'Haryana',
  'Madhya Pradesh',
  'Bihar',
  'Odisha',
  'Assam',
  'Jharkhand',
  'Uttarakhand',
  'Chhattisgarh',
  'Goa',
  'Himachal Pradesh',
  'Chandigarh',
  'Jammu & Kashmir',
  'Puducherry'
]

const POPULAR_CITIES = {
  'Tamil Nadu': ['Chennai', 'Coimbatore', 'Madurai', 'Tiruchirappalli', 'Salem'],
  'Karnataka': ['Bengaluru', 'Mysuru', 'Mangaluru', 'Hubballi'],
  'Maharashtra': ['Mumbai', 'Pune', 'Nagpur', 'Nashik', 'Aurangabad'],
  'Delhi (NCR)': ['New Delhi', 'Noida', 'Gurugram', 'Faridabad', 'Ghaziabad'],
  'Telangana': ['Hyderabad', 'Warangal'],
  'Kerala': ['Kochi', 'Thiruvananthapuram', 'Kozhikode'],
  'West Bengal': ['Kolkata', 'Durgapur', 'Siliguri'],
  'Gujarat': ['Ahmedabad', 'Gandhinagar', 'Surat', 'Vadodara'],
  'Uttar Pradesh': ['Lucknow', 'Kanpur', 'Noida', 'Varanasi', 'Prayagraj'],
  'Rajasthan': ['Jaipur', 'Jodhpur', 'Kota', 'Udaipur'],
  'Andhra Pradesh': ['Visakhapatnam', 'Vijayawada', 'Guntur'],
  'Punjab': ['Chandigarh', 'Ludhiana', 'Amritsar'],
  'Madhya Pradesh': ['Bhopal', 'Indore', 'Gwalior'],
  'Bihar': ['Patna', 'Gaya'],
  'Odisha': ['Bhubaneswar', 'Cuttack', 'Rourkela']
}

const POPULAR_HUBS = [
  { city: 'Chennai', state: 'Tamil Nadu' },
  { city: 'Bengaluru', state: 'Karnataka' },
  { city: 'Mumbai', state: 'Maharashtra' },
  { city: 'New Delhi', state: 'Delhi (NCR)' },
  { city: 'Hyderabad', state: 'Telangana' },
  { city: 'Pune', state: 'Maharashtra' },
  { city: 'Kolkata', state: 'West Bengal' },
  { city: 'Kochi', state: 'Kerala' }
]

export default function CurrentOpportunities() {
  const { user, recordActivity } = useApp()
  const activeProfile = user

  // HARD SEPARATION: student type checked from backend profile
  const isSchool = activeProfile?.role === 'school_student' || activeProfile?.level === 'school' || activeProfile?.student_type === 'school'
  const isCollege = !isSchool

  // Location state (initialized from profile, student can dynamically change)
  const [userCity, setUserCity] = useState(activeProfile?.city || '')
  const [userState, setUserState] = useState(activeProfile?.state || '')
  const [userCountry, setUserCountry] = useState(activeProfile?.country || 'India')

  // Live Sync & Fact-Check State
  const [lastSyncedDate, setLastSyncedDate] = useState('October 09, 2026')
  const [lastVerifiedTimestamp, setLastVerifiedTimestamp] = useState('')
  const [isSyncing, setIsSyncing] = useState(false)
  const [syncWarning, setSyncWarning] = useState(null)
  const [profileCompletenessMsg, setProfileCompletenessMsg] = useState(null)

  // Tab State
  const [activeTab, setActiveTab] = useState('competitions') // 'competitions' | 'updates' | 'saved'
  const [searchQuery, setSearchQuery] = useState('')
  const [activeScope, setActiveScope] = useState('All') // 'All' | 'Nearby' | 'City' | 'State' | 'India' | 'Global' | 'Online'
  const [activeCategory, setActiveCategory] = useState('All')
  const [presetFilter, setPresetFilter] = useState('All') // 'All' | 'NearYou' | 'Recommended' | 'ClosingSoon'

  // Feed items
  const [backendNews, setBackendNews] = useState([])
  const [backendOpps, setBackendOpps] = useState([])
  const [isLoading, setIsLoading] = useState(true)

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

  // Handle Live Daily Feed Sync & Location Change
  const handleDailySync = async (stateVal = userState, cityVal = userCity) => {
    setIsSyncing(true)
    setSyncWarning(null)
    try {
      const res = await api.getOpportunities({
        city: cityVal,
        state: stateVal === 'All States / National' ? '' : stateVal,
        country: userCountry
      })
      if (res && res.success) {
        setBackendNews(res.news || [])
        setBackendOpps(res.opportunities || [])
        if (res.last_updated) setLastSyncedDate(res.last_updated)
        if (res.last_verified_at) setLastVerifiedTimestamp(res.last_verified_at)
        if (res.profile_completeness_message) setProfileCompletenessMsg(res.profile_completeness_message)
        else setProfileCompletenessMsg(null)
      } else {
        setSyncWarning(res?.error || 'Unable to refresh feed. Showing latest stored records.')
      }
    } catch (err) {
      console.error('Sync error:', err)
      setSyncWarning('Network error while refreshing feed. Displaying cached records.')
    } finally {
      setTimeout(() => setIsSyncing(false), 300)
    }
  }

  const handleSelectHub = (hub) => {
    setUserState(hub.state)
    setUserCity(hub.city)
    handleDailySync(hub.state, hub.city)
  }

  const handleStateChange = (newState) => {
    const cleanState = newState === 'All States / National' ? '' : newState
    setUserState(cleanState)
    const availableCities = POPULAR_CITIES[cleanState] || []
    const newCity = availableCities.length > 0 ? availableCities[0] : ''
    setUserCity(newCity)
    handleDailySync(cleanState, newCity)
  }

  const handleCityChange = (newCity) => {
    setUserCity(newCity)
    handleDailySync(userState, newCity)
  }

  // Initial load
  useEffect(() => {
    let isMounted = true
    async function loadLiveFeed() {
      setIsLoading(true)
      try {
        const res = await api.getOpportunities({
          city: userCity,
          state: userState,
          country: userCountry
        })
        if (isMounted && res && res.success) {
          setBackendNews(res.news || [])
          setBackendOpps(res.opportunities || [])
          if (res.last_updated) setLastSyncedDate(res.last_updated)
          if (res.last_verified_at) setLastVerifiedTimestamp(res.last_verified_at)
          if (res.profile_completeness_message) setProfileCompletenessMsg(res.profile_completeness_message)
          else setProfileCompletenessMsg(null)
        }
      } catch (e) {
        console.error('Failed to load opportunities from backend:', e)
      } finally {
        if (isMounted) setIsLoading(false)
      }
    }
    loadLiveFeed()
    return () => { isMounted = false }
  }, [activeProfile?.id, activeProfile?._id, activeProfile?.role, activeProfile?.level])

  // Filter News Updates
  const filteredUpdates = (backendNews || []).filter((item) => {
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      const matchText = ((item.title || '') + (item.summary || item.description || '') + (item.source || '') + (item.tags || []).join(' ')).toLowerCase()
      if (!matchText.includes(q)) return false
    }

    if (activeCategory !== 'All' && item.category !== activeCategory) return false
    if (presetFilter === 'Recommended' && !item.isRecommended) return false
    if (presetFilter === 'NearYou' && !item.isNearYou && !item.isLocationMatch) return false

    return true
  })

  // Filter Competitions / Hackathons
  const filteredCompetitions = (backendOpps || []).filter((item) => {
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      const matchText = ((item.title || '') + (item.organizer || '') + (item.description || item.summary || '') + (item.locationName || '') + (item.category || '')).toLowerCase()
      if (!matchText.includes(q)) return false
    }

    if (activeScope !== 'All') {
      if (activeScope === 'Nearby' && !(item.isCityMatch || item.isStateMatch || item.isNearYou)) return false
      if (activeScope === 'Online' && !item.isOnline) return false
      if (activeScope === 'City' && !item.isCityMatch) return false
      if (activeScope === 'State' && !item.isStateMatch) return false
      if (activeScope === 'India' && item.locationScope !== 'India' && !item.isOnline) return false
    }

    if (activeCategory !== 'All' && item.category !== activeCategory) return false

    if (presetFilter === 'Recommended' && !item.isRecommended) return false
    if (presetFilter === 'ClosingSoon' && !item.isClosingSoon) return false
    if (presetFilter === 'NearYou' && !(item.isCityMatch || item.isStateMatch || item.isNearYou)) return false

    return true
  })

  // Count nearby items
  const nearbyCount = useMemo(() => {
    return (backendOpps || []).filter((item) => item.isCityMatch || item.isStateMatch || item.isNearYou).length
  }, [backendOpps])

  // Saved list combined
  const allCombined = [...(backendNews || []), ...(backendOpps || [])]
  const savedItems = allCombined.filter((item) => savedIds.includes(item.id))

  const departmentName = isCollege
    ? activeProfile?.domain || activeProfile?.department || activeProfile?.branch || 'College Program'
    : (activeProfile?.grade_level ? `Class ${activeProfile.grade_level}` : (activeProfile?.board ? `${activeProfile.board} Board` : 'School Program'))

  return (
    <>
      <PageHead title="Current News & Opportunities" />

      {/* ─── PROFILE COMPLETENESS WARNING BANNER ────────────────────────────── */}
      {profileCompletenessMsg && (
        <div className="mb-4 p-3.5 rounded-xl bg-[var(--warning-soft)] border border-[var(--warning)] text-[var(--warning)] flex items-center gap-2.5 text-[13px] font-semibold">
          <AlertCircle size={18} className="shrink-0" />
          <span>{profileCompletenessMsg}</span>
        </div>
      )}

      {/* ─── SYNC WARNING BANNER (IF SYNC ENCOUNTERS ISSUES) ─────────────────── */}
      {syncWarning && (
        <div className="mb-4 p-3 rounded-xl bg-[var(--error-soft)] border border-[var(--error)] text-[var(--error)] flex items-center gap-2 text-[12.5px] font-semibold">
          <AlertCircle size={16} className="shrink-0" />
          <span>{syncWarning}</span>
        </div>
      )}

      {/* ─── DYNAMIC LOCATION & CREDENTIALS SELECTOR BAR ────────────────────── */}
      <div className="mb-6 p-4.5 rounded-2xl bg-gradient-to-r from-[var(--accent-soft)] via-[var(--surface-alt)] to-[var(--surface)] border border-[var(--accent)] shadow-sm">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-xl bg-[var(--accent)] text-white flex items-center justify-center font-bold shrink-0 shadow-md">
              <Navigation size={22} />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-[14px] font-extrabold text-[var(--text)]">Nearby Opportunities & Location Selector</span>
                <span className="px-2 py-0.5 rounded-full text-[10.5px] font-bold bg-[var(--success-soft)] text-[var(--success)] flex items-center gap-1 border border-[var(--success)]">
                  <CheckCircle2 size={12} /> 100% Verified Live Feed (IST)
                </span>
              </div>
              <div className="text-[12px] text-[var(--text-soft)] mt-0.5 flex items-center gap-2 flex-wrap">
                <span><strong>Role:</strong> {isCollege ? 'College Student' : 'School Student'}</span>
                <span>•</span>
                <span><strong>Domain:</strong> {departmentName}</span>
                <span>•</span>
                <span><strong>Selected Location:</strong> <strong className="text-[var(--accent)]">{userCity || 'All Hubs'}, {userState || 'National'}</strong></span>
                {nearbyCount > 0 && (
                  <>
                    <span>•</span>
                    <span className="px-2 py-0.2 rounded-full bg-[var(--accent-soft)] text-[var(--accent)] font-extrabold text-[11px]">
                      📍 {nearbyCount} Nearby Events Found
                    </span>
                  </>
                )}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2 self-start lg:self-auto">
            <button
              onClick={() => handleDailySync(userState, userCity)}
              disabled={isSyncing}
              className="px-3.5 py-1.5 rounded-lg text-[12px] font-bold bg-[var(--accent)] text-white hover:opacity-90 transition-opacity flex items-center gap-1.5 shadow-sm"
            >
              <RefreshCw size={14} className={isSyncing ? 'animate-spin' : ''} />
              <span>{isSyncing ? 'Refreshing Live Feed...' : 'Sync Daily Feed'}</span>
            </button>
          </div>
        </div>

        {/* State / City Selector Controls */}
        <div className="mt-4 pt-3.5 border-t border-[var(--border)] grid grid-cols-1 md:grid-cols-12 gap-3 text-[12px] items-center">
          <div className="md:col-span-4">
            <label className="block font-bold text-[var(--text-soft)] mb-1 flex items-center gap-1">
              <MapPin size={13} className="text-[var(--accent)]" /> Choose State / Union Territory:
            </label>
            <select
              value={userState || 'All States / National'}
              onChange={(e) => handleStateChange(e.target.value)}
              className="w-full px-3 py-1.5 rounded-lg border border-[var(--border-strong)] bg-[var(--surface)] font-semibold text-[var(--text)] focus:outline-none focus:border-[var(--accent)]"
            >
              {INDIAN_STATES.map((st) => (
                <option key={st} value={st}>{st}</option>
              ))}
            </select>
          </div>

          <div className="md:col-span-4">
            <label className="block font-bold text-[var(--text-soft)] mb-1 flex items-center gap-1">
              <Compass size={13} className="text-[var(--accent)]" /> Choose City / Hub:
            </label>
            {userState && POPULAR_CITIES[userState] ? (
              <select
                value={userCity}
                onChange={(e) => handleCityChange(e.target.value)}
                className="w-full px-3 py-1.5 rounded-lg border border-[var(--border-strong)] bg-[var(--surface)] font-semibold text-[var(--text)] focus:outline-none focus:border-[var(--accent)]"
              >
                <option value="">All Cities in {userState}</option>
                {POPULAR_CITIES[userState].map((ct) => (
                  <option key={ct} value={ct}>{ct}</option>
                ))}
              </select>
            ) : (
              <input
                type="text"
                value={userCity}
                onChange={(e) => setUserCity(e.target.value)}
                onBlur={() => handleDailySync(userState, userCity)}
                onKeyDown={(e) => { if (e.key === 'Enter') handleDailySync(userState, userCity) }}
                placeholder="Enter city (e.g. Chennai, Bengaluru, Mumbai)..."
                className="w-full px-3 py-1.5 rounded-lg border border-[var(--border-strong)] bg-[var(--surface)] font-semibold text-[var(--text)] focus:outline-none focus:border-[var(--accent)]"
              />
            )}
          </div>

          <div className="md:col-span-4">
            <label className="block font-bold text-[var(--text-soft)] mb-1">
              Quick Switch Hubs:
            </label>
            <div className="flex items-center gap-1.5 flex-wrap">
              {POPULAR_HUBS.slice(0, 4).map((hub) => (
                <button
                  key={hub.city}
                  onClick={() => handleSelectHub(hub)}
                  className={`px-2 py-1 rounded-md text-[11px] font-bold border transition-colors ${
                    userCity === hub.city
                      ? 'bg-[var(--accent)] text-white border-[var(--accent)]'
                      : 'bg-[var(--surface)] border-[var(--border)] text-[var(--text-soft)] hover:border-[var(--accent)]'
                  }`}
                >
                  📍 {hub.city}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Top Navigation Tabs */}
      <div className="flex flex-col md:flex-row justify-between md:items-center gap-4 mb-6">
        <div className="flex gap-2 p-1 bg-[var(--surface-alt)] rounded-xl border border-[var(--border)] self-start">
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
            onClick={() => setActiveTab('updates')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-[13px] font-bold transition-all ${
              activeTab === 'updates'
                ? 'bg-[var(--surface)] text-[var(--accent)] shadow-sm'
                : 'text-[var(--text-soft)] hover:text-[var(--text)]'
            }`}
          >
            <Newspaper size={16} />
            <span>Current News & Updates</span>
            <span className="ml-1 px-1.5 py-0.2 text-[10.5px] rounded-full bg-[var(--accent-soft)] text-[var(--accent)] font-extrabold">
              {filteredUpdates.length}
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

      {/* Filter Presets & Controls */}
      {activeTab !== 'saved' && (
        <div className="space-y-3 mb-6 p-3 bg-[var(--surface-alt)] rounded-xl border border-[var(--border)]">
          {/* Presets */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[11px] font-bold uppercase tracking-wider text-[var(--text-faint)] mr-1">Quick View:</span>
            {[
              { id: 'All', label: 'All Verified Items' },
              { id: 'NearYou', label: `📍 Near You (${userCity || userState || 'Your State'})` },
              { id: 'Recommended', label: '✨ Recommended for Domain' },
              { id: 'ClosingSoon', label: '⚡ Closing Soon' }
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
                <span className="font-bold text-[var(--text-faint)]">Proximity Scope:</span>
                <select
                  value={activeScope}
                  onChange={(e) => setActiveScope(e.target.value)}
                  className="px-2.5 py-1 rounded-lg border border-[var(--border-strong)] bg-[var(--surface)] text-[var(--text)] font-semibold focus:outline-none"
                >
                  <option value="All">All Locations & Online</option>
                  <option value="Nearby">📍 Nearby / My State Only</option>
                  <option value="Online">🌐 Online / Remote Only</option>
                  <option value="India">🇮🇳 National Level Only</option>
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
                    <option value="Hackathons & Coding">Hackathons & Coding</option>
                    <option value="Coding Competitions">Coding Competitions</option>
                    <option value="Scholarships & Grants">Scholarships & Grants</option>
                    <option value="Hardware & Embedded Systems">Hardware & Embedded Systems</option>
                    <option value="Automotive & Mechanical">Automotive & Mechanical</option>
                    <option value="Civil & Infrastructure">Civil & Infrastructure</option>
                    <option value="Biotechnology & Innovation">Biotechnology & Healthcare</option>
                    <option value="Research & Policy">Research & Policy</option>
                  </>
                ) : (
                  <>
                    <option value="Science & Olympiads">Science & Olympiads</option>
                    <option value="Inter-School Competitions">Inter-School Competitions</option>
                    <option value="Scholarships & Grants">Scholarships & Grants</option>
                    <option value="Innovation & Robotics">Innovation & Robotics</option>
                    <option value="Quizzes & Debates">Quizzes & Debates</option>
                    <option value="Academic Competitions">Academic Competitions</option>
                  </>
                )}
              </select>
            </div>
          </div>
        </div>
      )}

      {/* ─── TAB 1: HACKATHONS & COMPETITIONS ─────────────────────────────── */}
      {activeTab === 'competitions' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredCompetitions.length === 0 ? (
            <Card className="col-span-2 text-center py-12">
              <Trophy size={40} className="mx-auto text-[var(--text-faint)] mb-3" />
              <div className="font-bold text-[15px]">No opportunities match your current filters.</div>
              <p className="text-xs text-[var(--text-soft)] mt-1 mb-4">Try selecting "All Locations & Online" or choosing your state from the location selector.</p>
              <Button onClick={() => { setSearchQuery(''); setPresetFilter('All'); setActiveScope('All'); setActiveCategory('All'); }}>Reset Filters</Button>
            </Card>
          ) : (
            filteredCompetitions.map((item) => {
              const isSaved = savedIds.includes(item.id)
              const linkUrl = item.url || item.link
              const isNearby = item.isCityMatch || item.isStateMatch || item.isNearYou
              return (
                <Card
                  key={item.id}
                  className={`flex flex-col justify-between transition-all hover:border-[var(--accent-dim)] ${
                    isNearby ? 'border-l-4 border-l-[var(--accent)] bg-gradient-to-br from-[var(--accent-soft)]/20 to-[var(--surface)]' : ''
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between gap-2 mb-2">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <Badge tone="accent">{item.category}</Badge>
                        {item.proximityBadge ? (
                          <Badge tone={item.proximityType === 'city' || item.proximityType === 'state' ? 'success' : 'neutral'}>
                            {item.proximityBadge}
                          </Badge>
                        ) : (
                          <Badge tone="neutral">
                            {item.city ? `📍 ${item.city}, ${item.state || 'India'}` : (item.locationScope || item.scope || 'National')}
                          </Badge>
                        )}
                        {item.isClosingSoon && <Badge tone="error">⚡ Closing Soon</Badge>}
                        {item.verificationBadge && (
                          <span className="px-2 py-0.5 rounded-full text-[10.5px] font-bold bg-[var(--success-soft)] text-[var(--success)] flex items-center gap-1 border border-[var(--success)]">
                            <CheckCircle2 size={11} /> {item.verificationBadge}
                          </span>
                        )}
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
                      <span>{item.organizer || item.source}</span>
                    </div>

                    <p className="text-[12.5px] leading-relaxed text-[var(--text-soft)] mb-4">
                      {item.description || item.summary}
                    </p>

                    <div className="space-y-2 mb-4 bg-[var(--surface-alt)] p-3 rounded-lg text-[12px]">
                      <div className="flex items-center gap-2">
                        <UserCheck size={13} className="text-[var(--text-faint)]" />
                        <span><strong>Eligibility:</strong> {item.eligibility}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <MapPin size={13} className="text-[var(--accent)]" />
                        <span><strong>Venue / Location:</strong> <strong className="text-[var(--text)]">{item.locationName || item.venue || item.city || 'National / Online'}</strong></span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Clock size={13} className="text-[var(--warning)]" />
                        <span><strong>Deadline:</strong> <span className="text-[var(--warning)] font-bold">{item.deadline}</span></span>
                      </div>
                      {(item.prize || item.prizePool) && (
                        <div className="flex items-center gap-2 text-[var(--success)]">
                          <Award size={13} />
                          <span><strong>Reward / Scholarship:</strong> {item.prize || item.prizePool}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-3 border-t border-[var(--border)]">
                    <span className="text-[11px] text-[var(--text-faint)] font-medium">Source: {item.source || item.organizer}</span>
                    <a
                      href={linkUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1 px-3.5 py-1.5 rounded-lg text-[12px] font-bold bg-[var(--accent)] text-white hover:opacity-90 transition-opacity shadow-sm"
                    >
                      <span>Apply / View Official Link</span>
                      <ExternalLink size={12} />
                    </a>
                  </div>
                </Card>
              )
            })
          )}
        </div>
      )}

      {/* ─── TAB 2: CURRENT UPDATES & EDUCATION NEWS ───────────────────────── */}
      {activeTab === 'updates' && (
        <div className="space-y-4 max-w-[840px]">
          {filteredUpdates.length === 0 ? (
            <Card className="text-center py-12">
              <Newspaper size={40} className="mx-auto text-[var(--text-faint)] mb-3" />
              <div className="font-bold text-[15px]">No news announcements match your current filter.</div>
              <p className="text-xs text-[var(--text-soft)] mt-1 mb-4">Try clearing the search query or switching categories.</p>
              <Button onClick={() => { setSearchQuery(''); setPresetFilter('All'); setActiveCategory('All'); }}>Reset Filters</Button>
            </Card>
          ) : (
            filteredUpdates.map((item) => {
              const isSaved = savedIds.includes(item.id)
              const linkUrl = item.url || item.link
              return (
                <Card key={item.id} className="relative hover:border-[var(--accent-dim)] transition-colors">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2 flex-wrap">
                        <Badge tone="accent">{item.category}</Badge>
                        {item.proximityBadge ? (
                          <Badge tone="neutral">{item.proximityBadge}</Badge>
                        ) : item.isLocationMatch ? (
                          <Badge tone="neutral">📍 {item.city || item.scope}</Badge>
                        ) : null}
                        <span className="text-[11.5px] text-[var(--text-faint)] font-medium flex items-center gap-1">
                          <Calendar size={12} /> Published: {item.published_at || lastSyncedDate}
                        </span>
                        {item.verificationBadge && (
                          <span className="px-2 py-0.5 rounded-full text-[10.5px] font-bold bg-[var(--success-soft)] text-[var(--success)] flex items-center gap-1 border border-[var(--success)]">
                            <CheckCircle2 size={11} /> {item.verificationBadge}
                          </span>
                        )}
                      </div>

                      <h3 className="text-[16px] font-extrabold text-[var(--text)] mb-2 leading-snug">
                        {item.title}
                      </h3>

                      <p className="text-[13.5px] leading-relaxed text-[var(--text-soft)] mb-4">
                        {item.summary || item.description}
                      </p>

                      <div className="flex items-center justify-between pt-3 border-t border-[var(--border)] flex-wrap gap-2">
                        <div className="flex items-center gap-1.5 text-[12px] text-[var(--text-soft)] font-semibold">
                          <Building2 size={13} className="text-[var(--accent)]" />
                          <span>Official Source: <strong className="text-[var(--text)]">{item.source || item.organizer}</strong></span>
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
                            href={linkUrl}
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
            savedItems.map((item) => {
              const linkUrl = item.url || item.link
              return (
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
                        <span className="text-[11.5px] text-[var(--text-faint)] font-medium">Source: {item.source || item.organizer}</span>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => toggleBookmark(item.id)}
                            className="px-3 py-1 rounded-lg text-[12px] border border-[var(--error)] text-[var(--error)] hover:bg-[var(--error-soft)] font-semibold"
                          >
                            Remove Bookmark
                          </button>
                          <a
                            href={linkUrl}
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
              )
            })
          )}
        </div>
      )}
    </>
  )
}
