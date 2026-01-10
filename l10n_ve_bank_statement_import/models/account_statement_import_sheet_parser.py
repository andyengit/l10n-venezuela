import logging

from odoo import api, models
from odoo.exceptions import UserError

try:
    from openpyxl.utils import column_index_from_string
except ImportError:
    column_index_from_string = None

_logger = logging.getLogger(__name__)


class AccountStatementImportSheetParser(models.TransientModel):
    _inherit = "account.statement.import.sheet.parser"

    def _parse_column_index(self, column_str):
        """Convierte una columna de string (letra o número) a índice numérico (1-based)"""
        if not column_str:
            return None
        try:
            if column_str.isdigit():
                return int(column_str)
            if column_index_from_string:
                return column_index_from_string(column_str.upper())
            raise UserError(
                "openpyxl no está disponible. No se puede convertir letra de columna a número."
            )
        except (ValueError, AttributeError):
            _logger.warning("No se pudo convertir columna '%s' a índice", column_str)
            return None

    def _get_balance_from_cell(self, csv_or_xlsx, row, column, mapping):
        """Obtiene el valor de saldo desde una celda específica"""
        if not row or not column:
            return None

        column_idx = self._parse_column_index(column)
        if not column_idx:
            return None

        try:
            if isinstance(csv_or_xlsx, tuple):
                sheet = csv_or_xlsx[1]
                if row <= sheet.max_row and column_idx <= sheet.max_column:
                    cell = sheet.cell(row, column_idx)
                    value = cell.value
                    if value is not None:
                        return self._parse_decimal(value, mapping)
            else:
                return None
        except Exception as e:
            _logger.warning("Error al leer celda [%s, %s]: %s", row, column, str(e))
            return None
        return None

    @api.model
    def parse(self, data_file, mapping, filename):
        result = super().parse(data_file, mapping, filename)
        if not result or len(result) < 3:
            return result

        currency_code, account_number, statements = result
        if not statements or not statements[0].get("transactions"):
            return result

        try:
            from io import BytesIO

            from openpyxl import load_workbook

            workbook = load_workbook(filename=BytesIO(data_file), data_only=True)
            csv_or_xlsx = (workbook, workbook.worksheets[0])
        except Exception:
            return result

        initial_balance = None
        final_balance = None

        if hasattr(mapping, "initial_balance_row") and hasattr(
            mapping, "initial_balance_column"
        ):
            if mapping.initial_balance_row and mapping.initial_balance_column:
                initial_balance = self._get_balance_from_cell(
                    csv_or_xlsx,
                    mapping.initial_balance_row,
                    mapping.initial_balance_column,
                    mapping,
                )

        if hasattr(mapping, "final_balance_row") and hasattr(
            mapping, "final_balance_column"
        ):
            if mapping.final_balance_row and mapping.final_balance_column:
                final_balance = self._get_balance_from_cell(
                    csv_or_xlsx,
                    mapping.final_balance_row,
                    mapping.final_balance_column,
                    mapping,
                )

        if initial_balance is not None or final_balance is not None:
            statement_data = statements[0]
            if initial_balance is not None:
                statement_data["balance_start"] = initial_balance
            if final_balance is not None:
                statement_data["balance_end_real"] = final_balance

        return currency_code, account_number, statements

    def _parse_rows(self, mapping, currency_code, data, columns):
        lines_skip_after = 0
        if hasattr(mapping, "lines_skip_after_header"):
            lines_skip_after = mapping.lines_skip_after_header or 0

        if not lines_skip_after:
            return super()._parse_rows(mapping, currency_code, data, columns)

        csv_or_xlsx, data_file = data

        if isinstance(csv_or_xlsx, tuple):
            numrows = csv_or_xlsx[1].max_row
        else:
            numrows = len(str(data_file.strip()).split("\\n"))

        label_line = mapping.header_lines_skip_count
        footer_line = numrows - mapping.footer_lines_skip_count
        start_line = label_line + 1 + lines_skip_after

        lines = []
        if isinstance(csv_or_xlsx, tuple):
            sheet = csv_or_xlsx[1]
            header_row_num = label_line + 1
            header_row = (
                sheet[header_row_num] if header_row_num <= sheet.max_row else []
            )
            max_col = len(header_row) if header_row else sheet.max_column
            for row_num in range(start_line, footer_line + 1):
                values = []
                for col_index in range(mapping.offset_column + 1, max_col + 1):
                    cell = sheet.cell(row_num, col_index)
                    cell_value = cell.value
                    values.append(cell_value)
                if mapping.skip_empty_lines and not any(values):
                    continue
                line = self._process_row_values(values, mapping, currency_code, columns)
                if line:
                    lines.append(line)
        else:
            rows = csv_or_xlsx
            for row_idx, row in enumerate(rows, label_line):
                if row_idx < start_line - 1:
                    continue
                if row_idx >= footer_line:
                    continue
                values = list(row)
                if mapping.skip_empty_lines and not any(values):
                    continue
                line = self._process_row_values(values, mapping, currency_code, columns)
                if line:
                    lines.append(line)
        return lines
