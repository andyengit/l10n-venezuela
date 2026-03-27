{
    "name": "Venezuela EDI Facturacion Digital",
    "summary": "Base para facturacion digital Venezuela (validaciones, payload y flujo)",
    "version": "18.0.1.0.0",
    "category": "Accounting/Localizations",
    "author": "andyengit",
    "maintainer": "andyengit",
    "website": "https://github.com/OCA/l10n-venezuela",
    "license": "LGPL-3",
    "depends": ["l10n_ve_seniat", "l10n_ve_withholding", "l10n_ve_igtf", "queue_job"],
    "data": [
        "views/account_journal_views.xml",
        "views/account_move_views.xml",
    ],
    "installable": True,
    "application": False,
}
