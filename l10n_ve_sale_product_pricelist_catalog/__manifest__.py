{
    "name": "Product Pricelist in Catalog",
    "icon": "/poweredbyandy_saas/static/description/icon.png",
    "version": "18.0.1.0.0",
    "category": "Sales",
    "sequence": 10,
    "summary": "Muestra las listas de precios y sus precios en el catálogo de productos",
    "author": "Andyengit,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-venezuela",
    "license": "LGPL-3",
    "images": [],
    "depends": [
        "sale",
        "product",
    ],
    "data": [
        "views/product_catalog_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "l10n_ve_sale_product_pricelist_catalog/static/src/js/product_catalog_pricelist.esm.js",
            "l10n_ve_sale_product_pricelist_catalog/static/src/xml/product_catalog_pricelist.xml",
        ],
    },
    "demo": [],
    "installable": True,
    "auto_install": False,
    "application": False,
}
