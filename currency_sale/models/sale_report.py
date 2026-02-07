from lxml import etree

from odoo import models, api


class SaleReport(models.Model):
    _inherit = "sale.report"

    def _select_additional_fields(self):
        res = super()._select_additional_fields()
        amount_fields = self.env['ir.model.fields'].sudo().search([
            ('model', '=', 'sale.order.line'),
            ('name', 'like', 'x_amount_currency_%'),
        ])
        for af in amount_fields:
            currency_id = af.name.replace('x_amount_currency_', '')
            res[af.name] = (
                f"CASE WHEN l.product_id IS NOT NULL"
                f" THEN SUM(l.{af.name}) ELSE 0 END"
            )
            res[f'x_currency_id_{currency_id}'] = currency_id
        return res

    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type in ('list', 'pivot'):
            self._inject_currency_fields_to_view(arch, 'price_total')
        return arch, view

    def _inject_currency_fields_to_view(self, arch, after_fields):
        amount_fields = self.env['ir.model.fields'].sudo().search([
            ('model', '=', self._name),
            ('name', 'like', 'x_amount_currency_%'),
        ])
        if not amount_fields:
            return
        if isinstance(after_fields, str):
            after_fields = [after_fields]
        ref_node = None
        for field_name in after_fields:
            ref_nodes = arch.xpath(f"//field[@name='{field_name}']")
            if ref_nodes:
                ref_node = ref_nodes[-1]
                break
        if ref_node is None:
            return
        parent = ref_node.getparent()
        idx = list(parent).index(ref_node)
        is_pivot = arch.tag == 'pivot'
        offset = 0
        for af in amount_fields:
            if af.currency_field and not is_pivot:
                currency_el = etree.Element('field')
                currency_el.set('name', af.currency_field)
                currency_el.set('column_invisible', 'True')
                parent.insert(idx + 1 + offset, currency_el)
                offset += 1
            field_el = etree.Element('field')
            field_el.set('name', af.name)
            if is_pivot:
                field_el.set('type', 'measure')
            else:
                field_el.set('optional', 'show')
                field_el.set('sum', 'Total')
            parent.insert(idx + 1 + offset, field_el)
            offset += 1
