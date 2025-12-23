// Simple API client - just wraps fetch with error handling
// Backend-friendly, no complex abstractions

import { API_BASE } from './constants';

interface FetchOptions extends RequestInit {
    timeout?: number;
}

class ApiError extends Error {
    constructor(
        message: string,
        public status?: number,
        public code?: string
    ) {
        super(message);
        this.name = 'ApiError';
    }
}

/**
 * Simple fetch wrapper with timeout and error handling
 */
async function apiFetch<T>(
    endpoint: string,
    options: FetchOptions = {}
): Promise<T> {
    const { timeout = 30000, ...fetchOptions } = options;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            ...fetchOptions,
            signal: controller.signal,
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new ApiError(
                errorData.message || `HTTP error! status: ${response.status}`,
                response.status,
                errorData.code
            );
        }

        return await response.json();
    } catch (error) {
        clearTimeout(timeoutId);

        if (error instanceof ApiError) {
            throw error;
        }

        if (error.name === 'AbortError') {
            throw new ApiError('Request timeout');
        }

        throw new ApiError(error.message || 'Network error');
    }
}

// Simple API methods - one per endpoint
export const api = {
    // Chat
    getChatHistory: (limit: number = 50) =>
        apiFetch(`/chat/history?limit=${limit}`),

    clearChatHistory: () =>
        apiFetch('/chat/history', { method: 'DELETE' }),

    // Documents
    getDocuments: () =>
        apiFetch('/documents'),

    uploadDocument: (file: File) => {
        const formData = new FormData();
        formData.append('file', file);
        return apiFetch('/upload', {
            method: 'POST',
            body: formData,
        });
    },

    deleteDocument: (docId: string) =>
        apiFetch(`/documents/${docId}`, { method: 'DELETE' }),

    // Sessions
    getSessions: () =>
        apiFetch('/sessions'),

    createSession: () =>
        apiFetch('/sessions', { method: 'POST' }),

    switchSession: (sessionId: string) =>
        apiFetch(`/sessions/${sessionId}/switch`, { method: 'PUT' }),

    deleteSession: (sessionId: string) =>
        apiFetch(`/sessions/${sessionId}`, { method: 'DELETE' }),
};

export { ApiError };
