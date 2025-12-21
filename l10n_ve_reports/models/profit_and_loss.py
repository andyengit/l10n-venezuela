from odoo import models, fields, _
from dateutil.relativedelta import relativedelta


class ProfitAndLossCustomHandler(models.AbstractModel):
    _name = 'account.profit.and.loss.report.handler'
    _inherit = 'account.report.custom.handler'
    _description = "Profit and Loss Custom Handler"

    def _get_custom_display_config(self):
        return {
            'components': {
                'AccountReportFilters': 'l10n_ve_reports.ProfitAndLossFilters',
            },
        }

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        
        # Opciones de conversión de moneda
        today = fields.Date.today()
        options['convert_to_currency'] = (previous_options or {}).get('convert_to_currency', False)
        options['currency_rate_date'] = (previous_options or {}).get('currency_rate_date', fields.Date.to_string(today))
        options['use_document_date'] = (previous_options or {}).get('use_document_date', False)
        
        # Lista de monedas disponibles
        currencies = report.env['res.currency'].search([('active', '=', True)], order='name')
        options['available_currencies'] = [{
            'id': currency.id,
            'name': currency.name,
            'symbol': currency.symbol,
        } for currency in currencies]
        
        # Si hay conversión de moneda, establecer la moneda convertida como la moneda de formato por defecto
        if options['convert_to_currency']:
            target_currency = report.env['res.currency'].browse(options['convert_to_currency'])
            if target_currency.exists():
                options['forced_currency_id'] = target_currency.id

    def _custom_line_postprocessor(self, report, options, lines):
        # Obtener información de conversión de moneda
        target_currency_id = options.get('convert_to_currency')
        if not target_currency_id:
            return lines
        
        target_currency = self.env['res.currency'].browse(target_currency_id)
        if not target_currency.exists():
            return lines
        
        company_currency = self.env.company.currency_id
        if target_currency == company_currency:
            return lines
        
        # Función helper para conversión
        def get_conversion_rate(from_currency, to_currency, date):
            try:
                if hasattr(to_currency, '_get_conversion_rate'):
                    return to_currency._get_conversion_rate(from_currency, to_currency, self.env.company, date)
                else:
                    test_amount = 1.0
                    converted = from_currency._convert(test_amount, to_currency, self.env.company, date)
                    return converted / test_amount if test_amount != 0 else 1.0
            except Exception:
                rate_obj = self.env['res.currency.rate'].search([
                    ('currency_id', '=', to_currency.id),
                    ('name', '<=', date),
                    ('company_id', '=', self.env.company.id),
                ], order='name desc', limit=1)
                if rate_obj:
                    return 1.0 / rate_obj.rate if rate_obj.rate != 0 else 1.0
                return 1.0
        
        currency_rate_date = fields.Date.from_string(options.get('currency_rate_date', fields.Date.today()))
        use_document_date = options.get('use_document_date', False)
        
        # Obtener fechas de los períodos de columna si existen (para comparación)
        column_groups = options.get('column_groups', {})
        default_date_to = fields.Date.from_string(options['date']['date_to'])
        
        # Convertir valores en todas las líneas
        for line in lines:
            if 'columns' in line:
                for column_idx, column in enumerate(line.get('columns', [])):
                    # Convertir valores monetarios
                    if column.get('figure_type') == 'monetary' or column.get('expression_label') == 'balance':
                        # Determinar la tasa a usar según el período de la columna
                        rate_date = currency_rate_date
                        if use_document_date:
                            # Para Profit and Loss con fecha de documento, usar la fecha del período de la columna
                            # Las columnas tienen column_group_key que puede contener información del período
                            column_group_key = column.get('column_group_key')
                            if column_group_key and column_group_key in column_groups:
                                col_options = column_groups[column_group_key]
                                if 'date' in col_options and 'date_to' in col_options['date']:
                                    rate_date = fields.Date.from_string(col_options['date']['date_to'])
                            else:
                                # Usar la fecha por defecto del reporte
                                rate_date = default_date_to
                        
                        rate = get_conversion_rate(company_currency, target_currency, rate_date)
                        
                        # Convertir el valor
                        if 'no_format' in column and column['no_format'] is not None:
                            column['no_format'] = column['no_format'] * rate
                        
                        # Actualizar formato de moneda
                        if 'format_params' not in column:
                            column['format_params'] = {}
                        column['format_params']['currency_id'] = target_currency.id
                        column['format_params']['currency'] = target_currency
                        column['currency_id'] = target_currency.id
            
            # Actualizar currency_id en la línea si existe
            if 'currency_id' in line:
                line['currency_id'] = target_currency.id
            if 'currency' in line:
                line['currency'] = target_currency.display_name
        
        return lines

