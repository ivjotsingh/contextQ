import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { User, Bot, ChevronDown, ChevronUp, FileText, ExternalLink, Zap } from 'lucide-react';
import SourceCard from './SourceCard';

export function MessageBubble({ message }) {
  const [showSources, setShowSources] = useState(false);
  const isUser = message.role === 'user';
  const hasSources = message.sources && message.sources.length > 0;

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''} animate-message-in`}>
      {/* Avatar */}
      <div className={`flex-shrink-0 w-8 h-8 rounded-xl flex items-center justify-center ${
        isUser 
          ? 'bg-sky-500' 
          : 'bg-gradient-to-br from-violet-500/20 to-sky-500/20 border border-white/10'
      }`}>
        {isUser ? (
          <User className="w-4 h-4 text-white" />
        ) : (
          <Bot className="w-4 h-4 text-sky-400" />
        )}
      </div>

      {/* Content */}
      <div className={`flex flex-col gap-2 ${isUser ? 'items-end' : 'items-start'} max-w-[80%]`}>
        {/* Message bubble */}
        <div className={`message-bubble ${isUser ? 'message-user' : 'message-assistant'}`}>
          {message.isStreaming && !message.content ? (
            <div className="typing-indicator py-0">
              <div className="typing-dot" />
              <div className="typing-dot" />
              <div className="typing-dot" />
            </div>
          ) : (
            <div className={isUser ? '' : 'prose-chat'}>
              {isUser ? (
                message.content
              ) : (
                <ReactMarkdown>{message.content}</ReactMarkdown>
              )}
            </div>
          )}

          {/* Streaming cursor */}
          {message.isStreaming && message.content && (
            <span className="inline-block w-2 h-4 bg-sky-400 ml-1 animate-pulse" />
          )}
        </div>

        {/* Cached badge */}
        {message.cached && (
          <div className="flex items-center gap-1.5 text-xs text-sky-400/70">
            <Zap className="w-3 h-3" />
            <span>Cached response</span>
          </div>
        )}

        {/* Sources toggle */}
        {hasSources && !message.isStreaming && (
          <button
            onClick={() => setShowSources(!showSources)}
            className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-400 
                     hover:text-gray-200 bg-white/[0.02] hover:bg-white/[0.05]
                     border border-white/[0.05] rounded-lg transition-all duration-200"
          >
            <FileText className="w-3.5 h-3.5" />
            <span>{message.sources.length} source{message.sources.length > 1 ? 's' : ''}</span>
            {showSources ? (
              <ChevronUp className="w-3.5 h-3.5" />
            ) : (
              <ChevronDown className="w-3.5 h-3.5" />
            )}
          </button>
        )}

        {/* Sources list */}
        {showSources && hasSources && (
          <div className="w-full space-y-2 animate-in">
            {message.sources.map((source, index) => (
              <SourceCard key={index} source={source} index={index + 1} />
            ))}
          </div>
        )}

        {/* Error state */}
        {message.isError && (
          <p className="text-xs text-red-400">
            Something went wrong. Please try again.
          </p>
        )}
      </div>
    </div>
  );
}

export default MessageBubble;

