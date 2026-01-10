# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class ProductReportWizard(models.TransientModel):
    _name = 'product.report.wizard'
    _description = 'Wizard para configuración del reporte de productos'

    pricelist_ids = fields.Many2many(
        'product.pricelist',
        string='Listas de Precios',
        help='Seleccione las listas de precios que desea incluir en el reporte'
    )

    product_ids = fields.Many2many(
        'product.product',
        string='Productos',
        help='Seleccione los productos que desea incluir en el reporte. Si no selecciona ninguno, se incluirán todos los productos activos.',
        domain=[('active', '=', True)],
        default=lambda self: self._default_product_ids()
    )

    def _default_product_ids(self):
        """Obtener productos seleccionados del contexto"""
        active_ids = self.env.context.get('active_ids', [])
        if active_ids:
            return self.env['product.product'].browse(active_ids)
        return self.env['product.product']

    def action_generate_report(self):
        """Generar el reporte PDF con los productos y sus precios"""
        if not self.pricelist_ids:
            raise UserError('Debe seleccionar al menos una lista de precios.')

        # Obtener productos - usar seleccionados o todos los activos
        if self.product_ids:
            products = self.product_ids
        else:
            products = self.env['product.product'].search([('active', '=', True)])

        if not products:
            raise UserError('No se encontraron productos para incluir en el reporte.')

        # Usar método personalizado para generar el reporte
        return self.generate_product_report(products)

    def generate_product_report(self, products):
        """Generar el reporte PDF usando el sistema estándar de reportes"""
        # Preparar datos asegurándonos de que sean objetos recordset
        pricelist_data = self.pricelist_ids  # Ya es un recordset
        product_data = products  # Ya es un recordset

        # Usar el sistema estándar de reportes con contexto personalizado
        # Pasar los IDs en lugar de los objetos para evitar problemas de serialización
        return self.env.ref('l10n_ve_product_report.action_product_report').with_context(
            pricelist_ids=self.pricelist_ids.ids,  # Pasar IDs
            product_ids=products.ids,  # Pasar IDs
            active_model='product.report.wizard',
            active_id=self.id
        ).report_action(self)
