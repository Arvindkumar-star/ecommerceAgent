"""
Business Integrations Module.
Provides clean adapter interfaces for live E-Commerce and Inventory sources.
Follows strict rule: ZERO local dummy data.
When not configured, reports explicit 'unconfigured' status.
"""

import json
import logging
import datetime
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
import requests

from core.knowledge_base import get_db_connection, knowledge_base

logger = logging.getLogger(__name__)


# -------------------------------------------------------------
# Base Adapter Interfaces
# -------------------------------------------------------------

class BaseECommerceAdapter(ABC):
    """Abstract interface for e-commerce order sources."""

    @abstractmethod
    def is_configured(self) -> bool:
        """Returns True if the integration is configured and active."""
        pass

    @abstractmethod
    def get_order(self, order_id: str) -> Dict[str, Any]:
        """
        Fetches live order information.
        Must return a dict with status: 'success', 'not_found', 'error', or 'unconfigured'.
        """
        pass

    @abstractmethod
    def test_connection(self) -> Dict[str, Any]:
        """Validates connection to the external system."""
        pass


class BaseInventoryAdapter(ABC):
    """Abstract interface for inventory stock sources."""

    @abstractmethod
    def is_configured(self) -> bool:
        """Returns True if the integration is configured and active."""
        pass

    @abstractmethod
    def get_stock(self, product_id: str) -> Dict[str, Any]:
        """
        Fetches live inventory information.
        Must return a dict with status: 'success', 'not_found', 'error', or 'unconfigured'.
        """
        pass

    @abstractmethod
    def test_connection(self) -> Dict[str, Any]:
        """Validates connection to the external system."""
        pass


# -------------------------------------------------------------
# Default Unconfigured Adapters (Zero fake data)
# -------------------------------------------------------------

class UnconfiguredECommerceAdapter(BaseECommerceAdapter):
    """Returned when a company has not configured an e-commerce order source."""

    def is_configured(self) -> bool:
        return False

    def get_order(self, order_id: str) -> Dict[str, Any]:
        return {
            "status": "unconfigured",
            "source": "orders_api",
            "order_id": order_id,
            "message": "Order integration is not configured. Please configure an authorized database or e-commerce API in Settings."
        }

    def test_connection(self) -> Dict[str, Any]:
        return {"success": False, "message": "No e-commerce integration configured."}


class UnconfiguredInventoryAdapter(BaseInventoryAdapter):
    """Returned when a company has not configured an inventory source."""

    def is_configured(self) -> bool:
        return False

    def get_stock(self, product_id: str) -> Dict[str, Any]:
        return {
            "status": "unconfigured",
            "source": "inventory_api",
            "product_id": product_id,
            "message": "Inventory integration is not configured. Please configure an inventory API or database in Settings."
        }

    def test_connection(self) -> Dict[str, Any]:
        return {"success": False, "message": "No inventory integration configured."}


# -------------------------------------------------------------
# Live REST API Adapters
# -------------------------------------------------------------

class RestApiECommerceAdapter(BaseECommerceAdapter):
    """Connects to a live external e-commerce REST API endpoint."""

    def __init__(self, endpoint_url: str, api_key: Optional[str] = None, timeout: int = 5):
        self.endpoint_url = endpoint_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def is_configured(self) -> bool:
        return bool(self.endpoint_url)

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json", "User-Agent": "NexusCX-Support-Agent/1.0"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def get_order(self, order_id: str) -> Dict[str, Any]:
        if not self.endpoint_url:
            return UnconfiguredECommerceAdapter().get_order(order_id)

        url = f"{self.endpoint_url}/orders/{order_id}"
        try:
            resp = requests.get(url, headers=self._headers(), timeout=self.timeout)
            if resp.status_code == 404:
                return {
                    "status": "not_found",
                    "source": "orders_api",
                    "order_id": order_id,
                    "message": f"Order #{order_id} was not found in the live e-commerce system."
                }
            if resp.status_code != 200:
                return {
                    "status": "error",
                    "source": "orders_api",
                    "order_id": order_id,
                    "message": f"External orders API returned HTTP {resp.status_code}."
                }
            data = resp.json()
            return {
                "status": "success",
                "source": "orders_api",
                "order_id": order_id,
                "data": data,
                "retrieved_at": datetime.datetime.now().isoformat()
            }
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "source": "orders_api",
                "order_id": order_id,
                "message": f"Failed to connect to orders API: {str(e)}"
            }

    def test_connection(self) -> Dict[str, Any]:
        try:
            url = f"{self.endpoint_url}/health"
            resp = requests.get(url, headers=self._headers(), timeout=self.timeout)
            return {
                "success": resp.status_code == 200,
                "status_code": resp.status_code,
                "message": "Connection verified successfully." if resp.status_code == 200 else f"Endpoint returned HTTP {resp.status_code}"
            }
        except Exception as e:
            return {"success": False, "message": f"Connection failed: {str(e)}"}


