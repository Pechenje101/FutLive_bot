'use client'

import { useState, useEffect, useCallback } from 'react'

const LANGUAGES = [
  { flag: '🇷🇺', name: 'Русский' },
  { flag: '🇬🇧', name: 'English' },
  { flag: '🇩🇪', name: 'Deutsch' },
  { flag: '🇪🇸', name: 'Español' },
  { flag: '🇮🇹', name: 'Italiano' },
  { flag: '🇫🇷', name: 'Français' },
  { flag: '🇵🇹', name: 'Português' },
  { flag: '🌍', name: 'Other' },
]

const SPORTS = [
  { id: 0, name: 'Футбол', icon: '⚽' },
  { id: 1, name: 'Хоккей', icon: '🏒' },
  { id: 2, name: 'Баскетбол', icon: '🏀' },
  { id: 3, name: 'Теннис', icon: '🎾' },
]

interface MatchData {
  title: string
  time: string
  status: string
  league: string
  url: string
  embed: string
  acestreams: string[]
}

export default function FutLiveApp() {
  const [activeTab, setActiveTab] = useState<'player' | 'matches'>('player')
  const [matchData, setMatchData] = useState<MatchData>({
    title: 'Выберите матч',
    time: '',
    status: '',
    league: '',
    url: '',
    embed: '',
    acestreams: [],
  })
  const [currentSport, setCurrentSport] = useState(0)
  const [toast, setToast] = useState<{ message: string; type: string } | null>(null)
  const [showPlayer, setShowPlayer] = useState(false)
  const [playerError, setPlayerError] = useState(false)

  const showToast = (message: string, type: string = '') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 3000)
  }

  // Open in Ace Player
  const openAcePlayer = useCallback((link: string) => {
    const contentId = link.replace('acestream://', '')
    const isAndroid = /android/i.test(navigator.userAgent)
    const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent)

    if (isAndroid) {
      window.location.href = `intent://${contentId}#Intent;scheme=acestream;package=org.acestream.media;end`
    } else if (isIOS) {
      window.location.href = `acestream://${contentId}`
    } else {
      navigator.clipboard.writeText(link).then(() => {
        showToast('Ссылка скопирована!', 'success')
      })
    }
  }, [])

  // Copy link
  const copyLink = useCallback((link: string) => {
    navigator.clipboard.writeText(link).then(() => {
      showToast('Скопировано!', 'success')
    })
  }, [])

  // Get proxied player URL
  const getProxiedPlayerUrl = useCallback((embedUrl: string) => {
    if (!embedUrl) return ''
    // Use our proxy to fetch the player
    return `/api/player-proxy?url=${encodeURIComponent(embedUrl)}`
  }, [])

  // Initialize from URL params
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const data: MatchData = {
      title: params.get('title') || 'Выберите матч',
      time: params.get('time') || '',
      status: params.get('status') || '',
      league: params.get('league') || '',
      url: params.get('url') || '',
      embed: params.get('embed') || '',
      acestreams: [],
    }

    try {
      const as = params.get('acestreams')
      if (as) data.acestreams = JSON.parse(decodeURIComponent(as))
    } catch {}

    if (data.acestreams.length === 0) {
      const single = params.get('acestream')
      if (single) data.acestreams = [single]
    }

    setMatchData(data)

    // Auto-show player if embed URL exists
    if (data.embed) {
      setShowPlayer(true)
    }
  }, [])

  // Handle iframe error
  const handlePlayerError = useCallback(() => {
    setPlayerError(true)
  }, [])

  // Open on LiveTV
  const openLiveTV = useCallback(() => {
    if (matchData.url) {
      window.open(matchData.url, '_blank')
    }
  }, [matchData.url])

  // Fullscreen player view
  if (showPlayer && matchData.embed) {
    return (
      <div style={{ minHeight: '100vh', background: '#0d0d1a', color: '#fff', fontFamily: 'system-ui, -apple-system, sans-serif' }}>
        {/* Player Header */}
        <header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 14px', background: 'rgba(0,0,0,0.9)', position: 'sticky', top: 0, zIndex: 100 }}>
          <button onClick={() => setShowPlayer(false)} style={{ display: 'flex', alignItems: 'center', gap: 6, background: 'rgba(255,255,255,0.1)', border: 'none', padding: '8px 14px', borderRadius: 8, color: '#fff', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>
            ← Назад
          </button>
          <div style={{ fontSize: 13, fontWeight: 600, maxWidth: '50%', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {matchData.title}
          </div>
          <div style={{ background: matchData.status.includes('LIVE') ? '#c0392b' : '#2980b9', padding: '4px 10px', borderRadius: 12, fontSize: 10, fontWeight: 600 }}>
            {matchData.status.includes('LIVE') ? '🔴 LIVE' : `⏱️ ${matchData.time}`}
          </div>
        </header>

        {/* Match Info */}
        <div style={{ padding: '8px 14px', background: 'rgba(255,255,255,0.03)', textAlign: 'center' }}>
          <div style={{ fontSize: 14, fontWeight: 600 }}>{matchData.title}</div>
          {matchData.league && <div style={{ fontSize: 11, color: '#666', marginTop: 2 }}>🏆 {matchData.league}</div>}
        </div>

        {/* Player Container */}
        <div style={{ position: 'relative', width: '100%', background: '#000' }}>
          <div style={{ position: 'relative', paddingTop: '56.25%' }}>
            {!playerError ? (
              <iframe
                src={getProxiedPlayerUrl(matchData.embed)}
                style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', border: 'none' }}
                allowFullScreen
                allow="autoplay; fullscreen; picture-in-picture"
                onError={handlePlayerError}
              />
            ) : (
              <div style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', background: '#1a1a2e', color: '#888', gap: 16, padding: 20, textAlign: 'center' }}>
                <div style={{ fontSize: 48 }}>⚠️</div>
                <div>Не удалось загрузить плеер</div>
                <button onClick={openLiveTV} style={{ background: '#3498db', color: '#fff', padding: '12px 24px', borderRadius: 10, fontSize: 14, fontWeight: 600, border: 'none', cursor: 'pointer' }}>
                  🌐 Открыть на LiveTV
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Alternative buttons */}
        <div style={{ padding: '12px 14px' }}>
          <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
            <button onClick={openLiveTV} style={{ flex: 1, background: 'rgba(52,152,219,0.2)', color: '#3498db', padding: '12px', borderRadius: 10, fontSize: 13, fontWeight: 600, border: '1px solid rgba(52,152,219,0.3)', cursor: 'pointer' }}>
              🌐 LiveTV
            </button>
            <button onClick={() => { setPlayerError(false); setShowPlayer(false) }} style={{ flex: 1, background: 'rgba(255,255,255,0.1)', color: '#fff', padding: '12px', borderRadius: 10, fontSize: 13, fontWeight: 600, border: 'none', cursor: 'pointer' }}>
              🔄 Перезагрузить
            </button>
          </div>

          {/* Ace Stream Sources */}
          {matchData.acestreams.length > 0 && (
            <div>
              <div style={{ fontSize: 11, color: '#888', marginBottom: 8 }}>🎬 Ace Stream ссылки:</div>
              {matchData.acestreams.slice(0, 4).map((link, i) => {
                const lang = LANGUAGES[i] || LANGUAGES[LANGUAGES.length - 1]
                return (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: 10, background: 'rgba(255,255,255,0.05)', borderRadius: 8, marginBottom: 4 }}>
                    <span style={{ fontSize: 18 }}>{lang.flag}</span>
                    <span style={{ flex: 1, fontSize: 12 }}>{lang.name}</span>
                    <button onClick={() => copyLink(link)} style={{ background: 'rgba(255,255,255,0.1)', border: 'none', padding: '6px', borderRadius: 6, fontSize: 12, cursor: 'pointer' }}>📋</button>
                    <button onClick={() => openAcePlayer(link)} style={{ background: '#e74c3c', color: '#fff', border: 'none', padding: '6px 12px', borderRadius: 6, fontSize: 11, fontWeight: 600, cursor: 'pointer' }}>🚀 Ace</button>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Toast */}
        {toast && (
          <div style={{ position: 'fixed', bottom: 20, left: '50%', transform: 'translateX(-50%)', background: toast.type === 'success' ? '#27ae60' : 'rgba(0,0,0,0.9)', color: '#fff', padding: '10px 20px', borderRadius: 20, fontSize: 13, fontWeight: 500, zIndex: 1000 }}>
            {toast.message}
          </div>
        )}

        <style jsx global>{`
          * { box-sizing: border-box; }
          body { margin: 0; }
        `}</style>
      </div>
    )
  }

  return (
    <div style={{ minHeight: '100vh', background: '#0d0d1a', color: '#fff', fontFamily: 'system-ui, -apple-system, sans-serif' }}>
      {/* Header */}
      <header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', background: 'linear-gradient(180deg, rgba(231,76,60,0.25) 0%, transparent 100%)', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 17, fontWeight: 700 }}>
          <span style={{ fontSize: 24 }}>⚽</span>
          <span>FutLive</span>
        </div>
        <div style={{ background: matchData.status.includes('LIVE') ? '#c0392b' : '#2980b9', padding: '6px 14px', borderRadius: 16, fontSize: 12, fontWeight: 600 }}>
          {matchData.status.includes('LIVE') ? '🔴 LIVE' : `⏱️ ${matchData.time}`}
        </div>
      </header>

      {/* Match Info */}
      {matchData.title !== 'Выберите матч' && (
        <div style={{ padding: '14px 16px', background: 'rgba(255,255,255,0.03)', textAlign: 'center', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
          <div style={{ fontSize: 16, fontWeight: 700 }}>{matchData.title}</div>
          {matchData.league && <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>🏆 {matchData.league}</div>}
        </div>
      )}

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 8, padding: 12, background: 'rgba(0,0,0,0.3)' }}>
        <button onClick={() => setActiveTab('player')} style={{ flex: 1, padding: 12, border: 'none', borderRadius: 12, fontSize: 14, fontWeight: 600, cursor: 'pointer', background: activeTab === 'player' ? '#e74c3c' : 'rgba(255,255,255,0.08)', color: activeTab === 'player' ? '#fff' : '#888' }}>📺 Смотреть</button>
        <button onClick={() => setActiveTab('matches')} style={{ flex: 1, padding: 12, border: 'none', borderRadius: 12, fontSize: 14, fontWeight: 600, cursor: 'pointer', background: activeTab === 'matches' ? '#e74c3c' : 'rgba(255,255,255,0.08)', color: activeTab === 'matches' ? '#fff' : '#888' }}>📋 Матчи</button>
      </div>

      {/* Player Tab */}
      {activeTab === 'player' && (
        <div style={{ padding: '16px' }}>
          {/* Watch Button */}
          {(matchData.embed || matchData.url) && (
            <div onClick={() => matchData.embed ? setShowPlayer(true) : openLiveTV()} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: 16, background: 'linear-gradient(135deg, rgba(46,204,113,0.2) 0%, rgba(39,174,96,0.15) 100%)', borderRadius: 14, marginBottom: 16, border: '2px solid #2ecc71', cursor: 'pointer' }}>
              <div style={{ fontSize: 32 }}>📺</div>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 700, fontSize: 16, color: '#2ecc71' }}>Смотреть трансляцию</div>
                <div style={{ fontSize: 12, color: '#888', marginTop: 4 }}>Открыть плеер</div>
              </div>
              <div style={{ background: '#2ecc71', color: '#fff', padding: '12px 20px', borderRadius: 10, fontSize: 14, fontWeight: 700 }}>▶ Смотреть</div>
            </div>
          )}

          {/* Open on LiveTV */}
          {matchData.url && (
            <div onClick={openLiveTV} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: 14, background: 'rgba(52,152,219,0.15)', borderRadius: 12, marginBottom: 16, border: '1px solid rgba(52,152,219,0.3)', cursor: 'pointer' }}>
              <div style={{ fontSize: 24 }}>🌐</div>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600, fontSize: 14 }}>Открыть на LiveTV.sx</div>
                <div style={{ fontSize: 11, color: '#888' }}>Смотреть на сайте</div>
              </div>
              <div style={{ color: '#3498db', fontSize: 18 }}>→</div>
            </div>
          )}

          {/* Ace Stream Sources */}
          {matchData.acestreams.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 13, color: '#888', marginBottom: 12, fontWeight: 600 }}>🎬 Ace Stream ссылки:</div>
              {matchData.acestreams.map((link, i) => {
                const lang = LANGUAGES[i] || LANGUAGES[LANGUAGES.length - 1]
                return (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: 12, background: 'rgba(255,255,255,0.05)', borderRadius: 10, marginBottom: 6 }}>
                    <div style={{ fontSize: 22 }}>{lang.flag}</div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 600, fontSize: 13 }}>{lang.name}</div>
                      <div style={{ fontSize: 10, color: '#666', marginTop: 1 }}>Ace Stream</div>
                    </div>
                    <button onClick={() => copyLink(link)} style={{ background: 'rgba(255,255,255,0.1)', border: 'none', padding: '8px', borderRadius: 6, fontSize: 14, cursor: 'pointer' }}>📋</button>
                    <button onClick={() => openAcePlayer(link)} style={{ background: '#e74c3c', color: '#fff', padding: '8px 14px', borderRadius: 6, fontSize: 12, fontWeight: 600, border: 'none', cursor: 'pointer' }}>🚀 Ace</button>
                  </div>
                )
              })}
            </div>
          )}

          {/* Help */}
          <div style={{ padding: 14, background: 'rgba(255,255,255,0.03)', borderRadius: 12, fontSize: 13, lineHeight: 1.7 }}>
            <div style={{ fontWeight: 600, marginBottom: 10, color: '#fff' }}>💡 Как смотреть:</div>
            <div style={{ color: '#888' }}>
              <b style={{ color: '#2ecc71' }}>📺 Плеер:</b> Нажмите "Смотреть трансляцию"<br/><br/>
              <b style={{ color: '#3498db' }}>🌐 LiveTV:</b> Откроет официальный сайт<br/><br/>
              <b style={{ color: '#e74c3c' }}>🚀 Ace Player (Android):</b><br/>
              Нажмите 🚀 - откроется приложение
            </div>
          </div>

          {!matchData.embed && !matchData.url && matchData.acestreams.length === 0 && (
            <div style={{ color: '#666', textAlign: 'center', padding: 40, fontSize: 14 }}>Источники не найдены</div>
          )}
        </div>
      )}

      {/* Matches Tab */}
      {activeTab === 'matches' && (
        <div>
          <div style={{ padding: 12, background: 'rgba(255,255,255,0.05)', textAlign: 'center', fontSize: 12, color: '#888' }}>📺 Трансляции LiveTV.sx</div>
          <div style={{ display: 'flex', gap: 6, padding: '10px 14px', overflowX: 'auto' }}>
            {SPORTS.map((sport) => (
              <button key={sport.id} onClick={() => setCurrentSport(sport.id)} style={{ padding: '10px 16px', border: 'none', borderRadius: 24, fontSize: 13, fontWeight: 600, cursor: 'pointer', background: currentSport === sport.id ? '#e74c3c' : 'rgba(255,255,255,0.1)', color: '#fff', whiteSpace: 'nowrap' }}>
                {sport.icon} {sport.name}
              </button>
            ))}
          </div>
          <iframe src={`https://livetv.sx/export/webmasters.php?s=${currentSport}&lang=ru`} style={{ width: '100%', height: '55vh', border: 'none' }} />
        </div>
      )}

      {/* Toast */}
      {toast && (
        <div style={{ position: 'fixed', bottom: 80, left: '50%', transform: 'translateX(-50%)', background: toast.type === 'success' ? '#27ae60' : 'rgba(0,0,0,0.9)', color: '#fff', padding: '12px 24px', borderRadius: 24, fontSize: 14, fontWeight: 500, zIndex: 1000, boxShadow: '0 4px 20px rgba(0,0,0,0.3)' }}>
          {toast.message}
        </div>
      )}

      <style jsx global>{`
        * { box-sizing: border-box; }
        body { margin: 0; }
      `}</style>
    </div>
  )
}
