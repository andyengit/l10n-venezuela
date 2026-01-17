# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Venezuela SENIAT - Sale",
    "website": "https://github.com/OCA/l10n-venezuela",
    "icon": "/sale/static/description/icon.png",
    "countries": ["ve"],
    "author": "Anderson Armeya, Odoo Community Association (OCA)",
    "category": "Sales/Localizations",
    "depends": ["base", "web", "sale", "l10n_ve_seniat", "account"],
    "data": [
        "views/report_sale_inherit.xml",
        "views/sale_order_views.xml",
    ],
    "license": "AGPL-3",
    "auto_install": ["account", "sale", "l10n_ve_seniat"],
    "installable": True,
}
