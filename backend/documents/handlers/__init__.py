"""Document handlers."""

from documents.handlers.upload_document import upload_document
from documents.handlers.list_documents import list_documents
from documents.handlers.delete_document import delete_document

__all__ = [
    "upload_document",
    "list_documents",
    "delete_document",
]

