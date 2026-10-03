# Retail Sale Chassis Description — Odoo 18

Module: `sale_chassis_description`. Depends only on `sale_stock`.

Enter the chassis **in the existing line Description**, below the product:

```text
TVS APACHE 180CC
DJHDGE73NSU73YGUDDUYEH
```

The text added below the product is free, with **at least 17 characters on one
line**. Colors, spaces, parentheses, hyphens and other punctuation are accepted:

```text
1GDHK33U25F914022 Yellow
1GDHK33U25F914022 (YELLOW)
1GDHK33U25F914022 - Yellow
```

Optional labels `Chassis Number:`, `Chassis:`, `Châssis:` and `VIN:` are accepted.
The automatic product description, optional label and surrounding whitespace
do not count toward the minimum. The complete entered text, including color,
is kept in sales, invoices and deliveries and printed on chassis tickets.
There is no VIN format, digit, exact-length or uniqueness validation; the
minimum applies to the entered text, including its color. Several descriptions
can be entered on separate lines; this simple module requires at least one
qualifying line on each configured product line, not one identifier per unit.

## Setup

Open **Settings → Sales → Retail Sale Chassis** for the current company.
Enable **Require chassis for retail sales**, select **Products requiring
chassis**, then Save. Selection applies to every variant of each selected
product. Services, notes and down payments are excluded. A fresh installation
starts disabled with no selected products. Disabling the requirement retains
the product list for later reactivation.

The product Sales tab no longer contains a chassis checkbox. This company's
settings are the sole source of mandatory chassis product selection. On upgrade,
previous product checkbox selections are copied to each relevant company and
activation is retained. Enabled `bike_identity` and `delivery_vehicle_identity`
selections, if installed, are imported once into this list. Later changes are
made here; deselecting a product removes this addon's requirement. Those addons
retain their independent policies and are not changed by these settings.

Only Settings administrators can change the configuration. Choose shared
products or products belonging to the current company. Enabling the requirement
requires at least one selected product.

## Sales workflow

1. Enter the chassis in the normal line description.
2. Click Confirm. For an unclassified motorcycle quotation, a popup asks
   **Retail / Détail** or **Wholesale / Gros**. There is no chassis-entry popup.
   Sale Type can also be chosen directly on the quotation.
3. Retail requires an added description line of at least 17 characters on each configured product line. If missing,
   the choice is saved and a message returns you to the draft quotation to edit
   its normal description. Confirm again after filling it.
4. Wholesale confirms without a chassis. Any supplied description is retained.

The type cannot change on a confirmed order; cancel it first. Direct server/RPC
confirmation also checks the requirements. Duplicating a quotation resets the
type choice. Cancelling an order clears its type choice; returning an already
cancelled order to draft also clears it. The next confirmation asks Retail or
Wholesale again, while existing descriptions and chassis are preserved.
Documents already confirmed before installation are not rewritten.

## Invoices and deliveries

Odoo copies the sales description into the invoice line. Sale Type follows the
sale into its invoice. Different types are kept in separate invoices when
several orders are invoiced together. Manual customer invoices use the same
classification popup at posting and retail check on the normal line description.
Credit notes are exempt from a new retail-entry requirement.

For outgoing stock moves on configured products, the full sales description is
copied into `stock.move.description_picking`. Native delivery slips show it in
the product row, including completed, serial/package and backorder layouts.
The existing Description column is displayed by default in the delivery Operations table.
For retail motorcycle sales, editing the sales line description also updates
linked outgoing deliveries that are not completed or cancelled. The chassis
therefore remains visible on the delivery order and its printed delivery slip.
Completed deliveries and issued invoices retain their existing descriptions. Editing a
standalone invoice does not update an unrelated sales order or delivery.

Partial documents copy the line description as text. There is no allocation of
individual chassis to quantities, stock lots or partial invoices. No POS changes.
Previously generated/downloaded PDF attachments are not regenerated.

## Chassis tickets (included)

The former `sale_chassis_ticket` functionality is now included in this module.
Use **Print Chassis Tickets** on a quotation or sales order classified as
**Retail / Détail**. The button is hidden for wholesale, unclassified and
cancelled orders, and printing is also restricted to retail on the server.
The report is not exposed in the generic Print menu.

Each chassis on a separate description line produces one 80 x 60 mm ticket.
Company, product, chassis in large text, order reference and date are printed.
Free text of at least 17 characters, including color, is printed in full. The automatic product
description is excluded. Physical product lines with positive quantities are
read even when the product is not selected for mandatory chassis validation; sections,
notes, services and down payments are skipped. Duplicate numbers in one line
print once. Quantities do not multiply tickets. Print at actual size; thermal
printer cutting depends on its driver. PDFs read the current description.

For an existing installation, upgrade this module before uninstalling
`sale_chassis_ticket` and removing its addon directory. The former module is no
longer needed. No sales descriptions are migrated or rewritten, and no existing
order is automatically classified as retail.

## Validation

```sh
docker compose exec -T web odoo -d sale_chassis_test_20261002 \
  -i sale_chassis_description --test-enable --test-tags /sale_chassis_description \
  --without-demo=all --stop-after-init --http-port=8096 --max-cron-threads=0
```

Use `-u sale_chassis_description` to repeat on this isolated test database.
Tests check classification, retail/wholesale, native description entry, invoice
posting, delivery/invoice/sales report HTML, permissions and server-side bypasses.

To also exercise the optional configuration integration on the test database:

```sh
docker compose exec -T web odoo -d sale_chassis_test_20261002 \
  -i bike_identity,delivery_vehicle_identity -u sale_chassis_description \
  --test-enable --test-tags /sale_chassis_description --without-demo=all \
  --stop-after-init --http-port=8096 --max-cron-threads=0
```

Validated on 2026-10-02: independent installation succeeded; 11 standalone
functional scenarios passed, then all 12 scenarios passed with both optional
identity addons installed. The integration check covers company defaults,
product-specific selection and delivery product selection.
