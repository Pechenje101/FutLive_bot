import { NextRequest, NextResponse } from 'next/server'

// Proxy for LiveTV player - removes X-Frame-Options to allow embedding
export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const playerUrl = searchParams.get('url')

  if (!playerUrl) {
    return new NextResponse('Missing player URL', { status: 400 })
  }

  try {
    console.log('Proxying player:', playerUrl)

    const response = await fetch(playerUrl, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8',
        'Referer': 'https://livetv.sx/',
        'Origin': 'https://livetv.sx',
        'Sec-Fetch-Dest': 'iframe',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-site',
      },
      signal: AbortSignal.timeout(15000),
    })

    if (!response.ok) {
      return new NextResponse(`Upstream error: ${response.status}`, { status: response.status })
    }

    const contentType = response.headers.get('content-type') || 'text/html'
    let content: string | ArrayBuffer

    // Handle different content types
    if (contentType.includes('text/html') || contentType.includes('javascript') || contentType.includes('css')) {
      content = await response.text()

      // If it's HTML, fix relative URLs
      if (contentType.includes('text/html')) {
        try {
          const baseUrl = new URL(playerUrl)
          const baseOrigin = baseUrl.origin
          const basePath = baseUrl.pathname.substring(0, baseUrl.pathname.lastIndexOf('/') + 1)

          // Inject base tag
          if (!content.includes('<base')) {
            content = content.replace(/<head[^>]*>/i, `$&<base href="${baseOrigin}${basePath}">`)
          }

          // Fix relative URLs
          content = content.replace(/(src|href)=["'](?!https?:|\/\/|#|data:|javascript:)([^"']+)["']/gi, 
            `$1="${baseOrigin}$2"`)
        } catch {
          // Keep original content if URL parsing fails
        }
      }
    } else {
      // Binary content (images, etc.)
      content = await response.arrayBuffer()
    }

    // Return content without restrictive headers
    return new NextResponse(content, {
      status: 200,
      headers: {
        'Content-Type': contentType,
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Access-Control-Allow-Headers': '*',
        'Cache-Control': 'public, max-age=60',
      },
    })

  } catch (error: unknown) {
    console.error('Player proxy error:', error)
    const errorMessage = error instanceof Error ? error.message : 'Unknown error'
    
    // Return HTML error page that can be displayed in iframe
    return new NextResponse(`
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="utf-8">
        <style>
          body { 
            font-family: sans-serif; 
            background: #1a1a2e; 
            color: #fff; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
            min-height: 100vh; 
            margin: 0;
            text-align: center;
          }
          .error { padding: 20px; }
          .icon { font-size: 48px; margin-bottom: 16px; }
          a { color: #2ecc71; }
        </style>
      </head>
      <body>
        <div class="error">
          <div class="icon">📺</div>
          <p>Не удалось загрузить плеер</p>
          <p style="color: #888; font-size: 12px;">${errorMessage}</p>
          <p style="margin-top: 16px;">
            <a href="${playerUrl}" target="_blank">Открыть на LiveTV →</a>
          </p>
        </div>
      </body>
      </html>
    `, {
      status: 200,
      headers: {
        'Content-Type': 'text/html; charset=utf-8',
      },
    })
  }
}
