from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    standard_price = fields.Float(tracking=True)
