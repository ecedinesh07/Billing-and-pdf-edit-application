import { environment } from '../../../environments/environment';

/**
 * FastAPI error bodies seen from this API:
 * - 400/404: `{ "detail": "Document not found" }`
 * - 422: `{ "detail": [{ "loc": ["body", "type"], "msg": "Field required" }] }`
 * - network: status 0, no JSON body
 */
export function apiErrorMessage(err: unknown, fallback: string): string {
  const httpErr = err as {
    status?: number;
    error?: { detail?: unknown } | string;
  };

  if (httpErr?.status === 0 || httpErr?.status === undefined) {
    const origin = environment.apiBaseUrl.replace(/\/api\/v1\/?$/, '');
    return `Cannot reach the API at ${origin}. Start the server, then try again.`;
  }

  const body = httpErr.error;
  if (typeof body === 'string' && body.trim()) {
    return body.trim();
  }

  if (body && typeof body === 'object' && 'detail' in body) {
    const formatted = formatDetail(body.detail);
    if (formatted) {
      return formatted;
    }
  }

  return fallback;
}

function formatDetail(detail: unknown): string | null {
  if (typeof detail === 'string' && detail.trim()) {
    return detail.trim();
  }

  if (!Array.isArray(detail)) {
    return null;
  }

  const parts = detail
    .map((item) => {
      if (!item || typeof item !== 'object') {
        return '';
      }
      const record = item as { msg?: unknown; loc?: unknown };
      const msg = typeof record.msg === 'string' ? record.msg.trim() : '';
      if (!msg) {
        return '';
      }
      const loc = Array.isArray(record.loc) ? record.loc : [];
      const field = loc.length ? String(loc[loc.length - 1]) : '';
      return field ? `${field}: ${msg}` : msg;
    })
    .filter((part) => part.length > 0);

  return parts.length ? parts.join(' ') : null;
}
