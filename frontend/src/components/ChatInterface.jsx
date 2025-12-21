import { useState, useRef, useEffect } from 'react';
import { Send, Square, Sparkles, Loader2 } from 'lucide-react';
import MessageBubble from './MessageBubble';

export function ChatInterface({ 
  messages, 
  isLoading,
  isLoadingHistory,
  onSendMessage, 
  onCancelRequest,
  hasDocuments 
}) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading || !hasDocuments) return;
    
    onSendMessage(input);
    setInput('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-6 scrollbar-hide">
        {isLoadingHistory ? (
          <div className="flex flex-col items-center justify-center h-full">
            <Loader2 className="w-8 h-8 text-sky-400 animate-spin mb-3" />
            <p className="text-sm text-gray-500">Loading chat history...</p>
          </div>
        ) : messages.length === 0 ? (
          <EmptyState hasDocuments={hasDocuments} />
        ) : (
          messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))
        )}

        {/* Loading indicator */}
        {isLoading && messages[messages.length - 1]?.role !== 'assistant' && (
          <div className="message-bubble message-assistant">
            <div className="typing-indicator">
              <div className="typing-dot" />
              <div className="typing-dot" />
              <div className="typing-dot" />
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="p-4 border-t border-white/[0.05]">
        <form onSubmit={handleSubmit} className="relative">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              hasDocuments 
                ? "Ask anything about your documents..." 
                : "Upload documents to start chatting..."
            }
            disabled={!hasDocuments}
            rows={1}
            className="input-field-chat pr-14 min-h-[56px] max-h-[200px]"
            style={{ resize: 'none' }}
          />
          
          {isLoading ? (
            <button
              type="button"
              onClick={onCancelRequest}
              className="absolute right-3 top-1/2 -translate-y-1/2 p-2 
                       bg-red-500/20 hover:bg-red-500/30 text-red-400 
                       rounded-xl transition-all duration-200"
              title="Stop generating"
            >
              <Square className="w-5 h-5" />
            </button>
          ) : (
            <button
              type="submit"
              disabled={!input.trim() || !hasDocuments}
              className="absolute right-3 top-1/2 -translate-y-1/2 p-2 
                       bg-sky-500 hover:bg-sky-400 text-white 
                       rounded-xl transition-all duration-200
                       disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:bg-sky-500"
              title="Send message"
            >
              <Send className="w-5 h-5" />
            </button>
          )}
        </form>

        <p className="text-xs text-gray-600 text-center mt-3">
          ContextQ uses AI to answer questions based on your documents
        </p>
      </div>
    </div>
  );
}

function EmptyState({ hasDocuments }) {
  const suggestions = [
    "What are the main topics covered?",
    "Summarize the key points",
    "What conclusions are drawn?",
    "Explain the methodology used",
  ];

  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-4">
      <div className="w-20 h-20 rounded-3xl bg-gradient-to-br from-sky-500/20 to-violet-500/20 
                      flex items-center justify-center mb-6 glow-subtle">
        <Sparkles className="w-10 h-10 text-sky-400" />
      </div>
      
      <h2 className="text-2xl font-semibold text-gray-100 mb-2">
        {hasDocuments ? 'Ready to chat' : 'Welcome to ContextQ'}
      </h2>
      
      <p className="text-gray-500 max-w-md mb-8">
        {hasDocuments 
          ? 'Ask questions about your documents and get answers with source citations.'
          : 'Upload your documents to start asking questions. Your data stays private.'}
      </p>

      {hasDocuments && (
        <div className="w-full max-w-md space-y-2">
          <p className="text-xs text-gray-600 uppercase tracking-wider mb-3">
            Try asking
          </p>
          <div className="grid grid-cols-2 gap-2">
            {suggestions.map((suggestion, i) => (
              <button
                key={i}
                className="px-4 py-3 text-sm text-left text-gray-400 
                         bg-white/[0.02] hover:bg-white/[0.05] 
                         border border-white/[0.05] hover:border-white/[0.1]
                         rounded-xl transition-all duration-200"
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default ChatInterface;

