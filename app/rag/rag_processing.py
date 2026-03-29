import os
import uuid
import base64
import logging
from typing import Optional

logger = logging.getLogger(__name__)

TRUSTGRAPH_URL = os.environ.get("TRUSTGRAPH_API_URL", "http://api-gateway:8088/")
TRUSTGRAPH_TOKEN = os.environ.get("TRUSTGRAPH_API_SECRET", None)

TRUSTGRAPH_FLOW = os.environ.get("TRUSTGRAPH_FLOW", "default")

TRUSTGRAPH_COLLECTION = os.environ.get("TRUSTGRAPH_COLLECTION", "default")

def _get_api():
    """Return a connected TrustGraph Api client."""
    from trustgraph.api import Api
    return Api(url=TRUSTGRAPH_URL, token=TRUSTGRAPH_TOKEN)


def _get_flow():
    """Return the configured TrustGraph flow handle."""
    return _get_api().flow().id(TRUSTGRAPH_FLOW)


class TrustGraphRAGService:
    """
    Thin wrapper around the TrustGraph Python API.
    """

    def __init__(
        self,
        flow_id: str = TRUSTGRAPH_FLOW,
        collection: str = TRUSTGRAPH_COLLECTION,
    ):
        self.flow_id = flow_id
        self.collection = collection

    def _flow(self):
        return _get_api().flow().id(self.flow_id)

    def query(self, question: str) -> str:
        """
        Run a Graph RAG query against TrustGraph.
        """
        try:
            response = self._flow().graph_rag(
                query=question,
                collection=self.collection,
            )
            return response
        except Exception as e:
            logger.error(f"[TrustGraphRAG] graph_rag query failed: {e}")
            raise

    def query_streaming(self, question: str):
        """
        Streaming variant — yields answer chunks as they arrive.
        Useful for SSE / streaming endpoints in your Flask/FastAPI app.
        """
        try:
            flow = _get_api().socket().flow(self.flow_id)
            for chunk in flow.graph_rag(
                query=question,
                collection=self.collection,
                streaming=True,
            ):
                yield chunk
        except Exception as e:
            logger.error(f"[TrustGraphRAG] streaming graph_rag failed: {e}")
            raise

    def insert_text(self, text: str, doc_id: Optional[str] = None) -> str:
        """
        Load plain text into TrustGraph for a given flow + collection.
        """
        if doc_id is None:
            doc_id = f"urn:doc:{uuid.uuid4()}"

        encoded = base64.b64encode(text.encode("utf-8")).decode("utf-8")

        try:
            lib = _get_api().library()
            lib.add_document(
                id=doc_id,
                text=encoded,
                kind="text/plain",
            )
            logger.info(f"[TrustGraphRAG] uploaded doc {doc_id} to library")

            _get_api().library().start_processing(
                flow_id=self.flow_id,
                document_id=doc_id,
                collection=self.collection,
                processing_id=f"urn:proc:{uuid.uuid4()}",
            )
            logger.info(f"[TrustGraphRAG] processing started for {doc_id}")
            return doc_id

        except Exception as e:
            logger.error(f"[TrustGraphRAG] insert_text failed for {doc_id}: {e}")
            raise

def ingest_document(doc_id: str, raw_bytes: bytes, filename: str) -> None:
    """
    Decode raw file bytes to text and ingest into TrustGraph.
    """
    _mark_status(doc_id, "processing")

    try:
        if filename.lower().endswith(".pdf"):
            text = _extract_pdf_text(raw_bytes)
        else:
            text = raw_bytes.decode("utf-8", errors="ignore")
    except Exception as e:
        logger.error(f"[ingest] decode failed for {filename}: {e}")
        _mark_status(doc_id, "failed")
        return

    try:
        svc = TrustGraphRAGService()
        svc.insert_text(text, doc_id=doc_id)
        logger.info(f"[ingest] {filename} ({doc_id}) submitted to TrustGraph")
        _mark_status(doc_id, "done")
    except Exception as e:
        logger.error(f"[ingest] TrustGraph ingest failed for {filename}: {e}")
        _mark_status(doc_id, "failed")


def _extract_pdf_text(raw_bytes: bytes) -> str:
    """Extract plain text from PDF bytes using pypdf."""
    try:
        import io
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(raw_bytes))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except ImportError:
        logger.warning("pypdf not installed — treating PDF as raw bytes")
        return raw_bytes.decode("utf-8", errors="ignore")


def _mark_status(doc_id: str, status: str) -> None:
    """Update document status in the database."""
    try:
        from app.database.connection import get_session
        from app.database.models import Document, StatusEnum

        status_map = {
            "processing": StatusEnum.processing,
            "done":       StatusEnum.done,
            "failed":     StatusEnum.failed,
        }
        status_val = status_map.get(status, StatusEnum.failed)

        with get_session() as session:
            doc = session.query(Document).filter_by(id=doc_id).first()
            if doc:
                doc.status = status_val
                session.commit()
                logger.info(f"[ingest] doc {doc_id} status -> {status}")
            else:
                logger.warning(
                    f"[ingest] doc {doc_id} not found in DB when marking {status}"
                )
    except Exception as e:
        logger.error(f"[ingest] failed to update status for {doc_id}: {e}")