from odoo import fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    l10n_ve_transfer_reason = fields.Text(
        string="Motivo del traslado",
        help="Motivo del traslado de los bienes muebles, según lo establecido "
        "en el Artículo 10, numeral 4, de la Providencia Administrativa "
        "del SENIAT.",
    )
