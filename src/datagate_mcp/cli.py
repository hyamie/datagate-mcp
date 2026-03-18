"""Full-CRUD CLI for the DataGate billing platform API."""

from __future__ import annotations

import json
import sys

import click
from rich.console import Console
from rich.table import Table

from datagate_mcp.client import DataGateClient, DataGateError

console = Console()


def _client() -> DataGateClient:
    try:
        return DataGateClient()
    except ValueError as e:
        console.print(f"[red]Configuration error:[/red] {e}")
        console.print(
            "Set DATAGATE_API_KEY and DATAGATE_CLIENT_ID environment variables."
        )
        sys.exit(1)


def _output(data, output_json: bool) -> None:
    """Print data as JSON or a summary."""
    if output_json:
        click.echo(json.dumps(data, indent=2, default=str))
    else:
        click.echo(json.dumps(data, indent=2, default=str))


def _paginated_table(result: dict, columns: list[tuple[str, str]], title: str) -> None:
    """Render a paginated API result as a rich table."""
    table = Table(title=f"{title} (page {result['page']}/{result['pages']}, {result['records']} total)")
    for col_name, _ in columns:
        table.add_column(col_name)

    for row in result["data"]:
        values = []
        for _, key in columns:
            val = row
            for part in key.split("."):
                if isinstance(val, dict):
                    val = val.get(part, "")
                else:
                    val = ""
            values.append(str(val) if val is not None else "")
        table.add_row(*values)

    console.print(table)


# -- Main group ------------------------------------------------------------


@click.group()
@click.option("--json", "output_json", is_flag=True, help="Output raw JSON")
@click.pass_context
def cli(ctx: click.Context, output_json: bool) -> None:
    """DataGate CLI — manage customers, invoices, products, and more."""
    ctx.ensure_object(dict)
    ctx.obj["json"] = output_json


# -- Customers -------------------------------------------------------------


@cli.group()
def customers() -> None:
    """Manage customers."""


@customers.command("list")
@click.option("--page", default=1, help="Page number")
@click.option("--page-size", default=50, help="Results per page")
@click.pass_context
def customers_list(ctx: click.Context, page: int, page_size: int) -> None:
    """List all customers."""
    with _client() as c:
        result = c.list_customers(page, page_size)

    if ctx.obj["json"]:
        _output(result, True)
    else:
        _paginated_table(result, [
            ("Name", "companyName"),
            ("Code", "customerCode"),
            ("Active", "isActive"),
            ("ID", "id"),
        ], "Customers")


@customers.command("get")
@click.argument("customer_id")
@click.pass_context
def customers_get(ctx: click.Context, customer_id: str) -> None:
    """Get a single customer by ID."""
    with _client() as c:
        result = c.get_customer(customer_id)
    _output(result, True)


@customers.command("create")
@click.option("--name", required=True, help="Company name")
@click.option("--code", default="", help="Customer code")
@click.option("--data", "extra_data", default="{}", help="Additional fields as JSON")
@click.pass_context
def customers_create(ctx: click.Context, name: str, code: str, extra_data: str) -> None:
    """Create a new customer."""
    payload = json.loads(extra_data)
    payload["companyName"] = name
    if code:
        payload["customerCode"] = code

    with _client() as c:
        result = c.create_customer(payload)
    _output(result, True)
    console.print("[green]Customer created.[/green]")


@customers.command("update")
@click.argument("customer_id")
@click.option("--data", "update_data", required=True, help="Fields to update as JSON")
@click.pass_context
def customers_update(ctx: click.Context, customer_id: str, update_data: str) -> None:
    """Update a customer."""
    payload = json.loads(update_data)
    with _client() as c:
        result = c.update_customer(customer_id, payload)
    _output(result, True)
    console.print("[green]Customer updated.[/green]")


@customers.command("delete")
@click.argument("customer_id")
@click.option("--confirm", is_flag=True, required=True, help="Confirm deletion")
@click.pass_context
def customers_delete(ctx: click.Context, customer_id: str, confirm: bool) -> None:
    """Delete a customer. Requires --confirm."""
    with _client() as c:
        c.delete_customer(customer_id)
    console.print("[green]Customer deleted.[/green]")


# -- Invoices --------------------------------------------------------------


@cli.group()
def invoices() -> None:
    """Search and view invoices."""


@invoices.command("search")
@click.option("--invoice-date", default=None, help="Invoice date (YYYY-MM-DD)")
@click.option("--period-start", default=None, help="Billing period start (YYYY-MM-DD)")
@click.option("--period-end", default=None, help="Billing period end (YYYY-MM-DD)")
@click.option("--page", default=1, help="Page number")
@click.option("--page-size", default=50, help="Results per page")
@click.pass_context
def invoices_search(
    ctx: click.Context,
    invoice_date: str | None,
    period_start: str | None,
    period_end: str | None,
    page: int,
    page_size: int,
) -> None:
    """Search invoices with optional filters."""
    with _client() as c:
        result = c.search_invoices(invoice_date, period_start, period_end, page, page_size)

    if ctx.obj["json"]:
        _output(result, True)
    else:
        _paginated_table(result, [
            ("Invoice #", "invoiceNumber"),
            ("Customer", "customer.name"),
            ("Date", "invoiceDate"),
            ("Amount", "amount"),
            ("Status", "status.name"),
        ], "Invoices")