class RestApiInventoryAdapter(BaseInventoryAdapter):
    """Connects to a live external inventory REST API endpoint."""

    def __init__(self, endpoint_url: str, api_key: Optional[str] = None, timeout: int = 5):
        self.endpoint_url = endpoint_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def is_configured(self) -> bool:
        return bool(self.endpoint_url)

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def get_stock(self, product_id: str) -> Dict[str, Any]:
        if not self.endpoint_url:
            return UnconfiguredInventoryAdapter().get_stock(product_id)

        url = f"{self.endpoint_url}/inventory/{product_id}"
        try:
            resp = requests.get(url, headers=self._headers(), timeout=self.timeout)
            if resp.status_code == 404:
                return {
                    "status": "not_found",
                    "source": "inventory_api",
                    "product_id": product_id,
                    "message": f"Product #{product_id} was not found in inventory."
                }
            if resp.status_code != 200:
                return {
                    "status": "error",
                    "source": "inventory_api",
                    "product_id": product_id,
                    "message": f"External inventory API returned HTTP {resp.status_code}."
                }
            data = resp.json()
            return {
                "status": "success",
                "source": "inventory_api",
                "product_id": product_id,
                "data": data,
                "retrieved_at": datetime.datetime.now().isoformat()
            }
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "source": "inventory_api",
                "product_id": product_id,
                "message": f"Failed to connect to inventory API: {str(e)}"
            }

    def test_connection(self) -> Dict[str, Any]:
        try:
            url = f"{self.endpoint_url}/health"
            resp = requests.get(url, headers=self._headers(), timeout=self.timeout)
            return {
                "success": resp.status_code == 200,
                "status_code": resp.status_code,
                "message": "Connection verified successfully." if resp.status_code == 200 else f"Endpoint returned HTTP {resp.status_code}"
            }
        except Exception as e:
            return {"success": False, "message": f"Connection failed: {str(e)}"}


# -------------------------------------------------------------
# Integration Registry & Factory
# -------------------------------------------------------------

