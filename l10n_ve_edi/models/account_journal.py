from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    l10n_ve_edi_provider = fields.Selection(
        selection=[("none", "Ninguno")],
        string="Proveedor de facturacion digital",
        default="none",
        help="Imprenta o conector para enviar facturas de cliente confirmadas de este diario.",
    )
