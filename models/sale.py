from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo import _

from .description import SALE_TYPES, validate_descriptions


class SaleOrder(models.Model):
    _inherit = "sale.order"

    chassis_sale_type = fields.Selection(SALE_TYPES, string="Sale Type", copy=False, tracking=True)

    def _chassis_lines(self):
        self.ensure_one()
        return self.order_line.filtered(
            lambda line: not line.display_type and not line.is_downpayment
            and line.product_uom_qty > 0 and line.product_id
            and line.product_id._retail_chassis_applies(self.company_id)
        )

    def _check_chassis_description(self):
        for order in self:
            validate_descriptions(order._chassis_lines(), order.chassis_sale_type,
                                  lambda line: line._get_sale_order_line_multiline_description_sale())

    def action_confirm(self):
        pending = self.filtered(lambda order: order._chassis_lines() and not order.chassis_sale_type)
        if pending:
            if len(self) != 1:
                raise ValidationError(_("Choose Retail or Wholesale on each quotation before batch confirmation."))
            return self.env["sale.chassis.confirmation"]._open_for_document(self)
        self._check_chassis_description()
        return super().action_confirm()

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        orders.filtered(lambda order: order.state == "sale")._check_chassis_description()
        return orders

    def write(self, values):
        reset_type = self.browse()
        if values.get("state") == "cancel":
            reset_type = self
        elif values.get("state") == "draft":
            # Also cover orders cancelled before this reset was introduced.
            reset_type = self.filtered(lambda order: order.state == "cancel")
        if "chassis_sale_type" in values and any(
            order.state == "sale" and order.chassis_sale_type != values["chassis_sale_type"] for order in self
        ):
            raise ValidationError(_("Cancel the order before changing its sale type."))
        result = super().write(values)
        # Clear the choice only after the state transition succeeds. Keep the
        # native descriptions and a retail choice saved after missing chassis.
        reset_type = reset_type.filtered("chassis_sale_type")
        if reset_type:
            reset_type.write({"chassis_sale_type": False})
        if values.get("state") == "sale" or {"chassis_sale_type", "order_line", "company_id"} & values.keys():
            self.filtered(lambda order: order.state == "sale")._check_chassis_description()
        return result

    def _prepare_invoice(self):
        values = super()._prepare_invoice()
        values["chassis_sale_type"] = self.chassis_sale_type
        return values

    def _get_invoice_grouping_keys(self):
        return super()._get_invoice_grouping_keys() + ["chassis_sale_type"]


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def write(self, values):
        result = super().write(values)
        if "name" in values:
            # The sale line edit is authorized; propagate its description to
            # the linked open deliveries even for users without Stock access.
            self.sudo().move_ids._sync_retail_chassis_description()
        return result

    @api.constrains("name", "product_id", "product_uom_qty", "display_type", "is_downpayment", "order_id")
    def _check_retail_chassis(self):
        # Existing confirmed documents without a classification are not backfilled.
        self.order_id.filtered(lambda order: order.state == "sale" and order.chassis_sale_type)._check_chassis_description()
