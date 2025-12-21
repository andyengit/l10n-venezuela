from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_ve_igtf_account_id = fields.Many2one(
        related="company_id.l10n_ve_igtf_account_id",
        readonly=False,
    )
    l10n_ve_igtf_percent = fields.Float(
        related="company_id.l10n_ve_igtf_percent",
        readonly=False,
    )

    l10n_ve_igtf_currency_ids = fields.Many2many(
        related="company_id.l10n_ve_igtf_currency_ids",
        readonly=False,
    )
