from odoo import api, models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _sync_retail_chassis_description(self):
        for move in self:
            line = move.sale_line_id
            if (move.state not in ("done", "cancel")
                    and move.picking_type_id.code == "outgoing"
                    and line.order_id.chassis_sale_type == "retail"
                    and line.product_id == move.product_id
                    and line.product_id._retail_chassis_applies(move.company_id)
                    and move.description_picking != line.name):
                move.description_picking = line.name

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        moves._sync_retail_chassis_description()
        return moves


class StockRule(models.Model):
    _inherit = "stock.rule"

    def _get_stock_move_values(self, product_id, product_qty, product_uom, location_dest_id,
                               name, origin, company_id, values):
        result = super()._get_stock_move_values(
            product_id, product_qty, product_uom, location_dest_id, name, origin, company_id, values,
        )
        # Copy the full native description at creation. Native delivery reports,
        # serial/package sections and backorders already use description_picking.
        if self.picking_type_id.code == "outgoing" and values.get("sale_line_id"):
            line = self.env["sale.order.line"].browse(values["sale_line_id"])
            if line.product_id._retail_chassis_applies(line.company_id):
                result["description_picking"] = line.name
        return result
