from odoo import SUPERUSER_ID, api


def post_init_hook(env):
    _enable_settings(env)


def _enable_settings(env):
    group_user = env.ref('base.group_user')
    groups_to_enable = [
        # Contabilidad
        'account.group_delivery_invoice_address',       # Direcciones del cliente
        'account.group_warning_account',                 # Advertencias en facturas
        # Producto
        'uom.group_uom',                                # Unidades de medida
        'product.group_product_variant',                 # Variantes
        'product.group_product_pricelist',               # Listas de precios
        # Ventas
        'sale.group_discount_per_so_line',               # Descuentos
        'sale.group_warning_sale',                       # Advertencias de venta
        'sale.group_proforma_sales',                     # Factura proforma
        'sale_management.group_sale_order_template',     # Plantillas de cotización
        # Inventario
        'stock.group_stock_multi_locations',             # Ubicaciones de almacenamiento
        'stock.group_adv_location',                      # Rutas multietapa
        'stock.group_production_lot',                    # Números de serie y lote
    ]

    for xml_id in groups_to_enable:
        group = env.ref(xml_id, raise_if_not_found=False)
        if group and group not in group_user.implied_ids:
            group_user.implied_ids |= group

    # Términos y condiciones: Agregar una nota
    env['ir.config_parameter'].sudo().set_param(
        'account.use_invoice_terms', True
    )
    companies = env['res.company'].sudo().search([])
    companies.write({
        'terms_type': 'plain',
        'display_invoice_tax_company_currency': True,
    })

    # Control de facturas de compra: Cantidad ordenada
    env['ir.default'].sudo().set(
        'product.template', 'purchase_method', 'purchase'
    )

    # Activar ruta MTO (Bajo pedido)
    mto_route = env.ref('stock.route_warehouse0_mto', raise_if_not_found=False)
    if mto_route and not mto_route.active:
        mto_route.active = True
