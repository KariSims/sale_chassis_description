{
    "name": "Retail Sale Chassis Description",
    "summary": "Retail/wholesale sales, chassis descriptions and 80 mm chassis tickets",
    "version": "18.0.1.2.1",
    "category": "Sales",
    "license": "LGPL-3",
    "depends": ["sale_stock"],
    "data": [
        "security/ir.model.access.csv",
        "views/settings_views.xml",
        "report/chassis_ticket.xml",
        "views/sale_views.xml",
        "views/invoice_views.xml",
        "views/delivery_views.xml",
        "wizard/confirmation_views.xml",
    ],
    "installable": True,
    "application": False,
}
