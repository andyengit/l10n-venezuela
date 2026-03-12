from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_ve_advance_liability_account_id = fields.Many2one(
        related="company_id.l10n_ve_advance_liability_account_id",
        readonly=False,
    )
    l10n_ve_is_ve_country = fields.Boolean(
        compute="_compute_l10n_ve_is_ve_country",
    )

    @api.depends("company_id.account_fiscal_country_id")
    def _compute_l10n_ve_is_ve_country(self):
        for rec in self:
            rec.l10n_ve_is_ve_country = rec.company_id.account_fiscal_country_id.code == "VE"

    @api.constrains("l10n_ve_advance_liability_account_id")
    def _check_l10n_ve_advance_liability_account_id(self):
        for rec in self:
            account = rec.l10n_ve_advance_liability_account_id
            if not account:
                continue
            if account.account_type not in ("liability_current", "liability_non_current"):
                raise ValidationError("La cuenta de anticipos debe ser de pasivo.")
            if not account.reconcile:
                raise ValidationError("La cuenta de anticipos debe permitir conciliacion.")
