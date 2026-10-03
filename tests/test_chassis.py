from lxml import etree

from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import Form, tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon

from ..models.description import extract_chassis_descriptions, has_chassis


@tagged("post_install", "-at_install")
class TestChassisDescription(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.bike = cls.env["product.product"].create({
            "name": "Test motorcycle", "type": "consu", "is_storable": True,
            "invoice_policy": "order", "list_price": 1200,
            "taxes_id": [Command.clear()],
            "property_account_income_id": cls.company_data["default_account_revenue"].id,
        })
        cls.env.company.sudo().write({
            "retail_chassis_enabled": True,
            "retail_chassis_product_tmpl_ids": [Command.set(cls.bike.product_tmpl_id.ids)],
        })
        cls.oil = cls.env["product.product"].create({
            "name": "Oil", "type": "consu",
            "list_price": 10, "taxes_id": [Command.clear()],
        })
        cls.warehouse = cls.env["stock.warehouse"].search([("company_id", "=", cls.env.company.id)], limit=1)
        cls.env["stock.quant"]._update_available_quantity(cls.bike, cls.warehouse.lot_stock_id, 20)
        cls.chassis = "DJHDGE73NSU73YGUDDUYEH"
        cls.salesperson = cls.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Chassis salesperson", "login": "chassis_description_sales",
            "company_id": cls.env.company.id, "company_ids": [Command.set(cls.env.company.ids)],
            "groups_id": [Command.set([cls.env.ref("sales_team.group_sale_salesman").id])],
        })

    def _sale(self, sale_type=False, description=None, product=None, quantity=1):
        product = product or self.bike
        values = {"product_id": product.id, "product_uom_qty": quantity}
        if description is not None:
            values["name"] = description
        return self.env["sale.order"].create({
            "partner_id": self.partner_a.id, "user_id": self.salesperson.id,
            "warehouse_id": self.warehouse.id, "chassis_sale_type": sale_type,
            "order_line": [Command.create(values)],
        })

    def _invoice(self, sale_type=False, description=None):
        return self.env["account.move"].create({
            "move_type": "out_invoice", "partner_id": self.partner_a.id,
            "chassis_sale_type": sale_type,
            "invoice_line_ids": [Command.create({
                "product_id": self.bike.id, "quantity": 1, "price_unit": 1200,
                "name": description or self.bike.display_name,
            })],
        })

    def _wizard(self, document):
        action = document.action_confirm() if document._name == "sale.order" else document.action_post()
        self.assertEqual(action["res_model"], "sale.chassis.confirmation")
        return self.env["sale.chassis.confirmation"].with_user(document.env.user).browse(action["res_id"])

    def _html(self, report, document):
        return self.env["ir.actions.report"]._render_qweb_html(report, document.ids)[0].decode()

    def test_retail_requires_chassis_not_product_default_or_notes(self):
        for description in (self.bike.display_name, self.bike.display_name + "\nShort note"):
            order = self._sale("retail", description)
            with self.assertRaises(ValidationError), self.cr.savepoint():
                order.action_confirm()
            self.assertEqual(order.state, "draft")
        self.bike.description_sale = "Chassis Number: CATALOG123"
        order = self._sale("retail")
        with self.assertRaises(ValidationError), self.cr.savepoint():
            order.action_confirm()

    def test_popup_saves_retail_choice_and_returns_to_native_description(self):
        order = self._sale().with_user(self.salesperson)
        wizard = self._wizard(order)
        self.assertFalse(wizard.sale_type)
        with Form(wizard) as form:
            form.sale_type = "retail"
        action = wizard.action_confirm()
        self.assertEqual(action["tag"], "display_notification")
        self.assertEqual(order.state, "draft")
        self.assertEqual(order.chassis_sale_type, "retail")
        self.assertEqual(order.order_line.name, self.bike.display_name)
        order.order_line.name += "\n" + self.chassis
        order.action_confirm()
        self.assertEqual(order.state, "sale")

    def test_wholesale_popup_confirms_without_chassis(self):
        order = self._sale().with_user(self.salesperson)
        wizard = self._wizard(order)
        wizard.sale_type = "wholesale"
        wizard.action_confirm()
        self.assertEqual(order.state, "sale")
        self.assertEqual(order.order_line.name, self.bike.display_name)

    def test_native_description_reaches_invoice_and_open_completed_delivery(self):
        description = self.bike.display_name + "\n" + self.chassis + "\nCustomer note"
        order = self._sale("retail", description)
        order.action_confirm()
        picking = order.picking_ids.filtered(lambda p: p.picking_type_id.code == "outgoing")
        self.assertEqual(picking.move_ids.description_picking, description)
        self.assertIn(self.chassis, self._html("stock.report_deliveryslip", picking))
        picking.button_validate()
        self.assertEqual(picking.state, "done")
        html = self._html("stock.report_deliveryslip", picking)
        cells = etree.HTML(html).xpath("//tbody/tr/td[1][contains(., $chassis)]", chassis=self.chassis)
        self.assertTrue(cells)
        self.assertIn("Customer note", "".join(cells[0].itertext()))
        invoice = order._create_invoices()
        self.assertEqual(invoice.chassis_sale_type, "retail")
        self.assertIn(description, invoice.invoice_line_ids.name)
        invoice.action_post()
        self.assertEqual(invoice.state, "posted")
        self.assertIn(self.chassis, self._html("account.report_invoice", invoice))
        self.assertIn(self.chassis, self._html("sale.report_saleorder", order))

    def test_manual_invoice_retail_and_wholesale(self):
        invoice = self._invoice()
        wizard = self._wizard(invoice)
        wizard.sale_type = "retail"
        result = wizard.action_confirm()
        self.assertEqual(result["tag"], "display_notification")
        self.assertEqual(invoice.state, "draft")
        with self.assertRaises(ValidationError), self.cr.savepoint():
            invoice._post()
        invoice.invoice_line_ids.name += "\nChassis Number: " + self.chassis
        invoice.action_post()
        self.assertEqual(invoice.state, "posted")
        wholesale = self._invoice("wholesale")
        wholesale.action_post()
        self.assertEqual(wholesale.state, "posted")

    def test_rpc_cannot_skip_classification_or_remove_confirmed_chassis(self):
        order = self._sale()
        with self.assertRaises(ValidationError), self.cr.savepoint():
            order.write({"state": "sale"})
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.env["sale.order"].create({
                "partner_id": self.partner_a.id, "state": "sale", "chassis_sale_type": "retail",
                "order_line": [Command.create({"product_id": self.bike.id, "product_uom_qty": 1})],
            })
        order.chassis_sale_type = "retail"
        order.order_line.name += "\n" + self.chassis
        order.action_confirm()
        with self.assertRaises(ValidationError), self.cr.savepoint():
            order.order_line.name = self.bike.display_name
        with self.assertRaises(ValidationError), self.cr.savepoint():
            order.chassis_sale_type = "wholesale"
        invoice = self._invoice()
        with self.assertRaises(ValidationError), self.cr.savepoint():
            invoice._post()
        with self.assertRaises(ValidationError), self.cr.savepoint():
            invoice.write({"state": "posted"})

    def test_other_products_sections_downpayments_and_duplicate_quotation(self):
        order = self._sale(product=self.oil)
        self.assertFalse(self.oil._retail_chassis_applies(self.env.company))
        result = order.action_confirm()
        self.assertEqual(order.state, "sale", (order.order_line.product_id.display_name, result))
        identified = self._sale("retail", self.bike.display_name + "\n" + self.chassis)
        identified.order_line = [Command.create({"display_type": "line_note", "name": "Note"})]
        identified.action_confirm()
        duplicate = identified.copy()
        self.assertFalse(duplicate.chassis_sale_type)
        self.assertEqual(duplicate.state, "draft")
        downpayment = self._sale("retail")
        downpayment.order_line.is_downpayment = True
        downpayment.action_confirm()
        self.assertEqual(downpayment.state, "sale")

    def test_partial_delivery_keeps_native_description_on_backorder(self):
        description = self.bike.display_name + "\n" + self.chassis + "\nABC456"
        order = self._sale("retail", description, quantity=2)
        order.action_confirm()
        picking = order.picking_ids
        picking.move_ids.quantity = 1
        result = picking.button_validate()
        if isinstance(result, dict) and result.get("res_model") == "stock.backorder.confirmation":
            self.env["stock.backorder.confirmation"].with_context(result["context"]).create({}).process()
        self.assertEqual(picking.state, "done")
        self.assertEqual(picking.backorder_ids.move_ids.description_picking, description)
        self.assertIn(self.chassis, self._html("stock.report_deliveryslip", picking.backorder_ids))

    def test_cannot_group_retail_and_wholesale_invoices(self):
        retail = self._sale("retail", self.bike.display_name + "\n" + self.chassis)
        wholesale = self._sale("wholesale")
        (retail | wholesale).action_confirm()
        invoices = (retail | wholesale)._create_invoices()
        self.assertEqual(len(invoices), 2)
        self.assertEqual(set(invoices.mapped("chassis_sale_type")), {"retail", "wholesale"})

    def test_classification_popup_does_not_bypass_document_access(self):
        order = self._sale()
        other_user = self.salesperson.copy({"name": "Other salesperson", "login": "chassis_other_sales"})
        forged = self.env["sale.chassis.confirmation"].with_user(other_user).create({
            "sale_order_id": order.id, "sale_type": "wholesale",
        })
        with self.assertRaises(AccessError), self.cr.savepoint():
            forged.action_confirm()
        self.assertEqual(order.state, "draft")

    def test_chassis_free_text_and_existing_layout(self):
        self.assertTrue(has_chassis("Test motorcycle\n" + self.chassis, "Test motorcycle"))
        for text in (
            "1GDHK33U25F914022", "1GDHK33U25F914022 Yellow",
            "1GDHK33U25F914022 (YELLOW)", "1GDHK33U25F914022 - Yellow",
        ):
            self.assertTrue(has_chassis("Test motorcycle\n" + text, "Test motorcycle"))
            self.assertEqual(extract_chassis_descriptions("Test motorcycle\nChâssis: " + text, "Test motorcycle"), [text])
        self.assertFalse(has_chassis("Test motorcycle\n1234567890123456", "Test motorcycle"))
        self.assertFalse(has_chassis("Test motorcycle\nChassis Number:   ", "Test motorcycle"))
        self.assertFalse(has_chassis("Test motorcycle\n", "Test motorcycle"))

    def test_company_product_configuration(self):
        self.assertTrue(self.bike._retail_chassis_applies(self.env.company))
        self.assertFalse(self.oil._retail_chassis_applies(self.env.company))
        self.env.company.sudo().write({"retail_chassis_enabled": False})
        self.assertFalse(self.bike._retail_chassis_applies(self.env.company))
        self.env.company.sudo().write({
            "retail_chassis_enabled": True,
            "retail_chassis_product_tmpl_ids": [Command.set(self.oil.product_tmpl_id.ids)],
        })
        self.assertFalse(self.bike._retail_chassis_applies(self.env.company))
        self.assertTrue(self.oil._retail_chassis_applies(self.env.company))
