"""Core HTTP client for the DataGate billing platform API."""

from __future__ import annotations

import os
import time
from typing import Any

import httpx

DEFAULT_BASE_URL = "https://api.dgportal.net"
DEFAULT_PAGE_SIZE = 50
RATE_LIMIT_PER_MIN = 60


class DataGateError(Exception):
    """Raised when the DataGate API returns an error."""

    def __init__(self, status_code: int, code: str, details: str) -> None:
        self.status_code = status_code
        self.code = code
        self.details = details
        super().__init__(f"DataGate {status_code}: {code} — {details}")


class RateLimitError(DataGateError):
    """Raised on HTTP 429."""

    def __init__(self, retry_after: int | None = None) -> None:
        self.retry_after = retry_after
        super().__init__(429, "rate_limit", f"Retry after {retry_after}s")


class DataGateClient:
    """Shared HTTP client for DataGate API.

    Configuration via env vars:
        DATAGATE_API_KEY   — Bearer token (required)
        DATAGATE_CLIENT_ID — Integration GUID (required)
        DATAGATE_BASE_URL  — Override base URL (default: production)
    """

    def __init__(
        self,
        api_key: str | None = None,
        client_id: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("DATAGATE_API_KEY", "")
        self.client_id = client_id or os.environ.get("DATAGATE_CLIENT_ID", "")
        self.base_url = (
            base_url
            or os.environ.get("DATAGATE_BASE_URL", "")
            or DEFAULT_BASE_URL
        )

        if not self.api_key:
            raise ValueError(
                "DATAGATE_API_KEY is required (env var or constructor arg)"
            )
        if not self.client_id:
            raise ValueError(
                "DATAGATE_CLIENT_ID is required (env var or constructor arg)"
            )

        self._http = httpx.Client(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "ClientID": self.client_id,
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
        self._call_count = 0
        self._window_start = time.monotonic()

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> DataGateClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    # -- Low-level ---------------------------------------------------------

    def _pace(self) -> None:
        """Simple rate-limit pacer: track calls within a 60s window."""
        now = time.monotonic()
        if now - self._window_start > 60:
            self._call_count = 0
            self._window_start = now

        self._call_count += 1
        if self._call_count >= RATE_LIMIT_PER_MIN - 5:  # 5-call buffer
            elapsed = now - self._window_start
            if elapsed < 60:
                time.sleep(60 - elapsed + 0.5)
            self._call_count = 0
            self._window_start = time.monotonic()

    def _handle_error(self, resp: httpx.Response) -> None:
        if resp.status_code == 429:
            retry = resp.headers.get("Retry-After")
            raise RateLimitError(int(retry) if retry else None)

        if resp.status_code >= 400:
            try:
                body = resp.json()
                code = body.get("code", "unknown")
                details = body.get("details", resp.text)
            except Exception:
                code = "unknown"
                details = resp.text
            raise DataGateError(resp.status_code, code, details)

    def get(self, path: str, params: dict | None = None) -> Any:
        self._pace()
        resp = self._http.get(path, params=params)
        self._handle_error(resp)
        return resp.json()

    def post(self, path: str, json: dict | None = None, params: dict | None = None) -> Any:
        self._pace()
        resp = self._http.post(path, json=json, params=params)
        self._handle_error(resp)
        return resp.json()

    def put(self, path: str, json: dict | None = None) -> Any:
        self._pace()
        resp = self._http.put(path, json=json)
        self._handle_error(resp)
        return resp.json()

    def delete(self, path: str) -> Any:
        self._pace()
        resp = self._http.delete(path)
        self._handle_error(resp)
        if resp.status_code == 204:
            return None
        return resp.json()

    # -- Pagination --------------------------------------------------------

    def get_all_pages(
        self, path: str, params: dict | None = None, page_size: int = DEFAULT_PAGE_SIZE,
    ) -> list[dict]:
        """Fetch all pages from a paginated GET endpoint."""
        params = dict(params or {})
        params["pageSize"] = page_size
        params["page"] = 1
        all_data: list[dict] = []

        while True:
            result = self.get(path, params=params)
            all_data.extend(result["data"])
            if params["page"] >= result.get("pages", 1):
                break
            params["page"] += 1

        return all_data

    def post_all_pages(
        self, path: str, json: dict | None = None, page_size: int = DEFAULT_PAGE_SIZE,
    ) -> list[dict]:
        """Fetch all pages from a paginated POST endpoint (e.g., invoice search)."""
        all_data: list[dict] = []
        page = 1

        while True:
            result = self.post(
                path,
                json=json,
                params={"page": page, "pageSize": page_size},
            )
            all_data.extend(result["data"])
            if page >= result.get("pages", 1):
                break
            page += 1

        return all_data

    # -- Customers ---------------------------------------------------------

    def list_customers(
        self, page: int = 1, page_size: int = DEFAULT_PAGE_SIZE,
    ) -> dict:
        return self.get("/customers", {"page": page, "pageSize": page_size})

    def get_customer(self, customer_id: str) -> dict:
        return self.get(f"/customers/{customer_id}")

    def create_customer(self, data: dict) -> dict:
        return self.post("/customers", json=data)

    def update_customer(self, customer_id: str, data: dict) -> dict:
        return self.put(f"/customers/{customer_id}", json=data)

    def delete_customer(self, customer_id: str) -> Any:
        return self.delete(f"/customers/{customer_id}")

    # -- Invoices ----------------------------------------------------------

    def search_invoices(
        self,
        invoice_date: str | None = None,
        period_start: str | None = None,
        period_end: str | None = None,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> dict:
        body: dict[str, str] = {}
        if invoice_date:
            body["invoiceDate"] = invoice_date
        if period_start:
            body["periodStart"] = period_start
        if period_end:
            body["periodEnd"] = period_end
        return self.post(
            "/invoices/search",
            json=body,
            params={"page": page, "pageSize": page_size},
        )

    def get_invoice_details(self, invoice_id: str) -> dict:
        return self.get(f"/invoices/{invoice_id}/details")

    # -- Products ----------------------------------------------------------

    def list_products(
        self,
        customer_id: str | None = None,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> dict:
        params: dict[str, Any] = {"page": page, "pageSize": page_size}
        if customer_id:
            params["customer.id"] = customer_id
        return self.get("/products", params)

    def get_product(self, product_id: str) -> dict:
        return self.get(f"/products/{product_id}")

    def create_product(self, data: dict) -> dict:
        return self.post("/products", json=data)

    def update_product(self, product_id: str, data: dict) -> dict:
        return self.put(f"/products/{product_id}", json=data)

    def delete_product(self, product_id: str) -> Any:
        return self.delete(f"/products/{product_id}")

    # -- Agreements --------------------------------------------------------

    def list_agreements(
        self,
        customer_id: str | None = None,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> dict:
        params: dict[str, Any] = {"page": page, "pageSize": page_size}
        if customer_id:
            params["customer.id"] = customer_id
        return self.get("/agreements", params)

    def get_agreement(self, agreement_id: str) -> dict:
        return self.get(f"/agreements/{agreement_id}")

    def create_agreement(self, data: dict) -> dict:
        return self.post("/agreements", json=data)

    def update_agreement(self, agreement_id: str, data: dict) -> dict:
        return self.put(f"/agreements/{agreement_id}", json=data)

    def delete_agreement(self, agreement_id: str) -> Any:
        return self.delete(f"/agreements/{agreement_id}")

    # -- Sites -------------------------------------------------------------

    def list_sites(
        self,
        customer_id: str | None = None,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> dict:
        params: dict[str, Any] = {"page": page, "pageSize": page_size}
        if customer_id:
            params["customer.id"] = customer_id
        return self.get("/sites", params)

    def get_site(self, site_id: str) -> dict:
        return self.get(f"/sites/{site_id}")

    def create_site(self, data: dict) -> dict:
        return self.post("/sites", json=data)

    def update_site(self, site_id: str, data: dict) -> dict:
        return self.put(f"/sites/{site_id}", json=data)

    def delete_site(self, site_id: str) -> Any:
        return self.delete(f"/sites/{site_id}")

    # -- Customer Users ----------------------------------------------------

    def list_customer_users(
        self, page: int = 1, page_size: int = DEFAULT_PAGE_SIZE,
    ) -> dict:
        return self.get("/customer-users", {"page": page, "pageSize": page_size})

    # -- Service Items -----------------------------------------------------

    def list_service_items(
        self,
        customer_id: str | None = None,
        site: str | None = None,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> dict:
        params: dict[str, Any] = {"page": page, "pageSize": page_size}
        if customer_id:
            params["customer.id"] = customer_id
        if site:
            params["site"] = site
        return self.get("/service-items", params)

    # -- Rate Cards --------------------------------------------------------

    def list_rate_cards(
        self, page: int = 1, page_size: int = DEFAULT_PAGE_SIZE,
    ) -> dict:
        return self.get("/rating/ratecards", {"page": page, "pageSize": page_size})

    # -- Kit Templates -----------------------------------------------------

    def list_kit_templates(
        self, page: int = 1, page_size: int = DEFAULT_PAGE_SIZE,
    ) -> dict:
        return self.get("/kit-templates", {"page": page, "pageSize": page_size})

    # -- Payments ----------------------------------------------------------

    def create_payment(self, customer_id: str, amount: float) -> str:
        """Create a payment. WARNING: No undo — void in portal only."""
        result = self.post(
            "/payments",
            json={"customer": {"id": customer_id}, "amount": amount},
        )
        return result
