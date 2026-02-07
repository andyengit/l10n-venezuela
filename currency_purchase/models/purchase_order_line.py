from lxml import etree

from odoo import api, fields, models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    @api.model
    def _compute_currency_field(self, currency_id):
        date = self.order_id.date_order or fields.Date.today()
        to_currency = self.env["res.currency"].browse(currency_id)
        total_in_currency = self.currency_id._convert(
            self.price_subtotal, to_currency, self.order_id.company_id, date
        )
        return total_in_currency

    @api.model
    def _compute_price_unit_currency_field(self, currency_id):
        date = self.order_id.date_order or fields.Date.today()
        to_currency = self.env["res.currency"].browse(currency_id)
        return self.currency_id._convert(
            self.price_unit, to_currency, self.order_id.company_id, date
        )

    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == 'list':
            self._inject_currency_fields_to_view(arch, 'price_subtotal')
            self._inject_currency_fields_to_view(
                arch, 'price_unit', 'x_price_unit_currency_%'
            )
        return arch, view

    def _inject_currency_fields_to_view(self, arch, after_fields,
                                        field_pattern='x_amount_currency_%'):
        amount_fields = self.env['ir.model.fields'].sudo().search([
            ('model', '=', self._name),
            ('name', 'like', field_pattern),
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
        offset = 0
        for af in amount_fields:
            if af.currency_field:
                currency_el = etree.Element('field')
                currency_el.set('name', af.currency_field)
                currency_el.set('column_invisible', 'True')
                parent.insert(idx + 1 + offset, currency_el)
                offset += 1
            field_el = etree.Element('field')
            field_el.set('name', af.name)
            field_el.set('optional', 'show')
            parent.insert(idx + 1 + offset, field_el)
            offset += 1
