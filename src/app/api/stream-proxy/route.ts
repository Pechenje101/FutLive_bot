import { NextRequest, NextResponse } from 'next/server'

// Enhanced streaming proxy for LiveTV
// Bypasses X-Frame-Options and handles LiveTV-specific requirements

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

// Cookie storage for session
let sessionCookies: string = ''

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const targetUrl = searchParams.get('url')

  if (!targetUrl) {
    return new NextResponse(JSON.stringify({ error: 'Missing URL parameter' }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' }
    })
  }

  try {
    const url = new URL(targetUrl)
    
    console.log('[Stream Proxy] Fetching:', targetUrl)

    // Enhanced headers to mimic real browser
    const headers: Record<string, string> = {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
      'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
      'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8,de;q=0.7,es;q=0.6',
      'Accept-Encoding': 'gzip, deflate, br',
      'Referer': 'https://livetv.sx/',
      'Origin': 'https://livetv.sx',
      'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
      'Sec-Ch-Ua-Mobile': '?0',
      'Sec-Ch-Ua-Platform': '"Windows"',
      'Sec-Fetch-Dest': 'iframe',
      'Sec-Fetch-Mode': 'navigate',
      'Sec-Fetch-Site': 'same-site',
      'Sec-Fetch-User': '?1',
      'Upgrade-Insecure-Requests': '1',
      'Cache-Control': 'max-age=0',
    }

    // Add session cookies if we have them
    if (sessionCookies) {
      headers['Cookie'] = sessionCookies
    }

    const response = await fetch(targetUrl, {
      headers,
      signal: AbortSignal.timeout(30000),
      redirect: 'follow',
    })

    // Save cookies from response
    const setCookie = response.headers.get('set-cookie')
    if (setCookie) {
      sessionCookies = setCookie.split(',').map(c => c.split(';')[0]).join('; ')
    }

    console.log('[Stream Proxy] Response status:', response.status, response.statusText)

    if (!response.ok) {
      // Try alternative URLs for LiveTV player
      if (targetUrl.includes('ltvplayer') && response.status === 404) {
        const eventId = targetUrl.match(/event=(\d+)/)?.[1]
        if (eventId) {
          // Try different CDN domains
          const alternatives = [
            `https://livetv.sx/ltvplayer/index.php?event=${eventId}`,
            `https://cdn.livetv873.me/ltvplayer/index.php?event=${eventId}`,
            `https://cdn.livetv874.me/ltvplayer/index.php?event=${eventId}`,
            `https://cdn.livetv875.me/ltvplayer/index.php?event=${eventId}`,
          ]
          
          for (const altUrl of alternatives) {
            if (altUrl === targetUrl) continue
            console.log('[Stream Proxy] Trying alternative:', altUrl)
            
            try {
              const altResponse = await fetch(altUrl, {
                headers,
                signal: AbortSignal.timeout(15000),
                redirect: 'follow',
              })
              
              if (altResponse.ok) {
                const html = await altResponse.text()
                return createHtmlResponse(html, altUrl)
              }
            } catch {
              continue
            }
          }
        }
      }
      
      return createErrorResponse(response.status, targetUrl)
    }

    const contentType = response.headers.get('content-type') || 'text/html'
    
    if (contentType.includes('text/html')) {
      const html = await response.text()
      return createHtmlResponse(html, targetUrl)
    }
    
    if (contentType.includes('javascript')) {
      let js = await response.text()
      js = rewriteUrls(js, targetUrl)
      return new NextResponse(js, {
        status: 200,
        headers: createCleanHeaders(contentType),
      })
    }
    
    if (contentType.includes('css')) {
      const css = await response.text()
      return new NextResponse(css, {
        status: 200,
        headers: createCleanHeaders(contentType),
      })
    }
    
    // Binary content
    const buffer = await response.arrayBuffer()
    return new NextResponse(buffer, {
      status: 200,
      headers: {
        ...createCleanHeaders(contentType),
        'Content-Length': String(buffer.byteLength),
      },
    })

  } catch (error: unknown) {
    console.error('[Stream Proxy] Error:', error)
    const errorMessage = error instanceof Error ? error.message : 'Unknown error'
    return createErrorResponse(0, targetUrl, errorMessage)
  }
}

function createCleanHeaders(contentType: string): Record<string, string> {
  return {
    'Content-Type': contentType,
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Access-Control-Allow-Headers': '*',
    'Cache-Control': 'public, max-age=30',
  }
}

