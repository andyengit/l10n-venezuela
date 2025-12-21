# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Venezuela SENIAT - Stock/Inventory",
    "website": "https://github.com/OCA/l10n-venezuela",
    "icon": "/stock/static/description/icon.png",
    "countries": ["ve"],
    "author": "Anderson Armeya, Odoo Community Association (OCA)",
    "category": "Inventory/Localizations",
    "depends": ["base", "web", "stock", "l10n_ve_seniat", "account"],
    "data": [
        "views/report_delivery_inherit.xml",
    ],
    "license": "AGPL-3",
    "auto_install": ["account", "stock", "l10n_ve_seniat"],
    "installable": True,
}
