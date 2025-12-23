import { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { Source } from '../types';
import { UI_CONSTANTS } from '../constants';

interface SourceCardProps {
    source: Source;
    index: number;
}

export function SourceCard({ source, index }: SourceCardProps) {
    const [isExpanded, setIsExpanded] = useState(false);

    // Truncate text for preview
    const needsTruncation = source.text.length > UI_CONSTANTS.PREVIEW_LENGTH;
    const previewText = needsTruncation
        ? source.text.slice(0, UI_CONSTANTS.PREVIEW_LENGTH) + '...'
        : source.text;

    // Format relevance score as percentage
    const relevancePercent = Math.round(source.relevance_score * 100);

    // Color based on relevance
    const getRelevanceColor = (score: number) => {
        if (score >= 0.8) return 'text-emerald-400 bg-emerald-500/10';
        if (score >= 0.6) return 'text-sky-400 bg-sky-500/10';
        return 'text-gray-400 bg-gray-500/10';
    };

    return (
        <div
            className="source-card"
            onClick={() => needsTruncation && setIsExpanded(!isExpanded)}
        >
            {/* Header */}
            <div className="flex items-start justify-between gap-3 mb-2">
                <div className="flex items-center gap-2 min-w-0">
                    <div className="flex items-center justify-center w-5 h-5 rounded bg-sky-500/10 
                        text-sky-400 text-xs font-medium flex-shrink-0">
                        {index}
                    </div>
                    <span className="text-sm font-medium text-gray-200 truncate" title={source.filename}>
                        {source.filename}
                    </span>
                </div>

                <div className="flex items-center gap-2 flex-shrink-0">
                    {source.page_number && (
                        <span className="text-xs text-gray-500">
                            p. {source.page_number}
                        </span>
                    )}
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${getRelevanceColor(source.relevance_score)}`}>
                        {relevancePercent}%
                    </span>
                </div>
            </div>

            {/* Content */}
            <p className="text-sm text-gray-400 leading-relaxed">
                {isExpanded ? source.text : previewText}
            </p>

            {/* Expand toggle */}
            {needsTruncation && (
                <button
                    className="flex items-center gap-1 mt-2 text-xs text-sky-400 hover:text-sky-300 transition-colors"
                    onClick={(e) => {
                        e.stopPropagation();
                        setIsExpanded(!isExpanded);
                    }}
                >
                    {isExpanded ? (
                        <>
                            <ChevronUp className="w-3 h-3" />
                            Show less
                        </>
                    ) : (
                        <>
                            <ChevronDown className="w-3 h-3" />
                            Show more
                        </>
                    )}
                </button>
            )}
        </div>
    );
}

export default SourceCard;
