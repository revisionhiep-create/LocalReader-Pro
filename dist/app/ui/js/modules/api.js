
export const API_URL = 'http://127.0.0.1:8000';

export async function fetchJSON(endpoint, options = {}) {
    try {
        const res = await fetch(`${API_URL}${endpoint}`, options);
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || err.error || `Request failed: ${res.status}`);
        }
        return await res.json();
    } catch (e) {
        throw e;
    }
}

export async function fetchBlob(endpoint, options = {}) {
    const res = await fetch(`${API_URL}${endpoint}`, options);
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || err.error || `Request failed: ${res.status}`);
    }
    return await res.blob();
}
