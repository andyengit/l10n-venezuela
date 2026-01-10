# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class ProductReportController(http.Controller):

    @http.route('/product_report/download/<int:wizard_id>', type='http', auth='user')
    def download_product_report(self, wizard_id):
        """Descargar el reporte de productos en PDF"""
        wizard = request.env['product.report.wizard'].browse(wizard_id)
        if not wizard.exists():
            return request.not_found()

        # Generar el reporte usando el wizard
        report_action = wizard.action_generate_report()
        return request.env['ir.actions.report']._get_report_from_name(
            report_action['report_name']
        )._render_qweb_pdf(report_action['data'])[0]
