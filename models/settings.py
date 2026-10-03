from odoo import _, api, Command, fields, models
from odoo.exceptions import AccessError, ValidationError


class ResCompany(models.Model):
    _inherit = "res.company"

    retail_chassis_enabled = fields.Boolean(string="Require chassis for retail sales")
    retail_chassis_product_tmpl_ids = fields.Many2many(
        "product.template", "retail_chassis_company_template_rel", "company_id", "product_tmpl_id",
        string="Products requiring chassis", check_company=True,
        help="All variants of these products require a chassis in their retail sales and invoice descriptions.",
    )

    def _check_retail_chassis_config_access(self, values):
        if {"retail_chassis_enabled", "retail_chassis_product_tmpl_ids"} & values.keys():
            if not self.env.su and not self.env.user.has_group("base.group_system"):
                raise AccessError(_("Only Settings administrators can configure retail chassis requirements."))

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            self._check_retail_chassis_config_access(values)
        return super().create(vals_list)

    def write(self, values):
        self._check_retail_chassis_config_access(values)
        return super().write(values)

    @api.constrains("retail_chassis_enabled", "retail_chassis_product_tmpl_ids")
    def _check_retail_chassis_config(self):
        for company in self:
            products = company.retail_chassis_product_tmpl_ids
            if company.retail_chassis_enabled and not products:
                raise ValidationError(_("Select the products requiring chassis before enabling the requirement."))
            if any(product.type == "service" for product in products):
                raise ValidationError(_("Chassis requirements apply to physical products, not services."))
            if any(product.company_id and product.company_id != company for product in products):
                raise ValidationError(_("Selected products must be shared or belong to this company."))


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # Stage both values so activation and product selection are saved together.
    retail_chassis_enabled = fields.Boolean(
        string="Require chassis for retail sales", compute="_compute_retail_chassis_settings",
        store=True, readonly=False,
    )
    retail_chassis_product_tmpl_ids = fields.Many2many(
        "product.template", string="Products requiring chassis",
        compute="_compute_retail_chassis_settings", store=True, readonly=False,
    )

    @api.depends("company_id")
    def _compute_retail_chassis_settings(self):
        for settings in self:
            settings.retail_chassis_enabled = settings.company_id.retail_chassis_enabled
            settings.retail_chassis_product_tmpl_ids = settings.company_id.retail_chassis_product_tmpl_ids

    def set_values(self):
        self.ensure_one()
        result = super().set_values()
        self.company_id.write({
            "retail_chassis_enabled": self.retail_chassis_enabled,
            "retail_chassis_product_tmpl_ids": [Command.set(self.retail_chassis_product_tmpl_ids.ids)],
        })
        return result
