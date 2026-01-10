# -*- coding: utf-8 -*-
from odoo import models, api


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def action_open_product_report_wizard(self):
        """Abrir wizard para configurar el reporte de productos"""
        return {
            'name': 'Configurar Reporte de Productos',
            'type': 'ir.actions.act_window',
            'res_model': 'product.report.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }
