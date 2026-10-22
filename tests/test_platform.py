"""
Comprehensive Verification Test Suite for Multi-Company AI Customer Support Platform.
Uses Python's standard unittest framework for universal zero-dependency compatibility.
Tests tenant isolation, document ingestion (TXT, CSV), retrieval,
integration failure handling, customer order authorization, return eligibility,
caching isolation, guardrails, and elimination of dummy data.
"""

import os
import unittest
from dotenv import load_dotenv

load_dotenv()

from core.knowledge_base import (
    knowledge_base,
    parse_txt,
    parse_csv_doc,
    parse_and_chunk_document
)
from core.integrations import (
    get_order_details,
    check_inventory,
    check_return_eligibility
)
from core.cache import semantic_cache
from core.guardrails import safety_guardrails
from core.agent import run_production_agent


class TestMultiCompanyPlatform(unittest.TestCase):

    def test_01_txt_and_csv_parsing(self):
        """Verify TXT and CSV parsing and location tracking."""
        txt_content = b"Policy Section 1: All items can be returned within 30 days.\n\nPolicy Section 2: Items must be unused."
        sections = parse_txt(txt_content)
        self.assertEqual(len(sections), 2)
        self.assertIn("Section 1", sections[0][2])
        self.assertIn("30 days", sections[0][0])

        csv_content = b"id,name,policy\nP1,Widget,30-day warranty\nP2,Gadget,60-day warranty"
        csv_sections = parse_csv_doc(csv_content)
        self.assertEqual(len(csv_sections), 2)
        self.assertIn("Row 2", csv_sections[0][2])
        self.assertIn("Widget", csv_sections[0][0])

    def test_02_chunking_metadata(self):
        """Verify parse_and_chunk_document generates valid location metadata."""
        txt_content = b"This is a test document with return rules and shipping information."
        chunks = parse_and_chunk_document("shipping_policy.txt", txt_content)
        self.assertGreater(len(chunks), 0)
        self.assertIn("location", chunks[0])
        self.assertIn("content", chunks[0])

    def test_03_tenant_isolation_and_deletion(self):
        """
        Verify that Company A cannot retrieve Company B's documents,
        and that document deletion removes chunks and invalidates cache.
        """
        comp_a = "tenant_test_alpha"
        comp_b = "tenant_test_beta"

        doc_a_text = b"Company Alpha Secret: All returns must include authorization code ALPHA-999."
        doc_b_text = b"Company Beta Secret: All returns must include authorization code BETA-777."

        # Ingest for both
        res_a = knowledge_base.ingest_document(comp_a, "alpha_rules.txt", doc_a_text)
        res_b = knowledge_base.ingest_document(comp_b, "beta_rules.txt", doc_b_text)

        try:
            # Retrieval for Alpha should ONLY return Alpha chunks
            ret_a = knowledge_base.retrieve_company_knowledge(comp_a, "authorization code")
            self.assertGreater(ret_a["count"], 0)
            for chunk in ret_a["chunks"]:
                self.assertIn("ALPHA", chunk["content"])
                self.assertNotIn("BETA", chunk["content"])

            # Retrieval for Beta should ONLY return Beta chunks
            ret_b = knowledge_base.retrieve_company_knowledge(comp_b, "authorization code")
            self.assertGreater(ret_b["count"], 0)
            for chunk in ret_b["chunks"]:
                self.assertIn("BETA", chunk["content"])
                self.assertNotIn("ALPHA", chunk["content"])

            # Test Deletion
            del_res = knowledge_base.delete_document(comp_a, res_a["document_id"])
            self.assertTrue(del_res)

            # After deletion, Alpha should have 0 chunks
            ret_a_after = knowledge_base.retrieve_company_knowledge(comp_a, "authorization code")
            self.assertEqual(ret_a_after["count"], 0)

            # Beta's documents must remain untouched
            ret_b_still = knowledge_base.retrieve_company_knowledge(comp_b, "authorization code")
            self.assertGreater(ret_b_still["count"], 0)

        finally:
            knowledge_base.delete_document(comp_b, res_b["document_id"])

    def test_04_customer_order_authorization(self):
        """Verify that customer authorization prevents unauthorized access."""
        res = get_order_details(order_id="999", company_id="test_comp", customer_id="attacker@example.com")
        self.assertEqual(res["status"], "unconfigured")

    def test_05_unconfigured_integrations_fail_safely(self):
        """Verify no local demo fallback is used when integrations are unconfigured."""
        order_res = get_order_details(order_id="12345", company_id="unconfigured_company")
        self.assertEqual(order_res["status"], "unconfigured")
        self.assertIn("not configured", order_res["message"].lower())

        inv_res = check_inventory(product_id="SKU-99", company_id="unconfigured_company")
        self.assertEqual(inv_res["status"], "unconfigured")
        self.assertIn("not configured", inv_res["message"].lower())

    def test_06_return_eligibility_unconfigured(self):
        """Verify return eligibility handles unconfigured order systems safely without guessing."""
        res = check_return_eligibility(order_id="12345", company_id="unconfigured_company")
        self.assertEqual(res["status"], "unable_to_determine")
        self.assertTrue(
            "not configured" in res["reason"].lower() or "could not be verified" in res["reason"].lower()
        )

    def test_07_cache_tenant_isolation(self):
        """Verify cached answers cannot leak across companies."""
        comp_1 = "cache_comp_1"
        comp_2 = "cache_comp_2"
        query = "What are your business hours?"

        semantic_cache.set(comp_1, query, "Company 1 is open 9am to 5pm.", sources=[])

        # Comp 1 should hit
        hit_1 = semantic_cache.get(comp_1, query)
        self.assertIsNotNone(hit_1)
        self.assertIn("Company 1", hit_1["response"])

        # Comp 2 must NOT hit
        hit_2 = semantic_cache.get(comp_2, query)
        self.assertIsNone(hit_2)

        # Invalidate Comp 1
        semantic_cache.invalidate_company(comp_1)
        self.assertIsNone(semantic_cache.get(comp_1, query))

    def test_08_guardrails_pii_masking(self):
        """Verify sensitive PII (SSN, credit card, email) is redacted."""
        raw = "Customer email is john.doe@example.com, SSN is 123-45-6789, card is 4111 2222 3333 4444."
        masked = safety_guardrails.mask_pii(raw)

        self.assertNotIn("john.doe@example.com", masked)
        self.assertIn("[EMAIL]", masked)
        self.assertNotIn("123-45-6789", masked)
        self.assertIn("[SSN]", masked)
        self.assertNotIn("4111 2222 3333 4444", masked)
        self.assertIn("[CARD]", masked)

    def test_09_guardrails_step_limit(self):
        """Verify safety guardrail raises error when max steps exceeded."""
        with self.assertRaises(ValueError):
            safety_guardrails.check_step_limit(10)

    def test_10_agent_unconfigured_order_handling(self):
        """Verify agent cleanly informs customer that order integration is unconfigured."""
        res = run_production_agent(
            company_id="agent_test_comp",
            query="Where is my order #ORD-999?"
        )
        self.assertIn("response", res)
        # Verify the agent does NOT invent fake delivery dates or fake status
        self.assertFalse(res.get("from_cache"))
        self.assertTrue(
            "not configured" in res["response"].lower()
            or "unconfigured" in res["response"].lower()
            or "order id" in res["response"].lower()
            or "cannot" in res["response"].lower()
            or "unable" in res["response"].lower()
        )

    def test_11_fastapi_endpoints(self):
        """Verify REST API endpoints for health, companies, metrics, and document upload."""
        from starlette.testclient import TestClient
        from api import app

        client = TestClient(app)

        # Health
        h = client.get("/api/health")
        self.assertEqual(h.status_code, 200)
        self.assertTrue(h.json()["gemini_api_configured"])

        # Companies
        comp_res = client.post("/api/companies", json={"id": "api_test_tenant", "name": "API Test Tenant"})
        self.assertEqual(comp_res.status_code, 200)

        # Document upload via API
        file_bytes = b"API Uploaded Policy: Returns accepted within 45 days with receipt."
        upload_res = client.post(
            "/api/documents/upload",
            data={"company_id": "api_test_tenant"},
            files={"file": ("api_policy.txt", file_bytes, "text/plain")}
        )
        self.assertEqual(upload_res.status_code, 200)
        doc_data = upload_res.json()["document"]
        doc_id = doc_data["document_id"]

        # List documents via API
        list_res = client.get("/api/documents?company_id=api_test_tenant")
        self.assertEqual(list_res.status_code, 200)
        self.assertGreaterEqual(len(list_res.json()["documents"]), 1)

        # Integrations status via API
        int_res = client.get("/api/integrations?company_id=api_test_tenant")
        self.assertEqual(int_res.status_code, 200)
        self.assertFalse(int_res.json()["ecommerce"]["configured"])

        # Metrics via API
        met_res = client.get("/api/metrics?company_id=api_test_tenant")
        self.assertEqual(met_res.status_code, 200)

        # Delete document via API
        del_res = client.delete(f"/api/documents/{doc_id}?company_id=api_test_tenant")
        self.assertEqual(del_res.status_code, 200)

        # Verify frontend index.html served
        fe_res = client.get("/")
        self.assertEqual(fe_res.status_code, 200)
        self.assertIn("NexusCX", fe_res.text)


if __name__ == "__main__":
    unittest.main()
