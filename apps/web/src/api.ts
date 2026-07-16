export async function api<T>(apiBase: string, path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, {
    headers: {
      "Content-Type": "application/json",
    },
    ...init,
  });

  if (!response.ok) {
    const generic = `Request failed with ${response.status}`;
    if (response.status >= 500) {
      throw new Error(generic);
    }
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? generic);
  }

  return (await response.json()) as T;
}