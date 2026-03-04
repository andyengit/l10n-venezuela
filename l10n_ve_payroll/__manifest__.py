{
    "name": "Venezuela - Nómina",
    "summary": "Requisitos legales de nómina para Venezuela (LOTTT)",
    "license": "LGPL-3",
    "version": "18.0.1.0.0",
    "author": "andyengit",
    "maintainer": "andyengit",
    "website": "https://github.com/OCA/l10n-venezuela",
    "category": "Human Resources/Payroll",
    "depends": [
        "payroll",
        "l10n_ve_seniat",
    ],
    "countries": ["ve"],
    "data": [
        "data/hr_salary_rule_category_data.xml",
        "data/hr_contribution_register_data.xml",
        "data/hr_salary_rule_data.xml",
        "data/hr_payroll_structure_data.xml",
        "views/res_config_settings_views.xml",
        "views/menus.xml",
    ],
    "application": False,
}
