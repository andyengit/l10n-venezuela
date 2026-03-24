from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    taxpayer_type = fields.Selection(
        related="company_id.taxpayer_type",
        readonly=False,
    )
    l10n_ve_on_behalf_of_third_party_enabled = fields.Boolean(
        related="company_id.l10n_ve_on_behalf_of_third_party_enabled",
        readonly=False,
    )

    exent_aliquot_sale = fields.Many2one(
        "account.tax", related="company_id.exent_aliquot_sale", readonly=False
    )
    general_aliquot_sale = fields.Many2one(
        "account.tax", related="company_id.general_aliquot_sale", readonly=False
    )
    reduced_aliquot_sale = fields.Many2one(
        "account.tax", related="company_id.reduced_aliquot_sale", readonly=False
    )
    extend_aliquot_sale = fields.Many2one(
        "account.tax", related="company_id.extend_aliquot_sale", readonly=False
    )

    exent_aliquot_purchase = fields.Many2one(
        "account.tax", related="company_id.exent_aliquot_purchase", readonly=False
    )
    general_aliquot_purchase = fields.Many2one(
        "account.tax", related="company_id.general_aliquot_purchase", readonly=False
    )
    reduced_aliquot_purchase = fields.Many2one(
        "account.tax", related="company_id.reduced_aliquot_purchase", readonly=False
    )
    extend_aliquot_purchase = fields.Many2one(
        "account.tax", related="company_id.extend_aliquot_purchase", readonly=False
    )
