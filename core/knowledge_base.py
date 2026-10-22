"""
Multi-Tenant Document Ingestion and Vector Knowledge Base.
Supports PDF, DOCX, TXT, CSV parsing, chunking with metadata,
and strict server-side tenant-isolated retrieval.
"""

import os
import io
import csv
import uuid
import sqlite3
import datetime
import logging
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

import pypdf
import docx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Default database path
DATA_DIR = os.getenv("DATA_DIR", os.path.join(os.path.dirname(os.path.dirname(__file__)), "data"))
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "support_platform.db")


import contextlib

def is_postgres() -> bool:
    """Returns True if DATABASE_URL is configured for PostgreSQL / Supabase."""
    db_url = os.getenv("DATABASE_URL")
    return bool(db_url and (db_url.startswith("postgresql://") or db_url.startswith("postgres://")))


class PostgresCursorWrapper:
    """Wraps a psycopg2 cursor so that standard '?' placeholders are translated to '%s'."""
    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, query, params=None):
        if params is not None:
            query = query.replace('?', '%s')
            return self._cursor.execute(query, params)
        return self._cursor.execute(query)

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    def __getattr__(self, name):
        return getattr(self._cursor, name)


class PostgresConnectionWrapper:
    """Wraps a psycopg2 connection to provide dictionary-like row access."""
    def __init__(self, conn):
        self._conn = conn

    def cursor(self):
        import psycopg2.extras
        cur = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        return PostgresCursorWrapper(cur)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


@contextlib.contextmanager
def get_db_connection():
    """
    Creates a thread-safe connection to either Supabase PostgreSQL (if DATABASE_URL is set)
    or local SQLite (if DATABASE_URL is unset).
    """
    if is_postgres():
        import psycopg2
        db_url = os.getenv("DATABASE_URL")
        conn = psycopg2.connect(db_url)
        wrapped = PostgresConnectionWrapper(conn)
        try:
            yield wrapped
        finally:
            conn.close()
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()


def init_db():
    """Initializes tables for local SQLite development. (Supabase tables are initialized via migration)."""
    if is_postgres():
        logger.info("Connected to Supabase PostgreSQL cloud database.")
        return

    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Companies table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS companies (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        
        # Documents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                company_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                status TEXT NOT NULL,
                chunk_count INTEGER DEFAULT 0,
                error_message TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
            )
        """)
        
        # Chunks table (multi-tenant vector store)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY,
                company_id TEXT NOT NULL,
                document_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                page_number INTEGER,
                location TEXT NOT NULL,
                content TEXT NOT NULL,
                embedding BLOB NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_company ON chunks(company_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(document_id)")

        # Integrations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS integrations (
                company_id TEXT NOT NULL,
                integration_type TEXT NOT NULL,
                provider TEXT NOT NULL,
                config_json TEXT NOT NULL,
                is_active INTEGER DEFAULT 0,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (company_id, integration_type)
            )
        """)

        # Metrics log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                id TEXT PRIMARY KEY,
                company_id TEXT NOT NULL,
                query TEXT NOT NULL,
                from_cache INTEGER DEFAULT 0,
                total_latency REAL NOT NULL,
                steps INTEGER NOT NULL,
                tools_used TEXT NOT NULL,
                error TEXT,
                timestamp TEXT NOT NULL
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_metrics_company ON metrics(company_id)")

        conn.commit()


init_db()


class EmbeddingService:
    """Generates embeddings using Google Generative AI with fallback handling."""

    def __init__(self):
        self._client = None
        self.model_name = os.getenv("GEMINI_EMBEDDING_MODEL", "models/gemini-embedding-001")

    def _get_client(self):
        if self._client is None:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY environment variable is not set.")
            self._client = GoogleGenerativeAIEmbeddings(
                model=self.model_name,
                google_api_key=api_key
            )
        return self._client

    def embed_text(self, text: str) -> np.ndarray:
        """Embeds a single query or chunk."""
        client = self._get_client()
        vec = client.embed_query(text)
        return np.array(vec, dtype=np.float32)

    def embed_documents(self, texts: List[str]) -> List[np.ndarray]:
        """Embeds multiple chunks in batch."""
        if not texts:
            return []
        client = self._get_client()
        vectors = client.embed_documents(texts)
        return [np.array(v, dtype=np.float32) for v in vectors]


# Shared embedding service singleton
embedding_service = EmbeddingService()


# -------------------------------------------------------------
# Document Parsers
# -------------------------------------------------------------

def parse_txt(file_bytes: bytes) -> List[Tuple[str, Optional[int], str]]:
    """Parses plain text document. Returns [(text, page_number, location)]."""
    text = file_bytes.decode("utf-8", errors="replace")
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [text.strip()]
    
    sections = []
    for i, p in enumerate(paragraphs, 1):
        sections.append((p, None, f"Section {i}"))
    return sections


