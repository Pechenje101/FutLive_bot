import { NextRequest, NextResponse } from 'next/server'

// Parse LiveTV event page and extract embed player URL
export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const eventUrl = searchParams.get('url')
  
  if (!eventUrl) {
    return NextResponse.json({ error: 'Missing event URL' }, { status: 400 })
  }
  
  try {
    const response = await fetch(eventUrl, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'Cache-Control': 'no-cache',
      },
      redirect: 'follow',
    })
    
    const html = await response.text()
    
    // Find iframe embed URL - multiple patterns to try
    const patterns = [
      // ltvplayer iframe
      /src=["']([^"']*ltvplayer[^"']*)["']/i,
      // cdn.livetv iframe
      /src=["']([^"']*cdn\.livetv[^"']*)["']/i,
      // cache player
      /src=["']([^"']*\/cache\/[^"']*)["']/i,
      // Generic player iframe
      /src=["'](https?:\/\/[^"']*player[^"']*)["']/i,
      // embed iframe
      /src=["'](https?:\/\/[^"']*embed[^"']*)["']/i,
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
        // Make sure it's a full URL
        if (!embedUrl.startsWith('http')) {
          embedUrl = 'https://livetv.sx' + embedUrl
        }
        break
      }
    }
    
    // Also extract acestream links from the page
    const acestreams: string[] = []
    const aceRegex = /acestream:\/\/([a-f0-9]{40})/gi
    let aceMatch
    while ((aceMatch = aceRegex.exec(html)) !== null) {
      acestreams.push(`acestream://${aceMatch[1]}`)
    }
    
    // Extract match title
    const titleMatch = html.match(/<title[^>]*>([^<]*)<\/title>/i)
    const title = titleMatch ? titleMatch[1].replace(' - LiveTV', '').trim() : ''
    
    return NextResponse.json({
      success: true,
      embedUrl,
      acestreams: [...new Set(acestreams)],
      title,
      originalUrl: eventUrl,
      debug: {
        htmlLength: html.length,
        foundEmbed: !!embedUrl,
        aceCount: acestreams.length
      }
    })
    
  } catch (error: any) {
    console.error('Event parse error:', error)
    return NextResponse.json({ 
      error: 'Failed to parse event page',
      message: error.message
    }, { status: 500 })
  }
}
