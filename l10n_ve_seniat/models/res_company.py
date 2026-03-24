from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    taxpayer_type = fields.Selection(
        related="partner_id.taxpayer_type",
        readonly=False,
    )
    l10n_ve_on_behalf_of_third_party_enabled = fields.Boolean(
        string="Facturación por cuenta de terceros habilitada",
        default=False,
    )

    exent_aliquot_sale = fields.Many2one(
        "account.tax", domain=[("type_tax_use", "=", "sale")]
    )
    general_aliquot_sale = fields.Many2one(
        "account.tax", domain=[("type_tax_use", "=", "sale")]
    )
    reduced_aliquot_sale = fields.Many2one(
        "account.tax", domain=[("type_tax_use", "=", "sale")]
    )
    extend_aliquot_sale = fields.Many2one(
        "account.tax", domain=[("type_tax_use", "=", "sale")]
    )

    exent_aliquot_purchase = fields.Many2one(
        "account.tax", domain=[("type_tax_use", "=", "purchase")]
    )
    general_aliquot_purchase = fields.Many2one(
        "account.tax", domain=[("type_tax_use", "=", "purchase")]
    )
    reduced_aliquot_purchase = fields.Many2one(
        "account.tax", domain=[("type_tax_use", "=", "purchase")]
    )
    extend_aliquot_purchase = fields.Many2one(
        "account.tax", domain=[("type_tax_use", "=", "purchase")]
    )
