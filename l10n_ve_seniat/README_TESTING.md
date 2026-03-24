# Tests y coverage para l10n_ve_seniat

## Ejecutar tests

```bash
cd /workspace
python odoo/odoo-bin -c odoo.conf --test-enable --stop-after-init \
  -d NOMBRE_BASE_DATOS \
  -i l10n_ve_seniat \
  --test-tags=post_install \
  --without-demo=all \
  --http-port=8070
```

Para ejecutar solo los tests de este módulo, el tag `post_install` ya filtra por los tests marcados. Los tests están en `l10n_ve_seniat/tests/`.

## Ejecutar tests con coverage

1. Instalar coverage: `pip install coverage`

2. Ejecutar con coverage:

```bash
cd /workspace
coverage run --source=custom/l10n-venezuela/l10n_ve_seniat \
  odoo/odoo-bin -c odoo.conf --test-enable --stop-after-init \
  -d NOMBRE_BASE_DATOS \
  -i l10n_ve_seniat \
  --test-tags=post_install \
  --without-demo=all \
  --http-port=8070
```

3. Ver reporte:

```bash
coverage report
coverage html -d htmlcov
```

## Estructura de tests

- `common.py`: Clase base L10nVeSeniatCommon con compañía venezolana
- `test_res_partner.py`: Validación RIF (check_vat_ve), taxpayer_type
- `test_account_tax.py`: Restricción de modificar alícuota de impuestos VE
- `test_account_move.py`: Validaciones VAT, total 0, múltiples impuestos, cancelación, draft, número de control
- `test_account_move_line.py`: Validación precio 0, subtotal
- `test_account_journal.py`: Secuencias SENIAT en diarios de venta
