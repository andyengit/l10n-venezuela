# -*- coding: utf-8 -*-
{
    'name': 'Venezuela - Product Report',
    'version': '18.0.1.0.0',
    'category': 'Localization',
    'summary': 'Reportes de productos con listas de precios para Venezuela',
    'description': """
    Este módulo permite generar reportes PDF de productos incluyendo:
    - Nombre del producto
    - Coste del producto
    - Precios en diferentes listas de precios
    - Cantidad a mano
    """,
    'author': 'andyengit',
    'maintainer': 'andyengit',
    'website': '',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'product',
        'stock',
        'sale',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/product_report_wizard.xml',
        'views/product_views.xml',
        'reports/product_report.xml',
        'reports/product_report_template.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'l10n_ve_product_report/static/src/scss/product_report.scss',
        ],
    },
    'assets': {
        'web.assets_backend': [
            'l10n_ve_product_report/static/src/scss/product_report.scss',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