@invoices.command("details")
@click.argument("invoice_id")
@click.pass_context
def invoices_details(ctx: click.Context, invoice_id: str) -> None:
    """Get full invoice details with line items."""
    with _client() as c:
        result = c.get_invoice_details(invoice_id)

    if ctx.obj["json"]:
        _output(result, True)
    else:
        console.print(f"[bold]Invoice:[/bold] {result.get('invoiceNumber', 'N/A')}")
        console.print(f"[bold]Date:[/bold] {result.get('invoiceDate', 'N/A')}")
        console.print()

        txns = result.get("transactions", [])
        if txns:
            table = Table(title="Transactions")
            table.add_column("Product")
            table.add_column("Qty", justify="right")
            table.add_column("Amount", justify="right")
            table.add_column("Tax", justify="right")
            table.add_column("Total", justify="right")

            for tx in txns:
                table.add_row(
                    tx.get("productLabel", tx.get("productCode", "")),
                    str(tx.get("quantity", "")),
                    f"${tx.get('amount', 0):,.2f}",
                    f"${tx.get('tax', 0):,.2f}",
                    f"${tx.get('total', 0):,.2f}",
                )

            total = sum(t.get("amount", 0) for t in txns)
            table.add_section()
            table.add_row("[bold]Total[/bold]", "", f"[bold]${total:,.2f}[/bold]", "", "")
            console.print(table)
        else:
            console.print("[dim]No transactions.[/dim]")


# -- Products --------------------------------------------------------------


@cli.group()
def products() -> None:
    """Manage products/services."""


@products.command("list")
@click.option("--customer-id", default=None, help="Filter by customer ID")
@click.option("--page", default=1, help="Page number")
@click.option("--page-size", default=50, help="Results per page")
@click.pass_context
def products_list(ctx: click.Context, customer_id: str | None, page: int, page_size: int) -> None:
    """List products with pricing."""
    with _client() as c:
        result = c.list_products(customer_id, page, page_size)

    if ctx.obj["json"]:
        _output(result, True)
    else:
        _paginated_table(result, [
            ("Code", "code"),
            ("Label", "label"),
            ("Customer", "customer.name"),
            ("Site", "site.name"),
            ("ID", "id"),
        ], "Products")


@products.command("get")
@click.argument("product_id")
@click.pass_context
def products_get(ctx: click.Context, product_id: str) -> None:
    """Get a single product with charges."""
    with _client() as c:
        result = c.get_product(product_id)
    _output(result, True)


@products.command("create")
@click.option("--customer-id", required=True, help="Customer ID")
@click.option("--code", required=True, help="Product code")
@click.option("--data", "extra_data", default="{}", help="Additional fields as JSON")
@click.pass_context
def products_create(ctx: click.Context, customer_id: str, code: str, extra_data: str) -> None:
    """Create a new product."""
    payload = json.loads(extra_data)
    payload["customer"] = {"id": customer_id}
    payload["code"] = code
    with _client() as c:
        result = c.create_product(payload)
    _output(result, True)
    console.print("[green]Product created.[/green]")


@products.command("update")
@click.argument("product_id")
@click.option("--data", "update_data", required=True, help="Fields to update as JSON")
@click.pass_context
def products_update(ctx: click.Context, product_id: str, update_data: str) -> None:
    """Update a product."""
    payload = json.loads(update_data)
    with _client() as c:
        result = c.update_product(product_id, payload)
    _output(result, True)
    console.print("[green]Product updated.[/green]")


@products.command("delete")
@click.argument("product_id")
@click.option("--confirm", is_flag=True, required=True, help="Confirm deletion")
@click.pass_context
def products_delete(ctx: click.Context, product_id: str, confirm: bool) -> None:
    """Delete a product. Requires --confirm."""
    with _client() as c:
        c.delete_product(product_id)
    console.print("[green]Product deleted.[/green]")


# -- Agreements ------------------------------------------------------------


@cli.group()
def agreements() -> None:
    """Manage billing agreements."""


@agreements.command("list")
@click.option("--customer-id", default=None, help="Filter by customer ID")
@click.option("--page", default=1, help="Page number")
@click.option("--page-size", default=50, help="Results per page")
@click.pass_context
def agreements_list(ctx: click.Context, customer_id: str | None, page: int, page_size: int) -> None:
    """List billing agreements."""
    with _client() as c:
        result = c.list_agreements(customer_id, page, page_size)

    if ctx.obj["json"]:
        _output(result, True)
    else:
        _paginated_table(result, [
            ("Name", "name"),
            ("Customer", "customer.name"),
            ("Default", "isDefault"),
            ("ID", "id"),
        ], "Agreements")


