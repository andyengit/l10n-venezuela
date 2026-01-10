from odoo import fields, models


class AccountStatementImportSheetMapping(models.Model):
    _inherit = "account.statement.import.sheet.mapping"

    lines_skip_after_header = fields.Integer(
        string="Líneas a omitir después del header",
        default=0,
        help="Número de líneas a omitir después del header antes de comenzar a leer las transacciones",
    )
    initial_balance_row = fields.Integer(
        string="Fila del Saldo Inicial",
        help="Fila donde se encuentra el saldo inicial (1-based, la primera fila es 1)",
    )
    initial_balance_column = fields.Char(
        string="Columna del Saldo Inicial",
        help="Columna donde se encuentra el saldo inicial (puede ser número 1-based o letra como 'E')",
    )
    final_balance_row = fields.Integer(
        string="Fila del Saldo Final",
        help="Fila donde se encuentra el saldo final (1-based, la primera fila es 1)",
    )
    final_balance_column = fields.Char(
        string="Columna del Saldo Final",
        help="Columna donde se encuentra el saldo final (puede ser número 1-based o letra como 'E')",
    )
