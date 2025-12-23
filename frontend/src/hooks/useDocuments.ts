import { useState, useCallback, useEffect, useRef } from 'react';
import { api } from '../api';
import { Document } from '../types';
import { UPLOAD_CONSTANTS, RESPONSE_CODES } from '../constants';

interface UploadResult {
    success: boolean;
    data?: any;
    error?: string;
    isDuplicate?: boolean;
    file: string;
}

/**
 * Custom hook for managing document state and uploads
 * 
 * FIX: Using API client
 * FIX: Added AbortController for cancellable uploads
 */
export function useDocuments() {
    const [documents, setDocuments] = useState<Document[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [isUploading, setIsUploading] = useState(false);
    const [uploadProgress, setUploadProgress] = useState(0);
    const [error, setError] = useState<string | null>(null);
    const abortControllerRef = useRef<AbortController | null>(null);

    /**
     * Fetch all documents for the current session
     */
    const fetchDocuments = useCallback(async () => {
        setIsLoading(true);
        setError(null);

        try {
            const data: any = await api.getDocuments();
            setDocuments(data.documents || []);
        } catch (err: any) {
            setError(err.message);
        } finally {
            setIsLoading(false);
        }
    }, []);

    /**
     * Upload a document
     * FIX: Added real progress tracking with XMLHttpRequest
     */
    const uploadDocument = useCallback(async (file: File): Promise<UploadResult> => {
        setIsUploading(true);
        setUploadProgress(0);
        setError(null);

        try {
            // Cancel any existing upload
            if (abortControllerRef.current) {
                abortControllerRef.current.abort();
            }
            abortControllerRef.current = new AbortController();

            const formData = new FormData();
            formData.append('file', file);

            // Use XMLHttpRequest for real progress tracking
            const xhr = new XMLHttpRequest();

            // Track upload progress
            xhr.upload.onprogress = (e) => {
                if (e.lengthComputable) {
                    const progress = (e.loaded / e.total) * 100;
                    setUploadProgress(progress);
                }
            };

            // Handle abort
            abortControllerRef.current.signal.addEventListener('abort', () => {
                xhr.abort();
            });

            const response: any = await new Promise((resolve, reject) => {
                xhr.onload = () => {
                    if (xhr.status >= 200 && xhr.status < 300) {
                        resolve(JSON.parse(xhr.responseText));
                    } else {
                        reject(new Error(`Upload failed: ${xhr.status}`));
                    }
                };
                xhr.onerror = () => reject(new Error('Network error'));
                xhr.open('POST', '/api/upload');
                xhr.send(formData);
            });

            // Add to documents list if not duplicate
            if (response.code !== RESPONSE_CODES.DUPLICATE_DOCUMENT) {
                const newDoc = response.data;
                setDocuments(prev => [
                    {
                        doc_id: newDoc.doc_id,
                        filename: newDoc.filename,
                        document_type: newDoc.document_type,
                        total_chunks: newDoc.total_chunks,
                        upload_timestamp: newDoc.upload_timestamp,
                        content_hash: newDoc.content_hash,
                        page_count: newDoc.page_count,
                    },
                    ...prev,
                ]);
            }

            return {
                success: true,
                data: response.data,
                isDuplicate: response.code === RESPONSE_CODES.DUPLICATE_DOCUMENT,
                file: file.name
            };
        } catch (err: any) {
            if (err.name === 'AbortError') {
                return { success: false, error: 'Upload cancelled', file: file.name };
            }
            setError(err.message);
            return { success: false, error: err.message, file: file.name };
        } finally {
            setIsUploading(false);
            setTimeout(() => setUploadProgress(0), 500);
        }
    }, []);

    /**
     * Upload multiple documents
     */
    const uploadDocuments = useCallback(async (files: File[]): Promise<UploadResult[]> => {
        const results: UploadResult[] = [];

        for (const file of files) {
            const result = await uploadDocument(file);
            results.push(result);
        }

        return results;
    }, [uploadDocument]);

    /**
     * Delete a document
     */
    const deleteDocument = useCallback(async (docId: string) => {
        setError(null);

        try {
            await api.deleteDocument(docId);
            setDocuments(prev => prev.filter(doc => doc.doc_id !== docId));
            return { success: true };
        } catch (err: any) {
            setError(err.message);
            return { success: false, error: err.message };
        }
    }, []);

    /**
     * Cancel ongoing upload
     */
    const cancelUpload = useCallback(() => {
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
            setIsUploading(false);
        }
    }, []);

    // Fetch documents on mount
    useEffect(() => {
        fetchDocuments();
    }, [fetchDocuments]);

    return {
        documents,
        isLoading,
        isUploading,
        uploadProgress,
        error,
        fetchDocuments,
        uploadDocument,
        uploadDocuments,
        deleteDocument,
        cancelUpload,
    };
}

export default useDocuments;
