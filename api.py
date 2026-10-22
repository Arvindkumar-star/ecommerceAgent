"""
FastAPI Backend for Multi-Company Customer Support and RAG Platform.
Provides REST endpoints for chat, document ingestion, company management,
real metrics, and integration settings.
"""

import os
import logging
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field

from core.knowledge_base import knowledge_base
from core.agent import run_production_agent
from core.cache import semantic_cache
from core.metrics import platform_metrics
from core.integrations import integration_manager, get_order_details, check_inventory

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("api")

app = FastAPI(
    title="Multi-Company AI Customer Support & RAG Platform",
    description="Enterprise multi-tenant customer support platform powered by LangGraph, Google Gemini, and real integrations.",
    version="2.0.0"
)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------------------------------------
# Request & Response Models
# -------------------------------------------------------------

class CompanyCreateRequest(BaseModel):
    id: str = Field(..., description="Unique company identifier (slug or code)")
    name: str = Field(..., description="Human-readable company name")


class ChatRequest(BaseModel):
    company_id: str = Field(..., description="Target company identifier")
    query: str = Field(..., min_length=1, description="Customer question")
    customer_id: Optional[str] = Field(default=None, description="Optional authenticated customer ID for order access")


class IntegrationConfigRequest(BaseModel):
    company_id: str
    integration_type: str = Field(..., description="'ecommerce' or 'inventory'")
    provider: str = Field(..., description="'rest_api' or 'unconfigured'")
    config: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


# -------------------------------------------------------------
# Company Endpoints
# -------------------------------------------------------------

@app.get("/api/companies")
def list_companies():
    """Lists all registered companies."""
    try:
        return {"companies": knowledge_base.list_companies()}
    except Exception as e:
        logger.error(f"Failed to list companies: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch companies.")


@app.post("/api/companies")
def create_company(req: CompanyCreateRequest):
    """Registers or updates a company."""
    clean_id = req.id.strip().lower().replace(" ", "_")
    if not clean_id:
        raise HTTPException(status_code=400, detail="Company ID cannot be empty.")
    try:
        comp = knowledge_base.get_or_create_company(company_id=clean_id, name=req.name.strip())
        return {"company": comp}
    except Exception as e:
        logger.error(f"Failed to create company: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/companies/{company_id}")
