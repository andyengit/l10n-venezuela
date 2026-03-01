from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    l10n_ve_is_ve_country = fields.Boolean(
        compute="_compute_l10n_ve_is_ve_country",
    )
    l10n_ve_transfer_reason = fields.Text(
        string="Motivo del traslado",
        help="Motivo del traslado de los bienes muebles, según lo establecido "
        "en el Artículo 10, numeral 4, de la Providencia Administrativa "
        "del SENIAT.",
    )

    @api.depends("company_id.account_fiscal_country_id")
    def _compute_l10n_ve_is_ve_country(self):
        for record in self:
            record.l10n_ve_is_ve_country = (
                record.company_id.account_fiscal_country_id
                and record.company_id.account_fiscal_country_id.code == "VE"
            )
