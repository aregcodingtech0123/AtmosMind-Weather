# AtmosMind Security Notes

## HTTP security headers (Vercel frontend)

Configured in `frontend/vercel.json` and root `vercel.json` for all routes (`/(.*)`):

| Header | Purpose |
|--------|---------|
| `X-Content-Type-Options: nosniff` | Blocks MIME sniffing |
| `X-Frame-Options: DENY` | Clickjacking protection |
| `Content-Security-Policy` | Restricts script/style/connect sources |
| `Strict-Transport-Security` | HTTPS enforcement on Vercel |
| `Referrer-Policy` | Limits referrer leakage |
| `Permissions-Policy` | Disables unused browser APIs |

### CSP customization

If your FastAPI backend uses a host **not** covered by `connect-src`, add its origin to the `Content-Security-Policy` value in `vercel.json`, for example:

```json
"connect-src 'self' https://your-api.example.com ..."
```

`style-src` includes `'unsafe-inline'` because Tailwind/CRA inject inline styles. `script-src` does **not** use `'unsafe-inline'`; Umami is allowlisted and inline handlers were removed from `index.html`.

### Nonce-based CSP (future / Next.js migration)

For Next.js App Router, prefer middleware nonces:

```ts
// middleware.ts (Next.js example)
import { NextResponse } from 'next/server';

export function middleware(request: Request) {
  const nonce = Buffer.from(crypto.randomUUID()).toString('base64');
  const csp = [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}' https://cloud.umami.is`,
    `style-src 'self' 'nonce-${nonce}' https://fonts.googleapis.com`,
    // ...
  ].join('; ');
  const response = NextResponse.next();
  response.headers.set('Content-Security-Policy', csp);
  response.headers.set('x-nonce', nonce);
  return response;
}
```

Pass `nonce` to `<Script nonce={nonce} />` and styled components as needed.

## Backend (FastAPI)

`SecurityHeadersMiddleware` in `backend/api.py` adds baseline headers when the API is served without Vercel.

SQLite access in `backend/database.py` uses **parameterized** queries only (`?` placeholders).
