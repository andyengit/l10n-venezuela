{
    "name": "Autorización de Ventas a Crédito",
    "icon": "/poweredbyandy_saas/static/description/icon.png",
    "version": "18.0.1.0.0",
    "category": "Sales",
    "summary": "Control de autorización para confirmar ventas y facturas a crédito",
    "author": "andyengit",
    "maintainer": "andyengit",
    "website": "https://github.com/OCA/l10n-venezuela",
    "depends": ["sale", "account"],
    "data": [
        "security/security.xml",
        "views/sale_order_views.xml",
        "views/account_move_views.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
    "auto_install": False,
}
