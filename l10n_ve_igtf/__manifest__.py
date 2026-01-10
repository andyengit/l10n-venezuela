{
    "name": "Venezuela IGTF",
    "website": "https://github.com/OCA/l10n-venezuela",
    "icon": "/account/static/description/l10n.png",
    "countries": ["ve"],
    "author": "Odoo Community Association (OCA)",
    "category": "Accounting/Localizations",
    "depends": ["web", "account", "l10n_ve_seniat"],
    "data": [
        "security/ir.model.access.csv",
        "views/account_payment_views.xml",
        "views/account_payment_register_views.xml",
        "views/res_config_settings.xml",
        "wizard/unreconcile_igtf_payment_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "l10n_ve_igtf/static/src/components/account_payment_field/account_payment.xml",
            "l10n_ve_igtf/static/src/components/account_payment_field/account_payment_field_patch.js",
        ],
    },
    "license": "AGPL-3",
}
