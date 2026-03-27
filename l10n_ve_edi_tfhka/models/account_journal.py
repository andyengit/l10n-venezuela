from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    l10n_ve_edi_provider = fields.Selection(
        selection_add=[("tfhka", "The Factory HKA")],
    )
