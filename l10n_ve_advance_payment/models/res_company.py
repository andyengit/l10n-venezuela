from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_ve_advance_liability_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Advance Liability Account",
        check_company=True,
        domain="[('account_type', 'in', ('liability_current', 'liability_non_current')), ('deprecated', '=', False)]",
    )
