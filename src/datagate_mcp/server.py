"""Read-only MCP server for the DataGate billing platform API."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from datagate_mcp.client import DataGateClient

mcp = FastMCP(
    "datagate",
    instructions="Read-only access to the DataGate billing platform — customers, invoices, products, agreements, and sites.",
)


def _client() -> DataGateClient:
    return DataGateClient()


# -- Customers -------------------------------------------------------------


@mcp.tool()
def list_customers(page: int = 1, page_size: int = 50) -> dict:
    """List all customers with pagination.

    Returns customers with company name, code, address, active status, and billing config.
    Default page_size is 50, max varies by DataGate config.
    """
    with _client() as c:
        return c.list_customers(page, page_size)


@mcp.tool()
def get_customer(customer_id: str) -> dict:
    """Get a single customer by ID (UUID).

    Returns full customer details including address, agreement, account manager,
    delivery method, tax rate, and custom fields.
    """
    with _client() as c:
        return c.get_customer(customer_id)


# -- Invoices --------------------------------------------------------------


@mcp.tool()
def search_invoices(
    invoice_date: str | None = None,
    period_start: str | None = None,
    period_end: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """Search invoices with optional filters.

    Args:
        invoice_date: Exact invoice date (YYYY-MM-DD). For monthly billing,
            use the 1st of the month (e.g., "2026-01-01" for December billing).
        period_start: Billing period start date (YYYY-MM-DD).
        period_end: Billing period end date (YYYY-MM-DD).
        page: Page number (1-indexed).
        page_size: Results per page (default 50).

    Returns invoices with number, dates, customer, amounts, and status.
    """
    with _client() as c:
        return c.search_invoices(invoice_date, period_start, period_end, page, page_size)


@mcp.tool()
def get_invoice_details(invoice_id: str) -> dict:
    """Get full invoice details with line-item transactions.

    Returns the invoice header plus transactions array. Each transaction has
    productCode, productLabel, quantity, amount (commission base), tax, and total.
    """
    with _client() as c:
        return c.get_invoice_details(invoice_id)


# -- Products --------------------------------------------------------------


@mcp.tool()
def list_products(
    customer_id: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """List products/services with pricing.

    Optionally filter by customer_id (UUID). Products include charges with
    sell amounts, which represent recurring or one-time billing.

    Args:
        customer_id: Filter to a specific customer's products.
        page: Page number (1-indexed).
        page_size: Results per page (default 50).
    """
    with _client() as c:
        return c.list_products(customer_id, page, page_size)


@mcp.tool()
def get_product(product_id: str) -> dict:
    """Get a single product by ID with full charge details."""
    with _client() as c:
        return c.get_product(product_id)


# -- Agreements ------------------------------------------------------------


@mcp.tool()
def list_agreements(
    customer_id: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """List billing agreements.

    Most customers have a single "Default Agreement" with billing frequency
    and payment terms. Filter by customer_id to see a specific customer's agreements.
    """
    with _client() as c:
        return c.list_agreements(customer_id, page, page_size)


@mcp.tool()
def get_agreement(agreement_id: str) -> dict:
    """Get a single agreement by ID.

    Note: DataGate returns this as an array (API quirk).
    """
    with _client() as c:
        return c.get_agreement(agreement_id)


# -- Sites -----------------------------------------------------------------


@mcp.tool()
def list_sites(
    customer_id: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """List physical site locations.

    Sites are addresses associated with customers. Filter by customer_id
    to see a specific customer's locations.
    """
    with _client() as c:
        return c.list_sites(customer_id, page, page_size)


# -- Other -----------------------------------------------------------------


@mcp.tool()
def list_customer_users(page: int = 1, page_size: int = 50) -> dict:
    """List portal login accounts for customers."""
    with _client() as c:
        return c.list_customer_users(page, page_size)


@mcp.tool()
def list_service_items(
    customer_id: str | None = None,
    site: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """List service items, optionally filtered by customer or site."""
    with _client() as c:
        return c.list_service_items(customer_id, site, page, page_size)


@mcp.tool()
def list_rate_cards(page: int = 1, page_size: int = 50) -> dict:
    """List rate cards."""
    with _client() as c:
        return c.list_rate_cards(page, page_size)


@mcp.tool()
def list_kit_templates(page: int = 1, page_size: int = 50) -> dict:
    """List kit templates."""
    with _client() as c:
        return c.list_kit_templates(page, page_size)


def main() -> None:
    """Entry point for `datagate-mcp` command."""
    mcp.run()


if __name__ == "__main__":
    main()
