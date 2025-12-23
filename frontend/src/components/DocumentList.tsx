import { FileText, Trash2, Clock, Layers } from 'lucide-react';
import { Document } from '../types';

const FILE_ICONS: Record<string, string> = {
    pdf: '📄',
    docx: '📝',
    txt: '📃',
};

const FILE_COLORS: Record<string, string> = {
    pdf: 'text-red-400 bg-red-500/10',
    docx: 'text-blue-400 bg-blue-500/10',
    txt: 'text-gray-400 bg-gray-500/10',
};

function formatDate(dateString: string): string {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now.getTime() - date.getTime();

    // Less than 1 minute
    if (diff < 60000) return 'Just now';

    // Less than 1 hour
    if (diff < 3600000) {
        const mins = Math.floor(diff / 60000);
        return `${mins}m ago`;
    }

    // Less than 24 hours
    if (diff < 86400000) {
        const hours = Math.floor(diff / 3600000);
        return `${hours}h ago`;
    }

    // Format as date
    return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
    });
}

interface DocumentListProps {
    documents: Document[];
    onDelete: (docId: string) => void;
    isLoading: boolean;
}

export function DocumentList({ documents, onDelete, isLoading }: DocumentListProps) {
    if (isLoading) {
        return (
            <div className="space-y-3">
                {[1, 2, 3].map(i => (
                    <div key={i} className="file-card shimmer h-20" />
                ))}
            </div>
        );
    }

    if (documents.length === 0) {
        return (
            <div className="text-center py-12">
                <div className="w-16 h-16 rounded-2xl bg-white/[0.03] flex items-center justify-center mx-auto mb-4">
                    <FileText className="w-8 h-8 text-gray-600" />
                </div>
                <p className="text-gray-500 mb-1">No documents yet</p>
                <p className="text-sm text-gray-600">Upload documents to start chatting</p>
            </div>
        );
    }

    return (
        <div className="space-y-2">
            {documents.map((doc, index) => (
                <div
                    key={doc.doc_id}
                    className="file-card group animate-in"
                    style={{ animationDelay: `${index * 50}ms` }}
                >
                    {/* File icon */}
                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-lg ${FILE_COLORS[doc.document_type] || FILE_COLORS.txt
                        }`}>
                        {FILE_ICONS[doc.document_type] || FILE_ICONS.txt}
                    </div>

                    {/* File info */}
                    <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-200 truncate" title={doc.filename}>
                            {doc.filename}
                        </p>
                        <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                            <span className="flex items-center gap-1">
                                <Layers className="w-3 h-3" />
                                {doc.total_chunks} chunks
                            </span>
                            <span className="flex items-center gap-1">
                                <Clock className="w-3 h-3" />
                                {formatDate(doc.upload_timestamp)}
                            </span>
                        </div>
                    </div>

                    {/* Delete button */}
                    <button
                        onClick={() => onDelete(doc.doc_id)}
                        className="btn-icon opacity-0 group-hover:opacity-100 text-gray-500 hover:text-red-400 
                       hover:bg-red-500/10 transition-all duration-200"
                        title="Delete document"
                    >
                        <Trash2 className="w-4 h-4" />
                    </button>
                </div>
            ))}
        </div>
    );
}

export default DocumentList;
