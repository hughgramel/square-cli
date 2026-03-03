# Square CLI

A command-line interface for Square — manage catalog, sales, inventory, customers, and more from the terminal. Modeled after the [Stripe CLI](https://github.com/stripe/stripe-cli).

```bash
pip install square-cli
```

## Quick Start

```bash
# Authenticate (stores credentials in your OS keychain)
square login

# View your catalog
square catalog list

# This week's sales by item
square sales --days 7 --by-item

# Search products
square catalog search "coffee"

# Low stock alerts
square inventory list --low-stock 10

# Pipe JSON to jq
square payments list --days 7 -f json | jq '.[].amount'
```

## Authentication

Credentials are stored in your OS keychain (macOS Keychain / Windows Credential Manager) — never in plaintext files.

```bash
square login                # OAuth browser flow → keychain
square login --sandbox      # Use sandbox environment
square login --profile dev  # Auth into named profile
square status               # Check auth state
square logout               # Clear credentials
```

You can also set `SQUARE_ACCESS_TOKEN` as an environment variable for CI/CD or scripting.

## Commands

### Auth & Config

| Command | Description |
|---|---|
| `square login` | Authenticate via OAuth browser flow |
| `square logout` | Clear stored credentials |
| `square status` | Show auth state, environment, location |
| `square config list` | View all config values |
| `square config set <key> <value>` | Set a config value |
| `square config unset <key>` | Remove a config value |
| `square config edit` | Open config in `$EDITOR` |

### Catalog

```bash
square catalog list                          # List all items
square catalog list --type CATEGORY          # Filter by type
square catalog get <object-id>               # Single item details
square catalog search "red bull"             # Search by text
square catalog create --name "Latte" --price 4.50 --sku LATTE001
square catalog update <id> --price 4.75      # Update fields
square catalog update <id> --price 4.75 --dry-run  # Preview changes
square catalog delete <id>                   # Delete (with confirmation)
square catalog export -o catalog.json        # Export full catalog
square catalog export -o catalog.csv -f csv  # Export as CSV
```

### Sales Reports

```bash
square sales                                 # Revenue summary (last 7 days)
square sales --days 30                       # Last 30 days
square sales --by-item                       # Breakdown by product
square sales --by-day                        # Daily revenue trend
square sales --by-hour                       # Peak hours analysis
square sales --by-category                   # By category
square sales --by-payment-method             # Cash vs card vs digital
square sales --top 10                        # Top 10 by revenue
square sales --bottom 5                      # Worst performers
square sales --start 2025-01-01 --end 2025-01-31  # Custom date range
```

### Orders

```bash
square orders list                           # Recent orders (7 days)
square orders list --days 30 --status COMPLETED
square orders get <order-id>                 # Order details + line items
```

### Payments

```bash
square payments list                         # Recent payments
square payments list --days 30 --status COMPLETED
square payments get <payment-id>             # Payment details
square payments refund <id> --amount 5.00 --reason "Damaged"
square payments refund <id> --full           # Full refund
```

### Refunds

```bash
square refunds list --days 30
square refunds get <refund-id>
```

### Inventory

```bash
square inventory list                        # All stock levels
square inventory list --low-stock 10         # Low stock alerts
square inventory list --out-of-stock         # Zero stock items
square inventory get <variation-id>          # Stock for one item
square inventory adjust <id> --delta -5      # Relative adjustment
square inventory adjust <id> --delta 24 --reason "Restocked"
square inventory set <id> --count 50         # Absolute count
square inventory history <id>                # Change history
```

### Customers

```bash
square customers list
square customers get <id>
square customers search "John"
square customers create --name "John Doe" --email john@example.com
square customers update <id> --note "VIP"
square customers delete <id>
```

### Locations

```bash
square locations list                        # All business locations
square locations get <location-id>
square locations set-default <location-id>   # Set default location
```

### Team & Labor

```bash
square team list                             # List team members
square team get <member-id>
square team create --first Jane --last Doe --email jane@example.com

square labor shifts list --days 7
square labor shifts list --member <id>
square labor timecards list --days 14
```

### Loyalty

```bash
square loyalty program                       # View program config
square loyalty accounts list
square loyalty accounts get <id>
square loyalty accounts search --phone 555-1234
square loyalty points <account-id> --points 10 --reason "Bonus"
```

### Gift Cards

```bash
square gift-cards list
square gift-cards get <card-id>
square gift-cards create --amount 25.00
square gift-cards activity <card-id>         # Transaction history
```

### Invoices

```bash
square invoices list
square invoices list --status UNPAID
square invoices get <invoice-id>
square invoices send <invoice-id>            # Publish & email
square invoices cancel <invoice-id>
```

### Disputes

```bash
square disputes list
square disputes get <dispute-id>
square disputes accept <dispute-id>          # Concede chargeback
```

### Subscriptions

```bash
square subscriptions list
square subscriptions get <id>
square subscriptions cancel <id>
square subscriptions pause <id>
square subscriptions resume <id>
```

### Vendors

```bash
square vendors list
square vendors get <vendor-id>
square vendors create --name "Costco" --note "Warehouse 115"
square vendors search "Costco"
square vendors update <id> --note "Updated note"
```

### Webhooks

```bash
square webhooks list
square webhooks create --name "Orders" --url https://example.com/hook --events order.created
square webhooks delete <id>
square webhooks event-types                  # List all event types
```

### Raw HTTP

For any Square API endpoint not covered by a dedicated command:

```bash
square get /v2/catalog/list
square post /v2/catalog/search -d '{"query": {"text_query": {"keywords": ["coffee"]}}}'
```

### Utility

```bash
square version                               # CLI version
square resources                             # List all resource types
square docs                                  # Open Square API docs
square docs catalog                          # Docs for specific resource
square feedback                              # Open GitHub issues
```

## Global Flags

Every command supports:

| Flag | Short | Description |
|---|---|---|
| `--format` | `-f` | Output format: `table`, `json`, `csv` |
| `--profile` | `-p` | Named profile (for multiple Square accounts) |
| `--sandbox` | | Use sandbox environment |
| `--access-token` | | Override token for this command |
| `--help` | | Show help |

## Output Formats

```bash
# Human-readable table (default)
square sales --days 7 --by-item

# JSON (pipe to jq, scripts, etc.)
square sales --days 7 --by-item -f json | jq '.[] | select(.units > 50)'

# CSV (spreadsheets, data analysis)
square catalog list -f csv > catalog.csv
```

## Configuration

Config file: `~/.config/square/config.toml`

```toml
[default]
environment = "production"
location_id = "LXXXX"
format = "table"

[staging]
environment = "sandbox"
```

Tokens are stored in your OS keychain, never in the config file.

## Requirements

- Python 3.11+
- A [Square account](https://squareup.com) (free to create)

## License

MIT
