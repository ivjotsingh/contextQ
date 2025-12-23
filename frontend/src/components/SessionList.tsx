import { MessageSquare, Plus, Trash2, Loader2 } from 'lucide-react';
import { Session } from '../types';

/**
 * Format relative time (e.g., "2 hours ago")
 */
function formatRelativeTime(isoString: string): string {
    if (!isoString) return '';

    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString();
}

interface SessionListProps {
    sessions: Session[];
    currentSessionId: string | null;
    isLoading: boolean;
    onCreateSession: () => void;
    onSwitchSession: (sessionId: string) => void;
    onDeleteSession: (sessionId: string) => void;
}

/**
 * Session list sidebar component
 */
export default function SessionList({
    sessions,
    currentSessionId,
    isLoading,
    onCreateSession,
    onSwitchSession,
    onDeleteSession,
}: SessionListProps) {
    if (isLoading) {
        return (
            <div className="flex items-center justify-center py-8">
                <Loader2 className="w-5 h-5 text-gray-400 animate-spin" />
            </div>
        );
    }

    return (
        <div className="space-y-2">
            {/* New Chat Button */}
            <button
                onClick={onCreateSession}
                className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl
                   bg-gradient-to-r from-sky-500/10 to-violet-500/10
                   border border-sky-500/20 hover:border-sky-500/40
                   text-sky-400 hover:text-sky-300
                   transition-all duration-200 group"
            >
                <div className="w-8 h-8 rounded-lg bg-sky-500/20 flex items-center justify-center
                        group-hover:bg-sky-500/30 transition-colors">
                    <Plus className="w-4 h-4" />
                </div>
                <span className="text-sm font-medium">New Chat</span>
            </button>

            {/* Sessions List */}
            <div className="space-y-1 mt-4">
                <p className="text-xs text-gray-500 uppercase tracking-wider px-2 mb-2">
                    Recent Chats
                </p>

                {sessions.length === 0 ? (
                    <p className="text-sm text-gray-500 px-2 py-4 text-center">
                        No previous chats
                    </p>
                ) : (
                    sessions.map((session) => (
                        <div
                            key={session.id}
                            className={`group relative flex items-center gap-3 px-3 py-2.5 rounded-xl
                         cursor-pointer transition-all duration-200
                         ${session.id === currentSessionId
                                    ? 'bg-white/[0.08] border border-white/10'
                                    : 'hover:bg-white/[0.04] border border-transparent'
                                }`}
                            onClick={() => onSwitchSession(session.id)}
                        >
                            <div className={`w-8 h-8 rounded-lg flex items-center justify-center
                              ${session.id === currentSessionId
                                    ? 'bg-sky-500/20'
                                    : 'bg-white/[0.05]'
                                }`}>
                                <MessageSquare className={`w-4 h-4 
                  ${session.id === currentSessionId ? 'text-sky-400' : 'text-gray-500'}`}
                                />
                            </div>

                            <div className="flex-1 min-w-0">
                                <p className={`text-sm truncate
                  ${session.id === currentSessionId ? 'text-white' : 'text-gray-300'}`}>
                                    {session.title || 'New Chat'}
                                </p>
                                <p className="text-xs text-gray-500 truncate">
                                    {formatRelativeTime(session.last_activity)}
                                    {session.message_count > 0 && (
                                        <span className="ml-2">• {session.message_count} messages</span>
                                    )}
                                </p>
                            </div>

                            {/* Delete button */}
                            <button
                                onClick={(e) => {
                                    e.stopPropagation();
                                    onDeleteSession(session.id);
                                }}
                                className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg
                           hover:bg-red-500/20 text-gray-500 hover:text-red-400
                           transition-all duration-200"
                                title="Delete chat"
                            >
                                <Trash2 className="w-3.5 h-3.5" />
                            </button>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
