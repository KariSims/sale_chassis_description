from odoo import api, Command, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    templates = env["product.template"].with_context(active_test=False).search([
        ("retail_chassis_required", "=", True), ("type", "!=", "service"),
    ])
    for company in env["res.company"].search([]):
        selected = templates.filtered(lambda product: not product.company_id or product.company_id == company)
        # Seed legacy optional-addon configuration once. The new settings are
        # authoritative afterwards; deselected products stay deselected.
        if "bike.identity.settings" in env:
            settings = env["bike.identity.settings"].search([
                ("company_id", "=", company.id), ("enabled", "=", True),
            ])
            selected |= settings.product_ids.product_tmpl_id
            if settings and "bike.identity.product.settings" in env:
                selected |= env["bike.identity.product.settings"].search([
                    ("company_id", "=", company.id), ("enabled", "=", True),
                ]).product_tmpl_id
        if "delivery_vin_enabled" in company._fields and company.delivery_vin_enabled:
            selected |= company.delivery_vin_product_ids.product_tmpl_id
        selected = selected.filtered(
            lambda product: product.type != "service" and (not product.company_id or product.company_id == company)
        )
        if selected:
            company.write({
                "retail_chassis_enabled": True,
                "retail_chassis_product_tmpl_ids": [Command.set(selected.ids)],
            })
