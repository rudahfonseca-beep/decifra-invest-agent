async function readError(r: Response, url: string): Promise<string> {
  try {
    const data = await r.json();
    if (data?.error) return String(data.error);
  } catch {
    /* ignore */
  }
  if (r.status === 502 || r.status === 504) {
    return `${url} -> ${r.status} (is \`decifra schemas serve\` running on :8765?)`;
  }
  return `${url} -> ${r.status}`;
}

export async function fetchJson<T>(urls: string[]): Promise<T> {
  let lastError: unknown;
  for (const url of urls) {
    try {
      const r = await fetch(url);
      if (!r.ok) throw new Error(await readError(r, url));
      return (await r.json()) as T;
    } catch (e) {
      lastError = e;
    }
  }
  throw lastError ?? new Error("fetch failed");
}

export async function postJson<T>(url: string, body: unknown): Promise<T> {
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  let data: { error?: string } & T;
  try {
    data = (await r.json()) as { error?: string } & T;
  } catch {
    throw new Error(await readError(r, url));
  }
  if (!r.ok) {
    throw new Error(data?.error || `${url} -> ${r.status}`);
  }
  return data as T;
}

export function qs(params: Record<string, string | number | boolean | undefined | null>): string {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "") continue;
    sp.set(k, String(v));
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
}
