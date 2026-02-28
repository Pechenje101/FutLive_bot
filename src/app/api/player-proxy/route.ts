import { NextRequest, NextResponse } from 'next/server'

export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl
  const embedUrl = searchParams.get('url')

  if (!embedUrl) {
    return new NextResponse('Missing URL parameter', { status: 400 })
  }

  try {
    // Fetch the player page
    const response = await fetch(embedUrl, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://livetv.sx/',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
      },
    })

    let html = await response.text()

    // Inject base tag for relative URLs
    const baseUrl = new URL(embedUrl).origin

    // Clean up HTML and inject necessary scripts
    html = html.replace('<head>', `<head>
      <base href="${baseUrl}/">
      <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
      <style>
        body { margin: 0; padding: 0; background: #000; overflow: hidden; }
        video { width: 100% !important; height: 100% !important; }
        iframe { width: 100% !important; height: 100% !important; border: none !important; }
        .ad, .ads, [class*="ad-"], [id*="ad-"] { display: none !important; }
      </style>
    `)

    // Remove common ad patterns
    html = html.replace(/<script[^>]*src=["'][^"']*ad[^"']*["'][^>]*><\/script>/gi, '')
    html = html.replace(/<div[^>]*class=["'][^"']*ad[^"']*["'][^>]*>.*?<\/div>/gi, '')
    html = html.replace(/<iframe[^>]*src=["'][^"']*(ads?|banner|doubleclick)[^"']*["'][^>]*>.*?<\/iframe>/gi, '')

    return new NextResponse(html, {
      headers: {
        'Content-Type': 'text/html; charset=utf-8',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET',
        'Access-Control-Allow-Headers': 'Content-Type',
      },
    })
  } catch (error) {
    console.error('Player proxy error:', error)
    return new NextResponse('Failed to fetch player', { status: 500 })
  }
}
