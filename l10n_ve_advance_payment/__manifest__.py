{
    "name": "Venezuela Advance Payment",
    "version": "18.0.1.0.0",
    "website": "https://github.com/OCA/l10n-venezuela",
    "countries": ["ve"],
    "author": "andyengit",
    "maintainer": "andyengit",
    "category": "Accounting/Localizations",
    "depends": ["account", "l10n_ve_seniat"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_config_settings_views.xml",
        "views/account_move_views.xml",
        "views/account_payment_register_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "l10n_ve_advance_payment/static/src/components/advance_payment_field/advance_payment_field.xml",
            "l10n_ve_advance_payment/static/src/components/advance_payment_field/advance_payment_field.js",
        ],
    },
    "license": "AGPL-3",
}
