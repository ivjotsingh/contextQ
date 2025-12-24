import { useState, useCallback, useRef, useEffect } from 'react';
import { throttle } from '../utils';
import { UI_CONSTANTS, API_BASE } from '../constants';
import { Message } from '../types';
import { api } from '../api';

/**
 * Custom hook for managing chat state and API interactions
 * 
 * @param chatId - The current chat ID for history
 */
export function useChat(chatId: string | null) {
    const [messages, setMessages] = useState<Message[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [isLoadingHistory, setIsLoadingHistory] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const abortControllerRef = useRef<AbortController | null>(null);
    const lastChatIdRef = useRef<string | null>(null);

    /**
     * Load chat history from server
     */
    const loadHistory = useCallback(async (targetChatId: string) => {
        setIsLoadingHistory(true);
        setMessages([]);

        try {
            const data: any = await api.getChatHistory(targetChatId, UI_CONSTANTS.CHAT_HISTORY_LIMIT);

            if (data.messages && data.messages.length > 0) {
                const formattedMessages: Message[] = data.messages.map((msg: any, index: number) => ({
                    id: msg.id || Date.now() + index,
                    role: msg.role,
                    content: msg.content,
                    sources: msg.sources || [],
                    timestamp: msg.timestamp,
                    isStreaming: false,
                }));
                setMessages(formattedMessages);
            }
        } catch (err: any) {
            // Non-critical error, just continue without history
        } finally {
            setIsLoadingHistory(false);
        }
    }, []);

    /**
     * Load history when chat changes
     */
    useEffect(() => {
        if (!chatId) {
            setMessages([]);
            setIsLoadingHistory(false);
            return;
        }

        if (chatId !== lastChatIdRef.current) {
            lastChatIdRef.current = chatId;
            loadHistory(chatId);
        }
    }, [chatId, loadHistory]);

    /**
     * Send a message and get a streaming response
     */
    const sendMessage = useCallback(async (question: string, docIds: string[] | null = null) => {
        if (!question.trim() || !chatId) return;

        // Add user message
        const userMessage: Message = {
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
        const assistantMessage: Message = {
            id: assistantMessageId,
            role: 'assistant',
            content: '',
            sources: [],
            isStreaming: true,
            timestamp: new Date().toISOString(),
        };

        setMessages(prev => [...prev, assistantMessage]);

        // Use ref to accumulate content, throttle state updates
        const contentRef = { current: '' };
        const sourcesRef = { current: [] as any[] };

        const throttledUpdate = throttle(() => {
            setMessages(prev =>
                prev.map(msg =>
                    msg.id === assistantMessageId
                        ? { ...msg, content: contentRef.current, sources: sourcesRef.current }
                        : msg
                )
            );
        }, UI_CONSTANTS.DEBOUNCE_MS);

        try {
            if (abortControllerRef.current) {
                abortControllerRef.current.abort();
            }
            abortControllerRef.current = new AbortController();

            const response = await fetch(`${API_BASE}/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    question,
                    chat_id: chatId,
                    doc_ids: docIds,
                }),
                signal: abortControllerRef.current.signal,
                credentials: 'include', // Required to send session cookies for document access
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const reader = response.body!.getReader();
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
                                contentRef.current += data.content;
                                throttledUpdate();
                            } else if (data.type === 'sources') {
                                sourcesRef.current = data.sources;
                                throttledUpdate();
                            } else if (data.type === 'done') {
                                setMessages(prev =>
                                    prev.map(msg =>
                                        msg.id === assistantMessageId
                                            ? { ...msg, content: contentRef.current, sources: sourcesRef.current, isStreaming: false }
                                            : msg
                                    )
                                );
                            } else if (data.type === 'error') {
                                throw new Error(data.error);
                            }
                        } catch (e: any) {
                            if (e.message !== 'Unexpected end of JSON input') {
                                throw e;
                            }
                        }
                    }
                }
            }
        } catch (err: any) {
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
    }, [chatId]);

    /**
     * Clear messages for current chat
     */
    const clearMessages = useCallback(async (deleteFromServer: boolean = true) => {
        setMessages([]);
        setError(null);

        if (deleteFromServer && chatId) {
            try {
                await api.clearChatHistory(chatId);
            } catch (err) {
                // Non-critical
            }
        }
    }, [chatId]);

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
        clearMessages,
        cancelRequest,
    };
}

export default useChat;