def parse_csv_doc(file_bytes: bytes) -> List[Tuple[str, Optional[int], str]]:
    """Parses CSV document. Returns [(text, page_number, location)]."""
    text = file_bytes.decode("utf-8", errors="replace")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return []

    header = rows[0]
    sections = []
    for row_idx, row in enumerate(rows[1:], start=2):
        row_dict = {header[i]: row[i] for i in range(min(len(header), len(row)))}
        row_str = ", ".join(f"{k}: {v}" for k, v in row_dict.items() if v)
        if row_str.strip():
            sections.append((row_str, None, f"Row {row_idx}"))
    return sections


def parse_pdf(file_bytes: bytes) -> List[Tuple[str, Optional[int], str]]:
    """Parses PDF document page-by-page. Returns [(text, page_number, location)]."""
    pdf_reader = pypdf.PdfReader(io.BytesIO(file_bytes))
    sections = []
    for page_num, page in enumerate(pdf_reader.pages, start=1):
        text = page.extract_text() or ""
        text = text.strip()
        if text:
            sections.append((text, page_num, f"Page {page_num}"))
    return sections


def parse_docx(file_bytes: bytes) -> List[Tuple[str, Optional[int], str]]:
    """Parses DOCX document paragraphs and tables. Returns [(text, page_number, location)]."""
    doc = docx.Document(io.BytesIO(file_bytes))
    sections = []
    
    # Paragraphs
    p_num = 1
    for p in doc.paragraphs:
        txt = p.text.strip()
        if txt:
            sections.append((txt, None, f"Paragraph {p_num}"))
            p_num += 1
            
    # Tables
    for t_idx, table in enumerate(doc.tables, start=1):
        table_rows = []
        for row in table.rows:
            row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if row_cells:
                table_rows.append(" | ".join(row_cells))
        if table_rows:
            table_text = "\n".join(table_rows)
            sections.append((table_text, None, f"Table {t_idx}"))
            
    return sections


def split_text_into_chunks(text: str, chunk_size: int = 700, chunk_overlap: int = 100) -> List[str]:
    """Splits a single block of text into overlapping character chunks."""
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - chunk_overlap
    return chunks


def parse_and_chunk_document(filename: str, file_bytes: bytes) -> List[Dict[str, Any]]:
    """
    Parses document based on extension and returns structured chunks with location metadata.
    Supported extensions: .pdf, .docx, .txt, .csv
    """
    ext = os.path.splitext(filename)[1].lower()
    
    if ext == ".pdf":
        sections = parse_pdf(file_bytes)
    elif ext == ".docx":
        sections = parse_docx(file_bytes)
    elif ext == ".csv":
        sections = parse_csv_doc(file_bytes)
    elif ext in [".txt", ".md"]:
        sections = parse_txt(file_bytes)
    else:
        raise ValueError(f"Unsupported file format '{ext}'. Supported formats: .pdf, .docx, .txt, .csv")

    if not sections:
        raise ValueError(f"Document '{filename}' appears empty or no readable text could be extracted.")

    structured_chunks = []
    for text, page_num, location in sections:
        sub_chunks = split_text_into_chunks(text)
        for i, chunk_text in enumerate(sub_chunks):
            chunk_loc = f"{location} (part {i+1})" if len(sub_chunks) > 1 else location
            structured_chunks.append({
                "content": chunk_text,
                "page_number": page_num,
                "location": chunk_loc
            })

    return structured_chunks


# -------------------------------------------------------------
# Multi-Tenant Knowledge Base Service
# -------------------------------------------------------------