function rewriteUrls(content: string, baseUrl: string): string {
  try {
    const url = new URL(baseUrl)
    const origin = url.origin
    
    // Rewrite LiveTV URLs to proxy
    content = content.replace(/(https?:\/\/[^"'\s]*(?:livetv|cdn\.livetv)[^"'\s]*)/gi, 
      (match) => `/api/stream-proxy?url=${encodeURIComponent(match)}`)
    
    // Fix relative URLs
    content = content.replace(/(src|href)=["'](?!https?:|\/\/|#|data:|javascript:|\/api\/)([^"']+)["']/gi,
      `$1="${origin}/$2"`)
    
    return content
  } catch {
    return content
  }
}

function createHtmlResponse(html: string, targetUrl: string): NextResponse {
  try {
    const url = new URL(targetUrl)
    const origin = url.origin
    
    // Remove blocking meta tags
    html = html.replace(/<meta[^>]*(?:x-frame-options|content-security-policy)[^>]*>/gi, '')
    
    // Inject base tag
    if (!html.includes('<base')) {
      html = html.replace(/<head[^>]*>/i, `$&<base href="${origin}/">`)
    }
    
    // Rewrite URLs
    html = rewriteUrls(html, targetUrl)
    
    // Inject helper script
    const injectScript = `
<script>
(function() {
  // Notify parent
  if (window.parent !== window) {
    window.parent.postMessage({ type: 'PLAYER_LOADED', url: '${targetUrl}' }, '*');
  }
  
  // Auto-play videos
  function autoPlay() {
    document.querySelectorAll('video').forEach(function(v) {
      v.play().catch(function(){});
      v.muted = false;
      v.volume = 1;
      v.setAttribute('playsinline', '');
      v.setAttribute('autoplay', '');
    });
  }
  
  document.addEventListener('DOMContentLoaded', autoPlay);
  setTimeout(autoPlay, 1000);
  setTimeout(autoPlay, 3000);
  
  // Handle acestream links
  document.addEventListener('click', function(e) {
    var target = e.target.closest('a[href^="acestream://"]');
    if (target) {
      e.preventDefault();
      var id = target.href.replace('acestream://', '');
      if (window.parent !== window) {
        window.parent.postMessage({ type: 'ACESTREAM_CLICK', id: id, url: 'acestream://' + id }, '*');
      } else {
        window.location.href = 'acestream://' + id;
      }
    }
  });
  
  // Monitor for dynamically added videos
  var observer = new MutationObserver(function(mutations) {
    mutations.forEach(function(mutation) {
      mutation.addedNodes.forEach(function(node) {
        if (node.tagName === 'VIDEO') {
          node.play().catch(function(){});
        }
        if (node.querySelectorAll) {
          node.querySelectorAll('video').forEach(function(v) {
            v.play().catch(function(){});
          });
        }
      });
    });
  });
  observer.observe(document.body, { childList: true, subtree: true });
})();
</script>`
    
    html = html.replace('</head>', `${injectScript}</head>`)
    
    return new NextResponse(html, {
      status: 200,
      headers: createCleanHeaders('text/html; charset=utf-8'),
    })
  } catch {
    return new NextResponse(html, {
      status: 200,
      headers: createCleanHeaders('text/html'),
    })
  }
}

function createErrorResponse(statusCode: number, targetUrl: string, errorMsg?: string): NextResponse {
  const message = statusCode === 404 ? 'Страница не найдена' : 
                  statusCode === 403 ? 'Доступ запрещён' :
                  statusCode > 0 ? `Ошибка сервера (${statusCode})` :
                  'Таймаут соединения'
  
  const html = `<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body{margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#1a1a2e;color:#fff;display:flex;align-items:center;justify-content:center;min-height:100vh;text-align:center}
.container{padding:20px;max-width:400px}
.icon{font-size:64px;margin-bottom:16px}
h2{margin:0 0 8px;font-size:18px}
p{color:#888;margin:0 0 16px;font-size:14px}
.btn{display:inline-block;background:#e74c3c;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:600;margin:4px}
.btn-primary{background:#2ecc71}
.btn-secondary{background:#9b59b6}
.error{color:#666;font-size:11px;margin-top:16px;background:rgba(255,255,255,0.05);padding:8px 12px;border-radius:6px}
</style>
</head>
<body>
<div class="container">
<div class="icon">📡</div>
<h2>${message}</h2>
<p>Не удалось загрузить плеер через прокси</p>
<div>
<a href="${targetUrl}" target="_blank" class="btn btn-primary">🌐 Открыть на LiveTV</a>
</div>
${errorMsg ? `<div class="error">${errorMsg}</div>` : ''}
</div>
</body></html>`
  
  return new NextResponse(html, {
    status: 200,
    headers: { 'Content-Type': 'text/html; charset=utf-8' },
  })
}

export async function OPTIONS() {
  return new NextResponse(null, {
    status: 204,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, OPTIONS',
      'Access-Control-Allow-Headers': '*',
    },
  })
}
