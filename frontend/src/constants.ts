// Simple constants file - no magic numbers/strings

export const API_BASE = '/api';

export const UPLOAD_CONSTANTS = {
    MAX_SIZE: 10 * 1024 * 1024, // 10MB
    ACCEPTED_TYPES: {
        'application/pdf': ['.pdf'],
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
        'text/plain': ['.txt'],
    },
} as const;

export const UI_CONSTANTS = {
    PREVIEW_LENGTH: 150,
    CHAT_HISTORY_LIMIT: 50,
    DEBOUNCE_MS: 100,
    SCROLL_THRESHOLD: 100,
} as const;

export const RESPONSE_CODES = {
    DUPLICATE_DOCUMENT: '1006',
} as const;
