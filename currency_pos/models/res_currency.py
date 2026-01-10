from odoo import models, api


class ResCurrency(models.Model):
    _inherit = 'res.currency'

    @api.model
    def _load_pos_data_domain(self, data):
        # Cargar todas las monedas activas en lugar de solo las del POS
        return [('active', '=', True)]

    @api.model
    def _load_pos_data_fields(self, config_id):
        # Añadir inverse_rate a los campos cargados
        fields_list = super()._load_pos_data_fields(config_id)
        if 'inverse_rate' not in fields_list:
            fields_list.append('inverse_rate')
        return fields_list