class MultiTenantKnowledgeBase:
    """Manages document storage, chunk vectorization, and tenant-isolated retrieval."""

    def __init__(self):
        self.embedding_service = embedding_service

    # --- Company Management ---
    def get_or_create_company(self, company_id: str, name: Optional[str] = None) -> Dict[str, Any]:
        """Fetches existing company or creates a new one."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, created_at FROM companies WHERE id = ?", (company_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            
            comp_name = name or f"Company {company_id}"
            now = datetime.datetime.now().isoformat()
            cursor.execute(
                "INSERT INTO companies (id, name, created_at) VALUES (?, ?, ?)",
                (company_id, comp_name, now)
            )
            conn.commit()
            return {"id": company_id, "name": comp_name, "created_at": now}

    def list_companies(self) -> List[Dict[str, Any]]:
        """Lists all registered companies."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, created_at FROM companies ORDER BY name ASC")
            return [dict(r) for r in cursor.fetchall()]

    def delete_company(self, company_id: str) -> bool:
        """Deletes a company and all its associated documents, chunks, integrations, and metrics."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM chunks WHERE company_id = ?", (company_id,))
            cursor.execute("DELETE FROM documents WHERE company_id = ?", (company_id,))
            cursor.execute("DELETE FROM integrations WHERE company_id = ?", (company_id,))
            cursor.execute("DELETE FROM metrics WHERE company_id = ?", (company_id,))
            cursor.execute("DELETE FROM companies WHERE id = ?", (company_id,))
            conn.commit()
            return True

    # --- Document Management ---
    def ingest_document(self, company_id: str, filename: str, file_bytes: bytes) -> Dict[str, Any]:
        """
        Parses document, generates embeddings, and saves chunks into SQLite.
        Enforces tenant isolation by associating every chunk with company_id.
        """
        # Ensure company exists
        self.get_or_create_company(company_id)

        document_id = str(uuid.uuid4())
        file_size = len(file_bytes)
        ext = os.path.splitext(filename)[1].lower()
        now = datetime.datetime.now().isoformat()

        # Parse & Chunk
        try:
            chunks = parse_and_chunk_document(filename, file_bytes)
        except Exception as e:
            with get_db_connection() as conn:
                conn.cursor().execute(
                    """INSERT INTO documents (id, company_id, filename, file_type, file_size, status, chunk_count, error_message, created_at)
                       VALUES (?, ?, ?, ?, ?, 'failed', 0, ?, ?)""",
                    (document_id, company_id, filename, ext, file_size, str(e), now)
                )
                conn.commit()
            raise ValueError(f"Failed to process document {filename}: {str(e)}")

        # Generate embeddings
        texts = [c["content"] for c in chunks]
        try:
            embeddings = self.embedding_service.embed_documents(texts)
        except Exception as e:
            with get_db_connection() as conn:
                conn.cursor().execute(
                    """INSERT INTO documents (id, company_id, filename, file_type, file_size, status, chunk_count, error_message, created_at)
                       VALUES (?, ?, ?, ?, ?, 'failed', 0, ?, ?)""",
                    (document_id, company_id, filename, ext, file_size, f"Embedding generation failed: {str(e)}", now)
                )
                conn.commit()
            raise RuntimeError(f"Embedding service error for {filename}: {str(e)}")

        # Store document & chunks atomically
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO documents (id, company_id, filename, file_type, file_size, status, chunk_count, error_message, created_at)
                   VALUES (?, ?, ?, ?, ?, 'indexed', ?, NULL, ?)""",
                (document_id, company_id, filename, ext, file_size, len(chunks), now)
            )

            for chunk_data, emb in zip(chunks, embeddings):
                chunk_id = str(uuid.uuid4())
                if is_postgres():
                    emb_str = f"[{','.join(map(str, emb.tolist()))}]"
                    cursor.execute(
                        """INSERT INTO chunks (id, company_id, document_id, filename, page_number, location, content, embedding, created_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?::vector, ?)""",
                        (chunk_id, company_id, document_id, filename, chunk_data["page_number"],
                         chunk_data["location"], chunk_data["content"], emb_str, now)
                    )
                else:
                    emb_blob = emb.astype(np.float32).tobytes()
                    cursor.execute(
                        """INSERT INTO chunks (id, company_id, document_id, filename, page_number, location, content, embedding, created_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (chunk_id, company_id, document_id, filename, chunk_data["page_number"],
                         chunk_data["location"], chunk_data["content"], emb_blob, now)
                    )
            conn.commit()

        # Upload raw document to Supabase Storage if configured
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if supabase_url and supabase_key:
            try:
                from supabase import create_client
                client = create_client(supabase_url, supabase_key)
                storage_path = f"{company_id}/{document_id}/{filename}"
                client.storage.from_("documents").upload(
                    path=storage_path,
                    file=file_bytes,
                    file_options={"content-type": "application/octet-stream", "upsert": "true"}
                )
                logger.info(f"Stored original document in Supabase Storage: {storage_path}")
            except Exception as se:
                logger.warning(f"Could not upload to Supabase storage (proceeding with vector DB): {se}")

        logger.info(f"Successfully indexed document {filename} ({len(chunks)} chunks) for company {company_id}")
        return {
            "document_id": document_id,
            "company_id": company_id,
            "filename": filename,
            "file_type": ext,
            "file_size": file_size,
            "chunk_count": len(chunks),
            "status": "indexed",
            "created_at": now
        }

    def list_documents(self, company_id: str) -> List[Dict[str, Any]]:
        """Lists all uploaded documents for a given company."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT id, company_id, filename, file_type, file_size, status, chunk_count, error_message, created_at
                   FROM documents WHERE company_id = ? ORDER BY created_at DESC""",
                (company_id,)
            )
            return [dict(r) for r in cursor.fetchall()]

    def delete_document(self, company_id: str, document_id: str) -> bool:
        """
        Deletes a document and all its indexed chunks.
        Strictly verifies company ownership before deleting.
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM documents WHERE id = ? AND company_id = ?", (document_id, company_id))
            if not cursor.fetchone():
                return False

            cursor.execute("DELETE FROM chunks WHERE document_id = ? AND company_id = ?", (document_id, company_id))
            cursor.execute("DELETE FROM documents WHERE id = ? AND company_id = ?", (document_id, company_id))
            conn.commit()
            return True

    # --- Retrieval ---
    def retrieve_company_knowledge(
        self,
        company_id: str,
        query: str,
        top_k: int = 4,
        similarity_threshold: float = 0.35
    ) -> Dict[str, Any]:
        """
        Retrieves relevant chunks strictly from the specified company's indexed documents.
        Uses native pgvector cosine search in Supabase or in-memory NumPy fallback.
        """
        if not company_id:
            return {
                "source": "knowledge_base",
                "company_id": company_id,
                "query": query,
                "chunks": [],
                "count": 0,
                "error": "company_id is required for retrieval."
            }

        # Native Supabase pgvector execution
        if is_postgres():
            try:
                q_vec = self.embedding_service.embed_text(query)
            except Exception as e:
                return {
                    "source": "knowledge_base",
                    "company_id": company_id,
                    "query": query,
                    "chunks": [],
                    "count": 0,
                    "error": f"Failed to generate query embedding: {str(e)}"
                }

            q_vec_str = f"[{','.join(map(str, q_vec.tolist()))}]"
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """SELECT id, document_id, filename, page_number, location, content,
                              1 - (embedding <=> ?::vector) AS score
                       FROM chunks
                       WHERE company_id = ?
                       ORDER BY embedding <=> ?::vector ASC
                       LIMIT ?""",
                    (q_vec_str, company_id, q_vec_str, top_k)
                )
                rows = cursor.fetchall()

            chunks = []
            for r in rows:
                score = float(r["score"]) if r["score"] is not None else 0.0
                if score >= similarity_threshold:
                    chunks.append({
                        "chunk_id": r["id"],
                        "document_id": r["document_id"],
                        "filename": r["filename"],
                        "page_number": r["page_number"],
                        "location": r["location"],
                        "content": r["content"],
                        "score": round(score, 4)
                    })

            return {
                "source": "knowledge_base",
                "company_id": company_id,
                "query": query,
                "chunks": chunks,
                "count": len(chunks)
            }

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT id, document_id, filename, page_number, location, content, embedding
                   FROM chunks WHERE company_id = ?""",
                (company_id,)
            )
            rows = cursor.fetchall()

        if not rows:
            return {
                "source": "knowledge_base",
                "company_id": company_id,
                "query": query,
                "chunks": [],
                "count": 0,
                "message": f"No documents have been indexed for company '{company_id}'. Please upload company policies or documentation."
            }

        # Embed query
        try:
            q_vec = self.embedding_service.embed_text(query)
        except Exception as e:
            return {
                "source": "knowledge_base",
                "company_id": company_id,
                "query": query,
                "chunks": [],
                "count": 0,
                "error": f"Failed to generate query embedding: {str(e)}"
            }

        q_norm = np.linalg.norm(q_vec)
        if q_norm == 0:
            q_norm = 1e-8

        # Score chunks
        scored_chunks = []
        for r in rows:
            chunk_vec = np.frombuffer(r["embedding"], dtype=np.float32)
            c_norm = np.linalg.norm(chunk_vec)
            if c_norm == 0:
                continue
            sim = float(np.dot(q_vec, chunk_vec) / (q_norm * c_norm))
            if sim >= similarity_threshold:
                scored_chunks.append({
                    "chunk_id": r["id"],
                    "document_id": r["document_id"],
                    "filename": r["filename"],
                    "page_number": r["page_number"],
                    "location": r["location"],
                    "content": r["content"],
                    "score": round(sim, 4)
                })

        # Sort by similarity descending and take top_k
        scored_chunks.sort(key=lambda x: x["score"], reverse=True)
        top_chunks = scored_chunks[:top_k]

        return {
            "source": "knowledge_base",
            "company_id": company_id,
            "query": query,
            "chunks": top_chunks,
            "count": len(top_chunks),
            "total_company_chunks": len(rows),
            "message": f"Retrieved {len(top_chunks)} relevant chunk(s)." if top_chunks else "No chunks matched the query with sufficient relevance."
        }


# Global knowledge base singleton
knowledge_base = MultiTenantKnowledgeBase()
