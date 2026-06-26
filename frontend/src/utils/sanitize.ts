/**
 * Client-side sanitization helpers (defense in depth with React's default escaping).
 */

// Intentional strip of C0 control chars (eslint no-control-regex)
// eslint-disable-next-line no-control-regex
const CONTROL_CHARS = /[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g;
const HTML_TAG = /<[^>]*>/g;

/** Strip control characters and limit length for UI / SEO display. */
export function sanitizeDisplayText(value: string, maxLength = 120): string {
  if (!value) return '';
  const cleaned = value.replace(CONTROL_CHARS, '').replace(HTML_TAG, '').trim();
  if (cleaned.length <= maxLength) return cleaned;
  return cleaned.slice(0, maxLength);
}

/** Allow only http(s) and mailto schemes for dynamic href values. */
export function isSafeHref(href: string): boolean {
  if (!href || typeof href !== 'string') return false;
  const trimmed = href.trim();
  if (trimmed.startsWith('/') && !trimmed.startsWith('//')) return true;
  try {
    const url = new URL(trimmed);
    return url.protocol === 'http:' || url.protocol === 'https:' || url.protocol === 'mailto:';
  } catch {
    return false;
  }
}

/** Remove HTML tags from AI/user markdown before lightweight custom rendering. */
export function stripHtmlTags(text: string): string {
  return text.replace(HTML_TAG, '');
}
