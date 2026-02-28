import { NextRequest, NextResponse } from 'next/server'

interface MatchInfo {
  title: string
  time: string
  league: string
  url: string
  sportId: number
  acestreams: string[]
}

// Parse HTML from livetv.sx webmasters API
function parseWebmastersHtml(html: string, sportId: number): MatchInfo[] {
  const matches: MatchInfo[] = []
  
  // Simple regex parsing for match entries
  // The webmasters API returns HTML with match rows
  const matchRegex = /<tr[^>]*class="[^"]*lrow[^"]*"[^>]*>([\s\S]*?)<\/tr>/gi
  let match
  
  while ((match = matchRegex.exec(html)) !== null) {
    const row = match[1]
    
    // Extract title (team names)
    const titleMatch = row.match(/<a[^>]*class="[^"]*lt[^"]*"[^>]*>([^<]+)<\/a>/i)
    const title = titleMatch ? titleMatch[1].trim() : ''
    
    // Extract URL
    const urlMatch = row.match(/href="([^"]+)"/i)
    let url = urlMatch ? urlMatch[1] : ''
    if (url && !url.startsWith('http')) {
      url = 'https://livetv.sx' + url
    }
    
    // Extract time/status
    const timeMatch = row.match(/<td[^>]*class="[^"]*time[^"]*"[^>]*>([^<]+)<\/td>/i)
    const time = timeMatch ? timeMatch[1].trim() : ''
    
    // Extract league
    const leagueMatch = row.match(/<td[^>]*class="[^"]*comp[^"]*"[^>]*>([^<]+)<\/td>/i)
    const league = leagueMatch ? leagueMatch[1].trim() : ''
    
    // Extract acestream links - looking for the [+N] links that show acestream IDs
    const acestreams: string[] = []
    
    // Look for onclick handlers or data attributes with acestream IDs
    const aceRegex = /acestream:\/\/([a-f0-9]+)/gi
    let aceMatch
    while ((aceMatch = aceRegex.exec(row)) !== null) {
      acestreams.push(`acestream://${aceMatch[1]}`)
    }
    
    // Also look for content IDs in various formats
    const contentIdRegex = /contentId["']?\s*[:=]\s*["']([a-f0-9]{40})["']/gi
    while ((aceMatch = contentIdRegex.exec(row)) !== null) {
      const id = `acestream://${aceMatch[1]}`
      if (!acestreams.includes(id)) {
        acestreams.push(id)
      }
    }
    
    if (title && url) {
      matches.push({
        title,
        time,
        league,
        url,
        sportId,
        acestreams
      })
    }
  }
  
  return matches
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const sport = searchParams.get('sport') || '0'
    
    // Fetch from livetv.sx webmasters API
    const response = await fetch(`https://livetv.sx/export/webmasters.php?s=${sport}&lang=ru`, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
      },
    })
    
    if (!response.ok) {
      throw new Error(`Failed to fetch: ${response.status}`)
    }
    
    const html = await response.text()
    const matches = parseWebmastersHtml(html, parseInt(sport))
    
    return NextResponse.json({
      success: true,
      sport: parseInt(sport),
      matches,
      rawLength: html.length
    })
    
  } catch (error: any) {
    console.error('Matches API error:', error)
    
    return NextResponse.json({
      success: false,
      error: error.message,
      matches: []
    }, { status: 500 })
  }
}
