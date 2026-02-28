# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Venezuela SENIAT - Stock/Inventory",
    "website": "https://github.com/OCA/l10n-venezuela",
    "icon": "/poweredbyandy_saas/static/description/icon.png",
    "countries": ["ve"],
    "author": "andyengit, Anderson Armeya, Odoo Community Association (OCA)",
    "maintainer": "andyengit",
    "category": "Inventory/Localizations",
    "depends": ["base", "web", "stock", "l10n_ve_seniat", "account"],
    "data": [
        "views/stock_picking_views.xml",
        "views/report_delivery_inherit.xml",
    ],
    "license": "AGPL-3",
    "auto_install": ["stock", "l10n_ve_seniat"],
    "installable": True,
}
