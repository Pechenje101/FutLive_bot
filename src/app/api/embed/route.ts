import { NextRequest, NextResponse } from 'next/server'

// Get embed player URL from LiveTV event page
export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const eventUrl = searchParams.get('url')
  
  if (!eventUrl) {
    return NextResponse.json({ error: 'Missing event URL' }, { status: 400 })
  }
  
  try {
    const response = await fetch(eventUrl, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8',
        'Referer': 'https://livetv.sx/',
      }
    })
    
    const html = await response.text()
    
    // Find iframe embed URL - multiple patterns for different LiveTV domains
    const patterns = [
      // Standard ltvplayer pattern
      /src=["']([^"']*ltvplayer[^"']*\.html[^"']*)["']/i,
      // CDN LiveTV pattern
      /src=["']([^"']*cdn\.livetv\d*\.me[^"']*)["']/i,
      // Generic player pattern
      /src=["']([^"']*\/player\/[^"']*)["']/i,
      // Embed pattern
      /src=["'](https?:\/\/[^"']*embed[^"']*)["']/i,
      // Any iframe with player in URL
      /src=["'](https?:\/\/[^"']*player[^"']*)["']/i,
    ]
    
    let embedUrl = null
    
    for (const pattern of patterns) {
      const match = html.match(pattern)
      if (match) {
        embedUrl = match[1]
        // Fix protocol-relative URLs
        if (embedUrl.startsWith('//')) {
          embedUrl = 'https:' + embedUrl
        }
        // Clean up URL (remove extra quotes if any)
        embedUrl = embedUrl.replace(/['"]$/, '')
        console.log('Found embed URL:', embedUrl)
        break
      }
    }
    
    // Also extract acestream links
    const acestreams: string[] = []
    const aceRegex = /acestream:\/\/([a-f0-9]{40})/gi
    let aceMatch
    while ((aceMatch = aceRegex.exec(html)) !== null) {
      acestreams.push(`acestream://${aceMatch[1]}`)
    }
    
    // Try to find alternative embed URLs from onclick handlers or data attributes
    if (!embedUrl) {
      // Look for data attributes
      const dataMatch = html.match(/data-(?:src|embed|url|player)=["']([^"']+)["']/i)
      if (dataMatch) {
        embedUrl = dataMatch[1]
        if (embedUrl.startsWith('//')) {
          embedUrl = 'https:' + embedUrl
        }
      }
    }
    
    // Look for player link in the page (sometimes there's a direct link)
    if (!embedUrl) {
      const linkMatch = html.match(/href=["']([^"']*(?:ltvplayer|player)[^"']*)["']/i)
      if (linkMatch) {
        let url = linkMatch[1]
        if (url.startsWith('//')) {
          url = 'https:' + url
        } else if (url.startsWith('/')) {
          // Relative URL - construct full URL
          const baseUrl = new URL(eventUrl)
          url = `${baseUrl.protocol}//${baseUrl.host}${url}`
        }
        embedUrl = url
      }
    }
    
    return NextResponse.json({
      success: true,
      embedUrl,
      acestreams: [...new Set(acestreams)],
      eventUrl,
      debug: {
        htmlLength: html.length,
        foundEmbed: !!embedUrl,
        acestreamCount: acestreams.length
      }
    })
    
  } catch (error: any) {
    console.error('Embed fetch error:', error)
    return NextResponse.json({ 
      error: 'Failed to fetch embed URL',
      message: error.message
    }, { status: 500 })
  }
}
