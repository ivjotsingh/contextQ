// Simple API client - just wraps fetch with error handling

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
            credentials: 'include', // Required to send/receive session cookies
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

        if (error instanceof Error) {
            if (error.name === 'AbortError') {
                throw new ApiError('Request timeout');
            }
            throw new ApiError(error.message || 'Network error');
        }

        throw new ApiError('Unknown error occurred');
    }
}

// API methods
export const api = {
    // Chat history (requires chat_id)
    getChatHistory: (chatId: string, limit: number = 50) =>
        apiFetch(`/chat/history?chat_id=${chatId}&limit=${limit}`),

    clearChatHistory: (chatId: string) =>
        apiFetch(`/chat/history?chat_id=${chatId}`, { method: 'DELETE' }),

    // Documents (uses session_id from cookie)
    getDocuments: () =>
        apiFetch('/documents'),

    uploadDocument: (file: File) => {
        const formData = new FormData();
        formData.append('file', file);
        return apiFetch('/documents/upload', {
            method: 'POST',
            body: formData,
        });
    },

    deleteDocument: (docId: string) =>
        apiFetch(`/documents/${docId}`, { method: 'DELETE' }),

    // Chats (uses session_id from cookie to filter)
    getChats: () =>
        apiFetch('/chats'),

    createChat: () =>
        apiFetch('/chats', { method: 'POST' }),

    deleteChat: (chatId: string) =>
        apiFetch(`/chats/${chatId}`, { method: 'DELETE' }),
};

export { ApiError };
