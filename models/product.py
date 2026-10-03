from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    retail_chassis_required = fields.Boolean(
        string="Legacy retail chassis selection", readonly=True, copy=False,
        help="Historical product selection kept for upgrade compatibility. Configure chassis requirements in Sales settings.",
    )


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _retail_chassis_applies(self, company):
        self.ensure_one()
        company = company.sudo()
        return bool(
            self.type != "service" and company.retail_chassis_enabled
            and self.product_tmpl_id in company.retail_chassis_product_tmpl_ids
        )
