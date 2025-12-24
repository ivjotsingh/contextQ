import { useState, useCallback, useEffect, useRef } from 'react';
import { api } from '../api';

interface Chat {
    id: string;
    title: string;
    created_at: string;
    last_activity: string;
    message_count: number;
}

/**
 * Custom hook for managing chats within a session
 * 
 * session_id is handled via cookie (browser identity)
 * chat_id is tracked in state (conversation identity)
 */
export function useChats() {
    const [chats, setChats] = useState<Chat[]>([]);
    const [currentChatId, setCurrentChatId] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const loadedRef = useRef(false);

    /**
     * Load chats from server
     */
    const loadChats = useCallback(async () => {
        try {
            const data: any = await api.getChats();
            const loadedChats = data.chats || [];
            setChats(loadedChats);

            // If we have chats, select the first one
            if (loadedChats.length > 0) {
                setCurrentChatId(loadedChats[0].id);
            } else {
                // No chats exist - create one automatically
                const newChatData: any = await api.createChat();
                const newChat = newChatData.data;
                setChats([newChat]);
                setCurrentChatId(newChat.id);
            }
        } catch (err) {
            // Non-critical
        } finally {
            setIsLoading(false);
        }
    }, []);

    /**
     * Load chats on mount
     */
    useEffect(() => {
        if (loadedRef.current) return;
        loadedRef.current = true;
        loadChats();
    }, [loadChats]);

    /**
     * Create a new chat
     */
    const createChat = useCallback(async () => {
        try {
            const data: any = await api.createChat();
            const newChat = data.data;

            setChats(prev => [newChat, ...prev]);
            setCurrentChatId(newChat.id);

            return newChat;
        } catch (err) {
            throw err;
        }
    }, []);

    /**
     * Switch to a different chat (client-side only)
     */
    const switchChat = useCallback((chatId: string) => {
        if (chatId === currentChatId) return;
        setCurrentChatId(chatId);
    }, [currentChatId]);

    /**
     * Delete a chat
     */
    const deleteChat = useCallback(async (chatId: string) => {
        try {
            await api.deleteChat(chatId);

            // Remove from local state
            setChats(prev => prev.filter(c => c.id !== chatId));

            // If we deleted the current chat, select another or create new
            if (chatId === currentChatId) {
                const remaining = chats.filter(c => c.id !== chatId);
                if (remaining.length > 0) {
                    setCurrentChatId(remaining[0].id);
                } else {
                    // Create a new chat
                    await createChat();
                }
            }

            return true;
        } catch (err) {
            return false;
        }
    }, [currentChatId, chats, createChat]);

    /**
     * Refresh chats
     */
    const refreshChats = useCallback(async () => {
        try {
            const data: any = await api.getChats();
            setChats(data.chats || []);
        } catch (err) {
            // Non-critical
        }
    }, []);

    return {
        chats,
        currentChatId,
        isLoading,
        createChat,
        switchChat,
        deleteChat,
        refreshChats,
    };
}

export default useChats;