def delete_company(company_id: str):
    """Deletes a company and all its associated data."""
    try:
        knowledge_base.delete_company(company_id=company_id)
        return {"status": "deleted", "company_id": company_id}
    except Exception as e:
        logger.error(f"Failed to delete company {company_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------
# Document Management & RAG Endpoints
# -------------------------------------------------------------

@app.get("/api/documents")
def list_documents(company_id: str = Query(..., description="Company ID")):
    """Lists all documents indexed for a specific company."""
    try:
        docs = knowledge_base.list_documents(company_id)
        return {"company_id": company_id, "documents": docs}
    except Exception as e:
        logger.error(f"Failed to list documents for {company_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/documents/upload")
async def upload_document(
    company_id: str = Form(...),
    file: UploadFile = File(...)
):
    """
    Validates, extracts, chunks, and indexes a company document.
    Invalidates company semantic cache upon successful ingestion.
    """
    if not company_id or not company_id.strip():
        raise HTTPException(status_code=400, detail="company_id is required.")

    filename = file.filename or "uploaded_document"
    ext = os.path.splitext(filename)[1].lower()
    allowed_exts = [".pdf", ".docx", ".txt", ".csv", ".md"]

    if ext not in allowed_exts:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{ext}'. Allowed formats: PDF, DOCX, TXT, CSV."
        )

    # Read bytes with 25MB limit
    content_bytes = await file.read()
    if len(content_bytes) > 25 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds the 25MB limit.")
    if len(content_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        doc_record = knowledge_base.ingest_document(
            company_id=company_id.strip(),
            filename=filename,
            file_bytes=content_bytes
        )
        # Invalidate company cache so answers reflect new document
        semantic_cache.invalidate_company(company_id.strip())

        return {
            "message": f"Document '{filename}' successfully indexed with {doc_record['chunk_count']} chunks.",
            "document": doc_record
        }
    except Exception as e:
        logger.error(f"Document ingestion failed for '{filename}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@app.delete("/api/documents/{document_id}")
def delete_document(
    document_id: str,
    company_id: str = Query(..., description="Company ID")
):
    """
    Deletes a document and its chunks from the vector database.
    Invalidates the company semantic cache.
    """
    try:
        deleted = knowledge_base.delete_document(company_id=company_id, document_id=document_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Document not found or does not belong to this company.")

        semantic_cache.invalidate_company(company_id)
        return {"message": "Document and all associated chunks deleted successfully."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------
# AI Support Chat Endpoint
# -------------------------------------------------------------

@app.post("/api/chat")
def chat(req: ChatRequest):
    """
    Executes the multi-tenant customer support agent pipeline.
    Utilizes semantic caching, real vector retrieval, and safety guardrails.
    """
    if not req.company_id:
        raise HTTPException(status_code=400, detail="company_id is required.")
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="query cannot be empty.")

    try:
        result = run_production_agent(
            company_id=req.company_id.strip(),
            query=req.query.strip(),
            customer_id=req.customer_id.strip() if req.customer_id else None
        )
        return result
    except Exception as e:
        logger.error(f"Chat pipeline error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal agent execution error.")


# -------------------------------------------------------------
# Integrations Endpoints
# -------------------------------------------------------------

@app.get("/api/integrations")
def get_integrations(company_id: str = Query(..., description="Company ID")):
    """Returns active integration statuses for the specified company."""
    ecommerce_rec = integration_manager.get_integration_record(company_id, "ecommerce")
    inventory_rec = integration_manager.get_integration_record(company_id, "inventory")

    return {
        "company_id": company_id,
        "ecommerce": {
            "configured": bool(ecommerce_rec and ecommerce_rec.get("is_active")),
            "provider": ecommerce_rec.get("provider") if ecommerce_rec else "unconfigured",
            "updated_at": ecommerce_rec.get("updated_at") if ecommerce_rec else None
        },
        "inventory": {
            "configured": bool(inventory_rec and inventory_rec.get("is_active")),
            "provider": inventory_rec.get("provider") if inventory_rec else "unconfigured",
            "updated_at": inventory_rec.get("updated_at") if inventory_rec else None
        }
    }


@app.post("/api/integrations")
def save_integration(req: IntegrationConfigRequest):
    """Configures or updates an external business integration for a company."""
    try:
        integration_manager.save_integration_config(
            company_id=req.company_id.strip(),
            integration_type=req.integration_type.strip(),
            provider=req.provider.strip(),
            config=req.config,
            is_active=req.is_active
        )
        return {"message": f"Integration '{req.integration_type}' saved successfully."}
    except Exception as e:
        logger.error(f"Failed to save integration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/integrations/test")
def test_integration(req: IntegrationConfigRequest):
    """Tests the external connectivity of an integration configuration."""
    try:
        if req.integration_type == "ecommerce":
            if req.provider == "rest_api":
                from core.integrations import RestApiECommerceAdapter
                adapter = RestApiECommerceAdapter(
                    endpoint_url=req.config.get("endpoint_url", ""),
                    api_key=req.config.get("api_key")
                )
                return adapter.test_connection()
        elif req.integration_type == "inventory":
            if req.provider == "rest_api":
                from core.integrations import RestApiInventoryAdapter
                adapter = RestApiInventoryAdapter(
                    endpoint_url=req.config.get("endpoint_url", ""),
                    api_key=req.config.get("api_key")
                )
                return adapter.test_connection()

        return {"success": False, "message": f"Provider '{req.provider}' does not support live testing."}
    except Exception as e:
        return {"success": False, "message": f"Connection test failed: {str(e)}"}


# -------------------------------------------------------------
# Observability & Metrics Endpoints
# -------------------------------------------------------------

@app.get("/api/metrics")
def get_metrics(company_id: str = Query(..., description="Company ID")):
    """Returns real telemetry and recent execution logs for a company."""
    try:
        summary = platform_metrics.get_summary(company_id)
        recent_logs = platform_metrics.get_recent_logs(company_id, limit=20)
        return {
            "company_id": company_id,
            "summary": summary,
            "recent_logs": recent_logs
        }
    except Exception as e:
        logger.error(f"Failed to fetch metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------
# Health Check Endpoint
# -------------------------------------------------------------

@app.get("/api/health")
def health_check():
    """Health check validating database and Gemini API key status."""
    has_gemini = bool(os.getenv("GEMINI_API_KEY"))
    return {
        "status": "healthy" if has_gemini else "degraded",
        "gemini_api_configured": has_gemini,
        "model": os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
        "embedding_model": os.getenv("GEMINI_EMBEDDING_MODEL", "models/gemini-embedding-001"),
        "version": "2.0.0"
    }


# -------------------------------------------------------------
# Frontend Static Asset Serving (If Built)
# -------------------------------------------------------------
DIST_DIR = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.exists(DIST_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(DIST_DIR, "assets")), name="assets")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        file_path = os.path.join(DIST_DIR, full_path)
        if full_path and os.path.exists(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(DIST_DIR, "index.html"))
