"""Document handlers."""

from apps.documents.handlers.delete_document import delete_document
from apps.documents.handlers.list_documents import list_documents
from apps.documents.handlers.upload_document import upload_document

__all__ = [
    "upload_document",
    "list_documents",
    "delete_document",
]
