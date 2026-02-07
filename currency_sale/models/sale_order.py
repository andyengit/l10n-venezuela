import json

from lxml import etree

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    total_currencies = fields.Json(
        string="Totales por Moneda",
        compute="_compute_total_currencies",
        store=True,
    )

    @api.depends(
        "currency_id",
        "amount_total",
        "date_order",
        "company_id.currency_id",
    )
    def _compute_total_currencies(self):
        for order in self:
            totals = {}
            currencies = self.env["res.currency"].search(
                [("active", "=", True), ("id", "!=", order.currency_id.id)]
            )
            for currency in currencies:
                date = order.date_order or fields.Date.today()
                total_in_currency = order.currency_id._convert(
                    order.amount_total, currency, order.company_id, date
                )
                totals[str(currency.id)] = {
                    "currency_id": currency.id,
                    "currency_name": currency.name,
                    "total": total_in_currency,
                }
            order.total_currencies = json.dumps(totals) if totals else False

    def _compute_tax_totals(self):
        super()._compute_tax_totals()
        for move in self:
            if move.tax_totals:
                move.tax_totals["display_in_company_currency"] = True

    @api.model
    def _compute_currency_field(self, currency_id):
        date = self.date_order or fields.Date.today()
        to_currency = self.env["res.currency"].browse(currency_id)
        total_in_currency = self.currency_id._convert(
            self.amount_total, to_currency, self.company_id, date
        )
        return total_in_currency

    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == 'list':
            self._inject_currency_fields_to_view(arch, 'amount_total')
        if view_type == 'form':
            self._inject_line_currency_fields_to_form(arch)
        return arch, view

    def _inject_line_currency_fields_to_form(self, arch):
        self._inject_line_fields_by_pattern(
            arch, 'price_subtotal', 'x_amount_currency_%'
        )
        self._inject_line_fields_by_pattern(
            arch, 'price_unit', 'x_price_unit_currency_%'
        )

    def _inject_line_fields_by_pattern(self, arch, after_field, field_pattern):
        line_fields = self.env['ir.model.fields'].sudo().search([
            ('model', '=', 'sale.order.line'),
            ('name', 'like', field_pattern),
        ])
        if not line_fields:
            return
        ref_nodes = arch.xpath(
            f"//field[@name='order_line']//list//field[@name='{after_field}']"
        )
        if not ref_nodes:
            return
        ref_node = ref_nodes[-1]
        parent = ref_node.getparent()
        idx = list(parent).index(ref_node)
        offset = 0
        for af in line_fields:
            currency_id = af.name.rsplit('_', 1)[-1]
            if af.currency_field:
                currency_el = etree.Element('field')
                currency_el.set('name', af.currency_field)
                currency_el.set('column_invisible', 'True')
                parent.insert(idx + 1 + offset, currency_el)
                offset += 1
            field_el = etree.Element('field')
            field_el.set('name', af.name)
            field_el.set('optional', 'show')
            field_el.set('readonly', '1')
            field_el.set(
                'column_invisible',
                f'parent.currency_id == {currency_id}'
            )
            parent.insert(idx + 1 + offset, field_el)
            offset += 1

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
