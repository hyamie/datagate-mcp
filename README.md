# datagate-mcp

MCP server and CLI for the [DataGate](https://dgportal.net) billing platform API.

- **MCP server** — read-only tools for Claude Desktop, Claude Code, and other MCP clients
- **CLI** — full CRUD for managing customers, invoices, products, agreements, sites, and payments

## Install

```bash
pip install datagate-mcp
```

Or run the MCP server directly:

```bash
uvx datagate-mcp
```

## Configuration

Set two environment variables:

| Variable | Description |
|----------|-------------|
| `DATAGATE_API_KEY` | Bearer token from DataGate portal |
| `DATAGATE_CLIENT_ID` | Integration GUID from DataGate portal |
| `DATAGATE_BASE_URL` | *(optional)* Override base URL (default: `https://api.dgportal.net`) |

## MCP Setup

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "datagate": {
      "command": "uvx",
      "args": ["datagate-mcp"],
      "env": {
        "DATAGATE_API_KEY": "your-api-key",
        "DATAGATE_CLIENT_ID": "your-client-id"
      }
    }
  }
}
```

### Claude Code

Add to `.mcp.json`:

```json
{
  "mcpServers": {
    "datagate": {
      "command": "uvx",
      "args": ["datagate-mcp"],
      "env": {
        "DATAGATE_API_KEY": "your-api-key",
        "DATAGATE_CLIENT_ID": "your-client-id"
      }
    }
  }
}
```

## CLI Usage

```bash
# List customers
datagate customers list
datagate customers list --page 2 --page-size 25

# Get a customer
datagate customers get <customer-id>

# Search invoices
datagate invoices search --invoice-date 2026-01-01
datagate invoices search --period-start 2025-12-01 --period-end 2025-12-31

# Invoice line items
datagate invoices details <invoice-id>

# List products (optionally by customer)
datagate products list --customer-id <id>

# JSON output
datagate --json customers list
```

### Write Operations

All write commands require `--confirm`:

```bash
datagate customers create --name "Acme Corp" --code "50099"
datagate customers update <id> --data '{"companyName": "Acme Corp LLC"}'
datagate customers delete <id> --confirm

datagate products create --customer-id <id> --code "Internet 1Gb"
datagate sites create --customer-id <id> --name "123 Main St"

# Payments are IRREVERSIBLE — void only via DataGate portal
datagate payments create --customer-id <id> --amount 100.00 --confirm
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `list_customers` | List customers with pagination |
| `get_customer` | Get single customer by ID |
| `search_invoices` | Search invoices by date/period |
| `get_invoice_details` | Invoice with line-item transactions |
| `list_products` | Products with pricing, filterable by customer |
| `get_product` | Single product with charges |
| `list_agreements` | Billing agreements, filterable by customer |
| `get_agreement` | Single agreement |
| `list_sites` | Physical locations, filterable by customer |
| `list_customer_users` | Portal login accounts |
| `list_service_items` | Service items |
| `list_rate_cards` | Rate cards |
| `list_kit_templates` | Kit templates |

## Rate Limits

- 60 calls/minute
- 5,000 calls/day
- The client automatically paces requests to stay within limits.

## License

MIT