class IntegrationManager:
    """Manages company-specific integration configurations stored securely in the database."""

    def get_integration_record(self, company_id: str, integration_type: str) -> Optional[Dict[str, Any]]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT company_id, integration_type, provider, config_json, is_active, updated_at FROM integrations WHERE company_id = ? AND integration_type = ?",
                (company_id, integration_type)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def save_integration_config(
        self,
        company_id: str,
        integration_type: str,
        provider: str,
        config: Dict[str, Any],
        is_active: bool = True
    ):
        now = datetime.datetime.now().isoformat()
        config_json = json.dumps(config)
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO integrations (company_id, integration_type, provider, config_json, is_active, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(company_id, integration_type) DO UPDATE SET
                   provider = excluded.provider,
                   config_json = excluded.config_json,
                   is_active = excluded.is_active,
                   updated_at = excluded.updated_at""",
                (company_id, integration_type, provider, config_json, 1 if is_active else 0, now)
            )
            conn.commit()

    def get_ecommerce_adapter(self, company_id: str) -> BaseECommerceAdapter:
        rec = self.get_integration_record(company_id, "ecommerce")
        if not rec or not rec["is_active"]:
            return UnconfiguredECommerceAdapter()

        provider = rec["provider"]
        config = json.loads(rec["config_json"]) if rec["config_json"] else {}

        if provider == "rest_api":
            return RestApiECommerceAdapter(
                endpoint_url=config.get("endpoint_url", ""),
                api_key=config.get("api_key")
            )
        return UnconfiguredECommerceAdapter()

    def get_inventory_adapter(self, company_id: str) -> BaseInventoryAdapter:
        rec = self.get_integration_record(company_id, "inventory")
        if not rec or not rec["is_active"]:
            return UnconfiguredInventoryAdapter()

        provider = rec["provider"]
        config = json.loads(rec["config_json"]) if rec["config_json"] else {}

        if provider == "rest_api":
            return RestApiInventoryAdapter(
                endpoint_url=config.get("endpoint_url", ""),
                api_key=config.get("api_key")
            )
        return UnconfiguredInventoryAdapter()


# Global integration manager singleton
integration_manager = IntegrationManager()


# -------------------------------------------------------------
# High-Level Real Tool Implementations (Callable by Agent)
# -------------------------------------------------------------

def get_order_details(order_id: str, company_id: str, customer_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetches live order information from configured integration.
    Strictly verifies customer authorization when customer_id is provided.
    Never invents orders or customer records.
    """
    adapter = integration_manager.get_ecommerce_adapter(company_id)
    result = adapter.get_order(order_id)

    if result.get("status") != "success":
        return result

    order_data = result.get("data", {})

    # Authorization Check
    # If customer_id is specified in the session, ensure this order belongs to them
    if customer_id:
        order_cust_id = str(order_data.get("customer_id") or order_data.get("customer_email") or "")
        clean_cust_id = str(customer_id).strip().lower()
        if clean_cust_id not in order_cust_id.lower():
            logger.warning(f"Unauthorized order access attempt: customer {customer_id} tried accessing order {order_id}")
            return {
                "status": "unauthorized",
                "source": "orders_api",
                "order_id": order_id,
                "message": f"Access denied: You are not authorized to view order #{order_id}."
            }

    return result


def check_inventory(product_id: str, company_id: str) -> Dict[str, Any]:
    """
    Queries live inventory integration for real-time stock levels.
    Never fabricates stock quantities.
    """
    adapter = integration_manager.get_inventory_adapter(company_id)
    return adapter.get_stock(product_id)


def check_return_eligibility(
    order_id: str,
    company_id: str,
    customer_id: Optional[str] = None,
    reason: Optional[str] = None
) -> Dict[str, Any]:
    """
    Determines return eligibility by:
    1. Verifying real order details through configured e-commerce source.
    2. Retrieving company's verified return policy documents via knowledge_base.
    3. Applying policy rules (e.g. 30-day window, delivery status) to verified order facts.
    4. Explaining the decision and citing policy documents.
    """
    # Step 1: Verify order
    order_res = get_order_details(order_id, company_id, customer_id)
    if order_res.get("status") != "success":
        return {
            "status": "unable_to_determine",
            "source": "return_eligibility",
            "order_id": order_id,
            "reason": f"Cannot determine eligibility: {order_res.get('message', 'Order could not be verified.')}"
        }

    order_data = order_res.get("data", {})
    delivery_date_str = order_data.get("delivery_date")
    order_status = order_data.get("status")

    if not order_status or order_status.lower() != "delivered":
        return {
            "status": "ineligible",
            "source": "return_eligibility",
            "order_id": order_id,
            "reason": f"Order #{order_id} is currently '{order_status or 'unknown'}'. Returns can only be initiated after delivery."
        }

    # Step 2: Retrieve verified company return policy
    policy_res = knowledge_base.retrieve_company_knowledge(
        company_id=company_id,
        query="return policy refund return window eligibility restocking fee conditions",
        top_k=3,
        similarity_threshold=0.3
    )

    chunks = policy_res.get("chunks", [])
    if not chunks:
        return {
            "status": "unable_to_determine",
            "source": "return_eligibility",
            "order_id": order_id,
            "reason": "No return policy document found in company knowledge base. Please upload company policy documents.",
            "order_verified": True
        }

    # Citations
    citations = [{"filename": c["filename"], "location": c["location"], "excerpt": c["content"][:200]} for c in chunks]
    combined_policy_text = "\n\n".join([f"[{c['filename']} - {c['location']}]: {c['content']}" for c in chunks])

    # Check delivery date window
    if not delivery_date_str:
        return {
            "status": "unable_to_determine",
            "source": "return_eligibility",
            "order_id": order_id,
            "reason": "Order delivery date is missing from live order records. Cannot calculate policy return window.",
            "citations": citations
        }

    try:
        delivery_date = datetime.datetime.fromisoformat(delivery_date_str.replace("Z", "+00:00")).date()
    except Exception:
        try:
            delivery_date = datetime.datetime.strptime(delivery_date_str[:10], "%Y-%m-%d").date()
        except Exception:
            return {
                "status": "unable_to_determine",
                "source": "return_eligibility",
                "order_id": order_id,
                "reason": f"Invalid delivery date format '{delivery_date_str}'.",
                "citations": citations
            }

    days_since_delivery = (datetime.date.today() - delivery_date).days

    # Check window (typically 30 days unless policy specifies otherwise)
    # Default 30-day window check based on extracted policy
    return_window = 30
    if "14 days" in combined_policy_text.lower():
        return_window = 14
    elif "60 days" in combined_policy_text.lower():
        return_window = 60

    if days_since_delivery > return_window:
        return {
            "status": "ineligible",
            "source": "return_eligibility",
            "order_id": order_id,
            "days_since_delivery": days_since_delivery,
            "policy_window_days": return_window,
            "reason": f"The return window of {return_window} days has expired. Order was delivered {days_since_delivery} days ago on {delivery_date_str}.",
            "citations": citations
        }

    return {
        "status": "eligible",
        "source": "return_eligibility",
        "order_id": order_id,
        "days_since_delivery": days_since_delivery,
        "policy_window_days": return_window,
        "reason": f"Order #{order_id} is eligible for return. Delivered {days_since_delivery} days ago on {delivery_date_str} (within the {return_window}-day return window).",
        "citations": citations,
        "order_summary": {
            "order_id": order_id,
            "total": order_data.get("total"),
            "status": order_status,
            "delivery_date": delivery_date_str
        }
    }
