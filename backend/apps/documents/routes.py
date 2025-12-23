"""Document routes - registers all document endpoints."""

from fastapi import APIRouter

from apps.documents.handlers import delete_document, list_documents, upload_document
from apps.documents.handlers.list_documents import DocumentListResponse

router = APIRouter(prefix="/documents", tags=["Documents"])

# POST /documents/upload - Upload document
router.post("/upload")(upload_document)

# GET /documents - List documents
router.get("", response_model=DocumentListResponse)(list_documents)

# DELETE /documents/{doc_id} - Delete document
router.delete("/{doc_id}")(delete_document)
