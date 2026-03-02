# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Venezuela SENIAT - Sale",
    "website": "https://github.com/OCA/l10n-venezuela",
    "icon": "/poweredbyandy_saas/static/description/icon.png",
    "countries": ["ve"],
    "author": "Anderson Armeya, andyengit, Odoo Community Association (OCA)",
    "maintainers": ["andyengit"],
    "category": "Sales/Localizations",
    "depends": ["base", "web", "sale", "l10n_ve_seniat", "account", "announcement"],
    "data": [
        "data/sale_order_announcement_actions.xml",
        "data/ir_cron_data.xml",
        "views/report_sale_inherit.xml",
        "views/sale_order_views.xml",
    ],
    "license": "AGPL-3",
    "auto_install": ["sale", "l10n_ve_seniat"],
    "installable": True,
}
