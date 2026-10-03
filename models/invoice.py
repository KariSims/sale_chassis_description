from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .description import SALE_TYPES, validate_descriptions


class AccountMove(models.Model):
    _inherit = "account.move"

    chassis_sale_type = fields.Selection(SALE_TYPES, string="Sale Type", copy=True, tracking=True)

    def _chassis_lines(self):
        self.ensure_one()
        if self.move_type != "out_invoice":
            return self.env["account.move.line"]
        return self.invoice_line_ids.filtered(
            lambda line: line.display_type == "product" and line.quantity > 0
            and not line.is_downpayment and line.product_id
            and line.product_id._retail_chassis_applies(self.company_id)
        )

    def _check_chassis_description(self):
        for invoice in self:
            validate_descriptions(invoice._chassis_lines(), invoice.chassis_sale_type,
                                  lambda line: line.product_id.with_context(lang=invoice.partner_id.lang).get_product_multiline_description_sale())

    def action_post(self):
        pending = self.filtered(lambda invoice: invoice._chassis_lines() and not invoice.chassis_sale_type)
        if pending:
            if len(self) != 1:
                raise ValidationError(_("Choose Retail or Wholesale on each invoice before batch posting."))
            return self.env["sale.chassis.confirmation"]._open_for_document(self)
        return super().action_post()

    def _post(self, soft=True):
        self.filtered(lambda invoice: invoice.state == "draft")._check_chassis_description()
        return super()._post(soft=soft)

    @api.model_create_multi
    def create(self, vals_list):
        invoices = super().create(vals_list)
        invoices.filtered(lambda invoice: invoice.state == "posted")._check_chassis_description()
        return invoices

    def write(self, values):
        if "chassis_sale_type" in values and any(
            invoice.state == "posted" and invoice.chassis_sale_type != values["chassis_sale_type"] for invoice in self
        ):
            raise ValidationError(_("Reset the invoice to draft before changing its sale type."))
        result = super().write(values)
        if values.get("state") == "posted":
            self.filtered(lambda invoice: invoice.state == "posted")._check_chassis_description()
        elif {"chassis_sale_type", "invoice_line_ids", "company_id"} & values.keys():
            self.filtered(lambda invoice: invoice.state == "posted" and invoice.chassis_sale_type)._check_chassis_description()
        return result


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.constrains("name", "product_id", "quantity", "display_type", "is_downpayment", "move_id")
    def _check_retail_chassis(self):
        self.move_id.filtered(lambda invoice: invoice.state == "posted" and invoice.chassis_sale_type)._check_chassis_description()
