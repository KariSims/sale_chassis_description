from odoo import _, models
from odoo.exceptions import UserError
from .description import extract_chassis_descriptions


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _chassis_ticket_rows(self):
        self.check_access("read")
        rows = []
        for order in self:
            if order.chassis_sale_type != "retail":
                raise UserError(_("Chassis tickets are available only for retail sales. Choose Retail on the quotation."))
            if order.state == "cancel":
                raise UserError(_("Return the cancelled order to a quotation before printing chassis tickets."))
            order_rows = []
            # Printing existing chassis must also work on historical sales and
            # products not enabled for mandatory retail chassis validation.
            lines = order.order_line.filtered(
                lambda line: not line.display_type and not line.is_downpayment
                and line.product_id and line.product_id.type != "service"
                and line.product_uom_qty > 0
            )
            for line in lines:
                seen = set()
                for chassis in extract_chassis_descriptions(
                    line.name, line._get_sale_order_line_multiline_description_sale(),
                ):
                    if chassis in seen:
                        continue
                    seen.add(chassis)
                    order_rows.append({"order": order, "line": line, "chassis": chassis})
            if not order_rows:
                raise UserError(_(
                    "%s: no chassis description of at least 17 characters found. Enter it below the product "
                    "(for example, 1GDHK33U25F914022 - Yellow).", order.name,
                ))
            rows.extend(order_rows)
        return rows

    def action_print_chassis_tickets(self):
        self._chassis_ticket_rows()
        return self.env.ref("sale_chassis_description.action_chassis_ticket").report_action(self, config=False)
