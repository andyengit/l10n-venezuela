from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_ve_payroll_alicuota_util = fields.Float(
        string="Alícuota Utilidades (%)",
        config_parameter="l10n_ve_payroll.alicuota_util",
        default=8.33,
        help="Porcentaje de utilidades sobre salario base (LOTTT)",
    )
    l10n_ve_payroll_alicuota_bv = fields.Float(
        string="Alícuota Bono Vacacional (%)",
        config_parameter="l10n_ve_payroll.alicuota_bv",
        default=4.16,
        help="Porcentaje de bono vacacional sobre salario base (LOTTT)",
    )
    l10n_ve_payroll_faov_empleador = fields.Float(
        string="FAOV Empleador (%)",
        config_parameter="l10n_ve_payroll.faov_empleador",
        default=2.0,
        help="Aporte patronal al FAOV sobre salario integral",
    )
    l10n_ve_payroll_faov_trabajador = fields.Float(
        string="FAOV Trabajador (%)",
        config_parameter="l10n_ve_payroll.faov_trabajador",
        default=1.0,
        help="Aporte del trabajador al FAOV sobre salario integral",
    )
