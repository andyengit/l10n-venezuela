{
    "name": "Multicurrency",
    "version": "18.0.1.0.0",
    "category": "Extra Tools",
    "summary": "Multimoneda",
    "author": "Andyengit,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-venezuela",
    "depends": ["account"],
    "data": [
        "views/account_move_views.xml",
        "views/res_currency_views.xml"
    ],
    "license": "LGPL-3",
    "installable": True,
    "auto_install": False,
    "assets": {
        "web.assets_backend": [
            "currency_account/static/src/**/*",
        ],
    },
}
