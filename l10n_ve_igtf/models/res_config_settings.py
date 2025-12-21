from odoo import api, fields, models


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

    l10n_ve_is_ve_country = fields.Boolean(
        compute="_compute_l10n_ve_is_ve_country",
        store=False,
    )

    @api.depends("company_id.account_fiscal_country_id")
    def _compute_l10n_ve_is_ve_country(self):
        for record in self:
            record.l10n_ve_is_ve_country = (
                record.company_id.account_fiscal_country_id
                and record.company_id.account_fiscal_country_id.code == "VE"
            )
