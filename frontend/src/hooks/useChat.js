import { useState, useCallback, useRef, useEffect } from 'react';

const API_BASE = '/api';

/**
 * Custom hook for managing chat state and API interactions
 */
export function useChat() {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);
  const [error, setError] = useState(null);
  const abortControllerRef = useRef(null);
  const historyLoadedRef = useRef(false);

  /**
   * Load chat history from server
   */
  const loadHistory = useCallback(async () => {
    setIsLoadingHistory(true);
    try {
      const response = await fetch(`${API_BASE}/chat/history?limit=50`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      if (data.messages && data.messages.length > 0) {
        const formattedMessages = data.messages.map((msg, index) => ({
          id: msg.id || Date.now() + index,
          role: msg.role,
          content: msg.content,
          sources: msg.sources || [],
          timestamp: msg.timestamp,
          isStreaming: false,
        }));
        setMessages(formattedMessages);
      } else {
        setMessages([]);
      }
    } catch (err) {
      console.error('Failed to load chat history:', err);
      // Non-critical error, just continue without history
    } finally {
      setIsLoadingHistory(false);
    }
  }, []);

  /**
   * Load chat history from server on mount
   */
  useEffect(() => {
    if (historyLoadedRef.current) return;
    historyLoadedRef.current = true;
    loadHistory();
  }, [loadHistory]);

  /**
   * Reload history (e.g., after switching sessions)
   */
  const reloadHistory = useCallback(async () => {
    await loadHistory();
  }, [loadHistory]);

  /**
   * Send a message and get a streaming response
   */
  const sendMessage = useCallback(async (question, docIds = null) => {
    if (!question.trim()) return;

    // Add user message
    const userMessage = {
      id: Date.now(),
      role: 'user',
      content: question,
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);
    setError(null);

    // Create placeholder for assistant message
    const assistantMessageId = Date.now() + 1;
    const assistantMessage = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      sources: [],
      isStreaming: true,
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, assistantMessage]);

    try {
      // Cancel any existing request
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      abortControllerRef.current = new AbortController();

      const response = await fetch(`${API_BASE}/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question,
          doc_ids: docIds,
        }),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));

              if (data.type === 'content') {
                setMessages(prev =>
                  prev.map(msg =>
                    msg.id === assistantMessageId
                      ? { ...msg, content: msg.content + data.content }
                      : msg
                  )
                );
              } else if (data.type === 'sources') {
                setMessages(prev =>
                  prev.map(msg =>
                    msg.id === assistantMessageId
                      ? { ...msg, sources: data.sources }
                      : msg
                  )
                );
              } else if (data.type === 'done') {
                setMessages(prev =>
                  prev.map(msg =>
                    msg.id === assistantMessageId
                      ? { ...msg, isStreaming: false, cached: data.cached }
                      : msg
                  )
                );
              } else if (data.type === 'error') {
                throw new Error(data.error);
              }
            } catch (e) {
              if (e.message !== 'Unexpected end of JSON input') {
                console.error('Error parsing SSE:', e);
              }
            }
          }
        }
      }
    } catch (err) {
      if (err.name === 'AbortError') {
        return;
      }

      setError(err.message);
      setMessages(prev =>
        prev.map(msg =>
          msg.id === assistantMessageId
            ? {
                ...msg,
                content: 'Sorry, an error occurred. Please try again.',
                isStreaming: false,
                isError: true,
              }
            : msg
        )
      );
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * Send a message without streaming (fallback)
   */
  const sendMessageSync = useCallback(async (question, docIds = null) => {
    if (!question.trim()) return;

    const userMessage = {
      id: Date.now(),
      role: 'user',
      content: question,
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question,
          doc_ids: docIds,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      const assistantMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: data.answer,
        sources: data.sources || [],
        cached: data.cached,
        timestamp: new Date().toISOString(),
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (err) {
      setError(err.message);
      setMessages(prev => [
        ...prev,
        {
          id: Date.now() + 1,
          role: 'assistant',
          content: 'Sorry, an error occurred. Please try again.',
          isError: true,
          timestamp: new Date().toISOString(),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * Clear all messages (local and optionally server)
   * @param {boolean} deleteFromServer - Whether to also delete from server (default: true)
   */
  const clearMessages = useCallback(async (deleteFromServer = true) => {
    setMessages([]);
    setError(null);

    // Also clear on server if requested
    if (deleteFromServer) {
      try {
        await fetch(`${API_BASE}/chat/history`, {
          method: 'DELETE',
        });
      } catch (err) {
        console.error('Failed to clear chat history on server:', err);
      }
    }
  }, []);

  /**
   * Cancel ongoing request
   */
  const cancelRequest = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsLoading(false);
    }
  }, []);

  return {
    messages,
    isLoading,
    isLoadingHistory,
    error,
    sendMessage,
    sendMessageSync,
    clearMessages,
    cancelRequest,
    reloadHistory,
  };
}

export default useChat;

