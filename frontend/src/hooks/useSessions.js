import { useState, useCallback, useEffect, useRef } from 'react';

const API_BASE = '/api';

/**
 * Custom hook for managing chat sessions
 */
export function useSessions() {
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const loadedRef = useRef(false);

  /**
   * Load sessions from server
   */
  const loadSessions = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/sessions`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setSessions(data.sessions || []);
      setCurrentSessionId(data.current_session_id);
    } catch (err) {
      console.error('Failed to load sessions:', err);
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
      const response = await fetch(`${API_BASE}/sessions`, {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      const newSession = data.data;

      setSessions(prev => [newSession, ...prev]);
      setCurrentSessionId(newSession.id);

      return newSession;
    } catch (err) {
      console.error('Failed to create session:', err);
      throw err;
    }
  }, []);

  /**
   * Switch to a different session
   */
  const switchSession = useCallback(async (sessionId) => {
    if (sessionId === currentSessionId) return;

    try {
      const response = await fetch(`${API_BASE}/sessions/${sessionId}/switch`, {
        method: 'PUT',
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      setCurrentSessionId(sessionId);
      return true;
    } catch (err) {
      console.error('Failed to switch session:', err);
      return false;
    }
  }, [currentSessionId]);

  /**
   * Delete a session
   */
  const deleteSession = useCallback(async (sessionId) => {
    try {
      const response = await fetch(`${API_BASE}/sessions/${sessionId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // Remove from local state
      setSessions(prev => prev.filter(s => s.id !== sessionId));

      // If we deleted the current session, reload to get new session
      if (sessionId === currentSessionId) {
        await loadSessions();
      }

      return true;
    } catch (err) {
      console.error('Failed to delete session:', err);
      return false;
    }
  }, [currentSessionId, loadSessions]);

  /**
   * Refresh sessions (e.g., after sending a message)
   */
  const refreshSessions = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/sessions`);
      if (response.ok) {
        const data = await response.json();
        setSessions(data.sessions || []);
      }
    } catch (err) {
      console.error('Failed to refresh sessions:', err);
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

