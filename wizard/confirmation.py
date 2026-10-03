from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from ..models.description import SALE_TYPES


class ChassisConfirmation(models.TransientModel):
    _name = "sale.chassis.confirmation"
    _description = "Retail / Wholesale Confirmation"

    sale_order_id = fields.Many2one("sale.order", readonly=True)
    invoice_id = fields.Many2one("account.move", readonly=True)
    sale_type = fields.Selection(SALE_TYPES, string="Sale Type")

    @api.model
    def _open_for_document(self, document):
        document.ensure_one()
        document.check_access("write")
        is_sale = document._name == "sale.order"
        wizard = self.create({
            "sale_order_id" if is_sale else "invoice_id": document.id,
            "sale_type": document.chassis_sale_type,
        })
        return {
            "type": "ir.actions.act_window", "name": _("Retail or Wholesale?"),
            "res_model": self._name, "res_id": wizard.id, "view_mode": "form", "target": "new",
        }

    def action_confirm(self):
        self.ensure_one()
        self.check_access("write")
        if bool(self.sale_order_id) == bool(self.invoice_id):
            raise ValidationError(_("Select one quotation or customer invoice."))
        is_sale = bool(self.sale_order_id)
        document = self.sale_order_id or self.invoice_id
        document.check_access("write")
        if document.state not in (("draft", "sent") if is_sale else ("draft",)):
            raise ValidationError(_("This document is no longer a draft. Close this window."))
        if not self.sale_type:
            raise ValidationError(_("Choose Retail or Wholesale."))
        document.chassis_sale_type = self.sale_type
        try:
            document._check_chassis_description()
        except ValidationError as error:
            # Keep the choice, close the popup and return to the native line
            # description. The document stays draft until its checks pass.
            return {
                "type": "ir.actions.client", "tag": "display_notification",
                "params": {"title": _("Chassis number required"), "message": str(error),
                           "type": "warning", "sticky": True,
                           "next": {"type": "ir.actions.act_window_close"}},
            }
        result = document.action_confirm() if is_sale else document.action_post()
        return result if isinstance(result, dict) else {"type": "ir.actions.act_window_close"}
