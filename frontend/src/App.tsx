import { useState, useEffect } from 'react';
import {
    FileText,
    MessageSquare,
    Upload,
    Menu,
    X,
    Sparkles,
    Github,
    MessagesSquare
} from 'lucide-react';
import { useChat } from './hooks/useChat';
import { useDocuments } from './hooks/useDocuments';
import { useChats } from './hooks/useSessions';
import ChatInterface from './components/ChatInterface';
import FileUpload from './components/FileUpload';
import DocumentList from './components/DocumentList';
import SessionList from './components/SessionList';
import ErrorBoundary from './components/ErrorBoundary';

type TabType = 'chats' | 'documents' | 'upload';

function App() {
    const [sidebarOpen, setSidebarOpen] = useState(true);
    const [activeTab, setActiveTab] = useState<TabType>('chats');

    // Chats (conversations) - tracked by chat_id
    const {
        chats,
        currentChatId,
        isLoading: isChatsLoading,
        createChat,
        switchChat,
        deleteChat,
        refreshChats,
    } = useChats();

    // Chat messages - depends on currentChatId
    const {
        messages,
        isLoading: isChatLoading,
        isLoadingHistory,
        sendMessage,
        cancelRequest,
        clearMessages,
    } = useChat(currentChatId);

    // Documents - tied to session (browser), not chat
    const {
        documents,
        isLoading: isDocsLoading,
        isUploading,
        uploadProgress,
        uploadDocuments,
        deleteDocument,
    } = useDocuments();

    const hasDocuments = documents.length > 0;

    // Handle chat switch - just update state, useChat will reload
    const handleSwitchChat = (chatId: string) => {
        switchChat(chatId);
    };

    // Handle new chat creation
    const handleCreateChat = async () => {
        await createChat();
    };

    // Refresh chats after sending message
    useEffect(() => {
        if (messages.length > 0 && !isChatLoading) {
            refreshChats();
        }
    }, [messages.length]);

    return (
        <ErrorBoundary>
            <div className="h-screen flex overflow-hidden">
                {/* Sidebar */}
                <aside
                    className={`${sidebarOpen ? 'w-88' : 'w-0'
                        } flex-shrink-0 transition-all duration-300 ease-in-out overflow-hidden`}
                >
                    <div className="h-full w-88 flex flex-col glass-panel m-3 mr-0 rounded-2xl">
                        {/* Sidebar Header */}
                        <div className="p-5 border-b border-white/[0.05]">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-sky-500 to-violet-500 
                                flex items-center justify-center shadow-lg shadow-sky-500/20">
                                        <Sparkles className="w-5 h-5 text-white" />
                                    </div>
                                    <div>
                                        <h1 className="text-lg font-semibold text-white">ContextQ</h1>
                                        <p className="text-xs text-gray-500">Document Chat</p>
                                    </div>
                                </div>
                                <button
                                    onClick={() => setSidebarOpen(false)}
                                    className="btn-icon lg:hidden"
                                >
                                    <X className="w-5 h-5" />
                                </button>
                            </div>
                        </div>

                        {/* Tab Navigation */}
                        <div className="p-3 border-b border-white/[0.05]">
                            <div className="flex gap-1 p-1 bg-white/[0.02] rounded-xl">
                                <button
                                    onClick={() => setActiveTab('chats')}
                                    className={`flex-1 flex items-center justify-center gap-1.5 px-2 py-2.5 rounded-lg 
                            text-sm font-medium transition-all duration-200 ${activeTab === 'chats'
                                            ? 'bg-white/[0.08] text-white'
                                            : 'text-gray-400 hover:text-gray-200'
                                        }`}
                                >
                                    <MessagesSquare className="w-4 h-4" />
                                    Chats
                                    {chats.length > 0 && (
                                        <span className="ml-0.5 px-1.5 py-0.5 text-xs bg-violet-500/20 text-violet-400 rounded-full">
                                            {chats.length}
                                        </span>
                                    )}
                                </button>
                                <button
                                    onClick={() => setActiveTab('documents')}
                                    className={`flex-1 flex items-center justify-center gap-1.5 px-2 py-2.5 rounded-lg 
                            text-sm font-medium transition-all duration-200 ${activeTab === 'documents'
                                            ? 'bg-white/[0.08] text-white'
                                            : 'text-gray-400 hover:text-gray-200'
                                        }`}
                                >
                                    <FileText className="w-4 h-4" />
                                    Docs
                                    {hasDocuments && (
                                        <span className="ml-0.5 px-1.5 py-0.5 text-xs bg-sky-500/20 text-sky-400 rounded-full">
                                            {documents.length}
                                        </span>
                                    )}
                                </button>
                                <button
                                    onClick={() => setActiveTab('upload')}
                                    className={`flex-1 flex items-center justify-center gap-2 px-2 py-2.5 rounded-lg 
                            text-sm font-medium transition-all duration-200 ${activeTab === 'upload'
                                            ? 'bg-white/[0.08] text-white'
                                            : 'text-gray-400 hover:text-gray-200'
                                        }`}
                                >
                                    <Upload className="w-4 h-4" />
                                    Upload
                                </button>
                            </div>
                        </div>

                        {/* Sidebar Content */}
                        <div className="flex-1 overflow-y-auto p-4 scrollbar-hide">
                            {activeTab === 'chats' ? (
                                <SessionList
                                    sessions={chats.map(c => ({
                                        id: c.id,
                                        title: c.title,
                                        created_at: c.created_at,
                                        last_activity: c.last_activity,
                                        message_count: c.message_count,
                                    }))}
                                    currentSessionId={currentChatId}
                                    isLoading={isChatsLoading}
                                    onCreateSession={handleCreateChat}
                                    onSwitchSession={handleSwitchChat}
                                    onDeleteSession={deleteChat}
                                />
                            ) : activeTab === 'documents' ? (
                                <DocumentList
                                    documents={documents}
                                    onDelete={deleteDocument}
                                    isLoading={isDocsLoading}
                                />
                            ) : (
                                <FileUpload
                                    onUpload={uploadDocuments}
                                    isUploading={isUploading}
                                    uploadProgress={uploadProgress}
                                />
                            )}
                        </div>

                        {/* Sidebar Footer */}
                        <div className="p-4 border-t border-white/[0.05]">
                            <div className="flex items-center justify-center">

                                <a
                                    href="https://github.com/ivjotsingh/contextQ/tree/contextQ"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="btn-icon"
                                    title="View on GitHub"
                                >
                                    <Github className="w-4 h-4" />
                                </a>
                            </div>
                        </div>
                    </div>
                </aside>

                {/* Main Content */}
                <main className="flex-1 flex flex-col min-w-0 p-3">
                    <div className="flex-1 flex flex-col glass-panel rounded-2xl overflow-hidden">
                        {/* Header */}
                        <header className="flex items-center justify-between px-5 py-4 border-b border-white/[0.05]">
                            <div className="flex items-center gap-3">
                                {!sidebarOpen && (
                                    <button
                                        onClick={() => setSidebarOpen(true)}
                                        className="btn-icon"
                                    >
                                        <Menu className="w-5 h-5" />
                                    </button>
                                )}
                                <div className="flex items-center gap-3">
                                    <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-sky-500/20 to-violet-500/20 
                                flex items-center justify-center border border-white/10">
                                        <MessageSquare className="w-4 h-4 text-sky-400" />
                                    </div>
                                    <div>
                                        <h2 className="text-sm font-medium text-white">Chat</h2>
                                        <p className="text-xs text-gray-500">
                                            {hasDocuments
                                                ? `${documents.length} document${documents.length > 1 ? 's' : ''} loaded`
                                                : 'No documents'}
                                        </p>
                                    </div>
                                </div>
                            </div>

                            <div className="flex items-center gap-2">
                                {messages.length > 0 && (
                                    <button
                                        onClick={() => clearMessages()}
                                        className="btn-secondary text-sm"
                                    >
                                        Clear chat
                                    </button>
                                )}
                                {!sidebarOpen && (
                                    <button
                                        onClick={() => {
                                            setSidebarOpen(true);
                                            setActiveTab('upload');
                                        }}
                                        className="btn-primary text-sm"
                                    >
                                        <span className="flex items-center gap-2">
                                            <Upload className="w-4 h-4" />
                                            Upload
                                        </span>
                                    </button>
                                )}
                            </div>
                        </header>

                        {/* Chat Area */}
                        <div className="flex-1 overflow-hidden">
                            <ErrorBoundary>
                                <ChatInterface
                                    messages={messages}
                                    isLoading={isChatLoading}
                                    isLoadingHistory={isLoadingHistory}
                                    onSendMessage={sendMessage}
                                    onCancelRequest={cancelRequest}
                                    hasDocuments={hasDocuments}
                                />
                            </ErrorBoundary>
                        </div>
                    </div>
                </main>

                {/* Mobile sidebar overlay */}
                {sidebarOpen && (
                    <div
                        className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40 lg:hidden"
                        onClick={() => setSidebarOpen(false)}
                    />
                )}
            </div>
        </ErrorBoundary>
    );
}

export default App;
