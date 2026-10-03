from odoo import models


class ChassisTicketReport(models.AbstractModel):
    _name = "report.sale_chassis_description.chassis_ticket"
    _description = "Sale Chassis Tickets"

    def _get_report_values(self, docids, data=None):
        orders = self.env["sale.order"].browse(docids).exists()
        return {
            "doc_ids": orders.ids,
            "doc_model": "sale.order",
            "docs": orders,
            "tickets": orders._chassis_ticket_rows(),
        }


class ChassisTicketLayout(models.Model):
    _inherit = "ir.actions.report"

    def _get_layout(self):
        if self.report_name == "sale_chassis_description.chassis_ticket":
            return self.env.ref("sale_chassis_description.ticket_minimal_layout")
        return super()._get_layout()
