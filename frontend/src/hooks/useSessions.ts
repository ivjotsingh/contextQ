import { useState, useCallback, useEffect, useRef } from 'react';
import { api } from '../api';
import { Session } from '../types';

/**
 * Custom hook for managing chat sessions
 * 
 * FIX: Using API client
 * FIX: Fixed useEffect dependency issue
 */
export function useSessions() {
    const [sessions, setSessions] = useState<Session[]>([]);
    const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const loadedRef = useRef(false);

    /**
     * Load sessions from server
     */
    const loadSessions = useCallback(async () => {
        try {
            const data: any = await api.getSessions();
            setSessions(data.sessions || []);
            setCurrentSessionId(data.current_session_id);
        } catch (err) {
            // Non-critical
        } finally {
            setIsLoading(false);
        }
    }, []);

    /**
     * Load sessions on mount
     */
    useEffect(() => {
        if (loadedRef.current) return;
        loadedRef.current = true;
        loadSessions();
    }, [loadSessions]);

    /**
     * Create a new session
     */
    const createSession = useCallback(async () => {
        try {
            const data: any = await api.createSession();
            const newSession = data.data;

            setSessions(prev => [newSession, ...prev]);
            setCurrentSessionId(newSession.id);

            return newSession;
        } catch (err) {
            throw err;
        }
    }, []);

    /**
     * Switch to a different session
     */
    const switchSession = useCallback(async (sessionId: string) => {
        if (sessionId === currentSessionId) return true;

        try {
            await api.switchSession(sessionId);
            setCurrentSessionId(sessionId);
            return true;
        } catch (err) {
            return false;
        }
    }, [currentSessionId]);

    /**
     * Delete a session
     */
    const deleteSession = useCallback(async (sessionId: string) => {
        try {
            await api.deleteSession(sessionId);

            // Remove from local state
            setSessions(prev => prev.filter(s => s.id !== sessionId));

            // If we deleted the current session, reload to get new session
            if (sessionId === currentSessionId) {
                await loadSessions();
            }

            return true;
        } catch (err) {
            return false;
        }
    }, [currentSessionId, loadSessions]);

    /**
     * Refresh sessions (e.g., after sending a message)
     */
    const refreshSessions = useCallback(async () => {
        try {
            const data: any = await api.getSessions();
            setSessions(data.sessions || []);
        } catch (err) {
            // Non-critical
        }
    }, []);

    return {
        sessions,
        currentSessionId,
        isLoading,
        createSession,
        switchSession,
        deleteSession,
        refreshSessions,
    };
}

export default useSessions;