@agreements.command("get")
@click.argument("agreement_id")
@click.pass_context
def agreements_get(ctx: click.Context, agreement_id: str) -> None:
    """Get a single agreement."""
    with _client() as c:
        result = c.get_agreement(agreement_id)
    _output(result, True)


@agreements.command("create")
@click.option("--customer-id", required=True, help="Customer ID")
@click.option("--name", required=True, help="Agreement name")
@click.option("--data", "extra_data", default="{}", help="Additional fields as JSON")
@click.pass_context
def agreements_create(ctx: click.Context, customer_id: str, name: str, extra_data: str) -> None:
    """Create a new agreement."""
    payload = json.loads(extra_data)
    payload["customer"] = {"id": customer_id}
    payload["name"] = name
    with _client() as c:
        result = c.create_agreement(payload)
    _output(result, True)
    console.print("[green]Agreement created.[/green]")


@agreements.command("update")
@click.argument("agreement_id")
@click.option("--data", "update_data", required=True, help="Fields to update as JSON")
@click.pass_context
def agreements_update(ctx: click.Context, agreement_id: str, update_data: str) -> None:
    """Update an agreement."""
    payload = json.loads(update_data)
    with _client() as c:
        result = c.update_agreement(agreement_id, payload)
    _output(result, True)
    console.print("[green]Agreement updated.[/green]")


@agreements.command("delete")
@click.argument("agreement_id")
@click.option("--confirm", is_flag=True, required=True, help="Confirm deletion")
@click.pass_context
def agreements_delete(ctx: click.Context, agreement_id: str, confirm: bool) -> None:
    """Delete an agreement. Requires --confirm."""
    with _client() as c:
        c.delete_agreement(agreement_id)
    console.print("[green]Agreement deleted.[/green]")


# -- Sites -----------------------------------------------------------------


@cli.group()
def sites() -> None:
    """Manage physical site locations."""


@sites.command("list")
@click.option("--customer-id", default=None, help="Filter by customer ID")
@click.option("--page", default=1, help="Page number")
@click.option("--page-size", default=50, help="Results per page")
@click.pass_context
def sites_list(ctx: click.Context, customer_id: str | None, page: int, page_size: int) -> None:
    """List sites."""
    with _client() as c:
        result = c.list_sites(customer_id, page, page_size)

    if ctx.obj["json"]:
        _output(result, True)
    else:
        _paginated_table(result, [
            ("Name", "name"),
            ("Customer", "customer.name"),
            ("Code", "code"),
            ("ID", "id"),
        ], "Sites")


@sites.command("create")
@click.option("--customer-id", required=True, help="Customer ID")
@click.option("--name", required=True, help="Site name")
@click.option("--data", "extra_data", default="{}", help="Additional fields as JSON")
@click.pass_context
def sites_create(ctx: click.Context, customer_id: str, name: str, extra_data: str) -> None:
    """Create a new site."""
    payload = json.loads(extra_data)
    payload["customer"] = {"id": customer_id}
    payload["name"] = name
    with _client() as c:
        result = c.create_site(payload)
    _output(result, True)
    console.print("[green]Site created.[/green]")


@sites.command("update")
@click.argument("site_id")
@click.option("--data", "update_data", required=True, help="Fields to update as JSON")
@click.pass_context
def sites_update(ctx: click.Context, site_id: str, update_data: str) -> None:
    """Update a site."""
    payload = json.loads(update_data)
    with _client() as c:
        result = c.update_site(site_id, payload)
    _output(result, True)
    console.print("[green]Site updated.[/green]")


@sites.command("delete")
@click.argument("site_id")
@click.option("--confirm", is_flag=True, required=True, help="Confirm deletion")
@click.pass_context
def sites_delete(ctx: click.Context, site_id: str, confirm: bool) -> None:
    """Delete a site. Requires --confirm."""
    with _client() as c:
        c.delete_site(site_id)
    console.print("[green]Site deleted.[/green]")


# -- Payments --------------------------------------------------------------


@cli.group()
def payments() -> None:
    """Manage payments (write-only — no read/delete via API)."""


@payments.command("create")
@click.option("--customer-id", required=True, help="Customer ID (UUID)")
@click.option("--amount", required=True, type=float, help="Payment amount")
@click.option("--confirm", is_flag=True, required=True, help="Confirm payment (IRREVERSIBLE)")
@click.pass_context
def payments_create(ctx: click.Context, customer_id: str, amount: float, confirm: bool) -> None:
    """Create a payment. IRREVERSIBLE — cannot be voided via API.

    To void a payment, use the DataGate portal UI.
    """
    console.print(f"[yellow bold]WARNING: Creating ${amount:,.2f} payment for customer {customer_id}[/yellow bold]")
    console.print("[yellow]This action is IRREVERSIBLE via API. Void in DataGate portal only.[/yellow]")

    if not click.confirm("Proceed?"):
        console.print("[dim]Cancelled.[/dim]")
        return

    with _client() as c:
        result = c.create_payment(customer_id, amount)
    _output(result, True)
    console.print("[green]Payment created.[/green]")


if __name__ == "__main__":
    cli()
