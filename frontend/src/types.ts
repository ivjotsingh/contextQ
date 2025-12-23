// Type definitions for the application
// Simple, backend-friendly types

export interface Message {
    id: number;
    role: 'user' | 'assistant';
    content: string;
    sources?: Source[];
    timestamp: string;
    isStreaming?: boolean;
    isError?: boolean;
    cached?: boolean;
}

export interface Source {
    text: string;
    filename: string;
    page_number?: number;
    relevance_score: number;
    chunk_index: number;
    doc_id: string;
}

export interface Document {
    doc_id: string;
    filename: string;
    document_type: string;
    total_chunks: number;
    upload_timestamp: string;
    content_hash: string;
    page_count?: number;
}

export interface Session {
    id: string;
    title: string;
    created_at: string;
    last_activity: string;
    message_count: number;
}

export interface UploadResult {
    success: boolean;
    data?: Document;
    error?: string;
    isDuplicate?: boolean;
    file: string;
}

// API Response types
export interface ApiResponse<T> {
    success: boolean;
    data?: T;
    error?: {
        code: string;
        message: string;
    };
    code?: string;
    message?: string;
}
