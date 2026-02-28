import { NextRequest, NextResponse } from 'next/server'

// Get embed player URL and try to extract Ace Stream links
export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const eventUrl = searchParams.get('url')

  if (!eventUrl) {
    return NextResponse.json({ error: 'Missing event URL' }, { status: 400 })
  }

  console.log('[LiveTV Player] Processing:', eventUrl)

  // Extract event ID
  const eventIdMatch = eventUrl.match(/eventinfo\/(\d+)/i)
  const eventId = eventIdMatch ? eventIdMatch[1] : null

  // Build possible player URLs
  const playerUrls: string[] = []
  
  if (eventId) {
    playerUrls.push(
      `https://livetv.sx/ltvplayer/index.php?event=${eventId}`,
      `https://cdn.livetv873.me/ltvplayer/index.php?event=${eventId}`,
    )
  }

  let acestreams: string[] = []

  // Try to fetch event page and extract acestreams
  try {
    const response = await fetch(eventUrl, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8',
        'Referer': 'https://livetv.sx/',
      },
      signal: AbortSignal.timeout(15000),
    })

    if (response.ok) {
      const html = await response.text()
      
      // Multiple patterns for acestream IDs
      const patterns = [
        /acestream:\/\/([a-f0-9]{40})/gi,
        /["']([a-f0-9]{40})["']/gi,
        /id["']?\s*[:=]\s*["']([a-f0-9]{40})["']/gi,
      ]

      for (const pattern of patterns) {
        let match
        while ((match = pattern.exec(html)) !== null) {
          const id = match[1]
          if (id && id.length === 40 && /^[a-f0-9]+$/i.test(id)) {
            const aceUrl = `acestream://${id}`
            if (!acestreams.includes(aceUrl)) {
              acestreams.push(aceUrl)
            }
          }
        }
      }

      console.log('[LiveTV Player] Found', acestreams.length, 'acestream links')
    }
  } catch (error) {
    console.log('[LiveTV Player] Fetch failed:', error)
  }

  return NextResponse.json({
    success: true,
    eventId,
    playerUrls,
    acestreams,
    acestreamsCount: acestreams.length,
    eventUrl,
    message: acestreams.length > 0 
      ? `Found ${acestreams.length} Ace Stream sources` 
      : 'Ace Stream links are loaded via JavaScript - use LiveTV directly',
  })
}
