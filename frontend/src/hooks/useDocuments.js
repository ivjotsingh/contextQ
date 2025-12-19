import { useState, useCallback, useEffect } from 'react';

const API_BASE = '/api';

/**
 * Custom hook for managing document state and uploads
 */
export function useDocuments() {
  const [documents, setDocuments] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState(null);

  /**
   * Fetch all documents for the current session
   */
  const fetchDocuments = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/documents`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setDocuments(data.documents || []);
    } catch (err) {
      setError(err.message);
      console.error('Error fetching documents:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * Upload a document
   */
  const uploadDocument = useCallback(async (file) => {
    setIsUploading(true);
    setUploadProgress(0);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      // Simulate progress for better UX
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return prev;
          }
          return prev + Math.random() * 15;
        });
      }, 200);

      const response = await fetch(`${API_BASE}/upload`, {
        method: 'POST',
        body: formData,
      });

      clearInterval(progressInterval);
      setUploadProgress(100);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || `Upload failed: ${response.status}`);
      }

      const data = await response.json();

      // Add to documents list if not duplicate
      if (data.code !== '1006') { // Not duplicate
        const newDoc = data.data;
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

      return { success: true, data: data.data, isDuplicate: data.code === '1006' };
    } catch (err) {
      setError(err.message);
      return { success: false, error: err.message };
    } finally {
      setIsUploading(false);
      setTimeout(() => setUploadProgress(0), 500);
    }
  }, []);

  /**
   * Upload multiple documents
   */
  const uploadDocuments = useCallback(async (files) => {
    const results = [];
    
    for (const file of files) {
      const result = await uploadDocument(file);
      results.push({ file: file.name, ...result });
    }

    return results;
  }, [uploadDocument]);

  /**
   * Delete a document
   */
  const deleteDocument = useCallback(async (docId) => {
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/documents/${docId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error(`Delete failed: ${response.status}`);
      }

      setDocuments(prev => prev.filter(doc => doc.doc_id !== docId));
      return { success: true };
    } catch (err) {
      setError(err.message);
      return { success: false, error: err.message };
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
  };
}

export default useDocuments;

