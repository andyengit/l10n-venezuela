# Powered By Andy - SaaS

Módulo integrador que instala todos los módulos base necesarios para el SaaS de Venezuela en Odoo 18.0.

## Repositorios Necesarios

### 1. `andyengit/l10n-venezuela` (este repositorio)

Contiene los módulos de localización venezolana:

| Módulo | Descripción |
|--------|-------------|
| `l10n_ve_seniat` | Plan contable SENIAT |
| `l10n_ve_seniat_sale` | Extensión de ventas para SENIAT |
| `l10n_ve_stock` | Inventario Venezuela |
| `l10n_ve_reports` | Reportes Venezuela |
| `l10n_ve_igtf` | IGTF (Impuesto a Grandes Transacciones Financieras) |
| `l10n_ve_withholding` | Retenciones |
| `l10n_ve_exchange_rates` | Tasas de cambio |
| `l10n_ve_bank_statement_import` | Importación de estados de cuenta bancarios |
| `currency_account` | Moneda en contabilidad |
| `currency_purchase` | Moneda en compras |
| `currency_sale` | Moneda en ventas |
| `res_currency_rate_provider_BCV` | Proveedor de tasas BCV |
| `poweredbyandy_saas` | Este módulo |

---

### 2. `OCA/web` — Módulos Web

Repositorio: `https://github.com/OCA/web.git` — Rama: `18.0`

| Módulo |
|--------|
| `web_responsive` |
| `web_chatter_position` |
| `web_dialog_size` |
| `web_dark_mode` |
| `web_datetime_picker_default_time` |
| `web_excel_export_dynamic_expand` |
| `web_search_with_and` |
| `web_widget_numeric_step` |
| `web_copy_confirm` |
| `web_company_color` |
| `web_group_expand` |
| `web_pwa_customize` |

---

### 3. `OCA/currency` — Monedas

Repositorio: `https://github.com/OCA/currency.git` — Rama: `18.0`

| Módulo |
|--------|
| `currency_rate_update` |

---

### 4. `OCA/partner-contact` — Contactos

Repositorio: `https://github.com/OCA/partner-contact.git` — Rama: `18.0`

| Módulo |
|--------|
| `partner_vat_unique` |
| `partner_ref_unique` |
| `partner_external_map` |
| `partner_contact_birthdate` |
| `partner_contact_age_range` |

---

### 5. `OCA/account-reconcile` — Conciliación Contable

Repositorio: `https://github.com/OCA/account-reconcile.git` — Rama: `18.0`

| Módulo |
|--------|
| `account_in_payment` |
| `account_partner_reconcile` |
| `account_reconcile_oca` |
| `account_reconcile_model_oca` |

---

### 6. `OCA/account-invoicing` — Facturación

Repositorio: `https://github.com/OCA/account-invoicing.git` — Rama: `18.0`

| Módulo |
|--------|
| `account_invoice_refund_link` |
| `account_invoice_supplierinfo_update` |

---

### 7. `poweredbyandy/bank-statement-import` — Importación de Extractos Bancarios

Repositorio: `https://github.com/poweredbyandy/bank-statement-import.git` — Rama: `18.0`

> **Nota:** Este es un fork con adaptaciones propias. No usar el repositorio OCA directamente.

| Módulo |
|--------|
| `account_statement_import_base` |
| `account_statement_import_file_reconcile_oca` |
| `account_statement_import_sheet_file` |

---

### 8. `OCA/server-brand` — Personalización de Marca

Repositorio: `https://github.com/OCA/server-brand.git` — Rama: `18.0`

| Módulo |
|--------|
| `portal_odoo_debranding` |
| `disable_odoo_online` |

---

### 9. `OCA/server-ux` — UX del Servidor

Repositorio: `https://github.com/OCA/server-ux.git` — Rama: `18.0`

| Módulo |
|--------|
| `developer_menu` |

---

### 10. `OCA/social` — Social / Correo

Repositorio: `https://github.com/OCA/social.git` — Rama: `18.0`

| Módulo |
|--------|
| `mail_notification_with_history` |

---

### Módulos de Odoo Core (no requieren clonado extra)

Estos módulos vienen incluidos en Odoo 18.0 Community/Enterprise:

- `account`
- `stock`
- `google_calendar`
- `microsoft_calendar`
- `product_margin`
- `board`

---

## Comando para clonar todos los repositorios

Ejecutar desde el directorio donde se desea almacenar los addons (ej: `/workspace/oca`):

```bash
#!/bin/bash
# ==============================================================
# Script de clonado de repositorios para poweredbyandy_saas
# Odoo 18.0
# ==============================================================

BRANCH="18.0"
DEPTH="--depth 1"  # Clonar solo el último commit (más rápido). Quitar para historial completo.
OCA_DIR="./oca"
CUSTOM_DIR="./custom"

mkdir -p "$OCA_DIR" "$CUSTOM_DIR"

echo "=== Clonando repositorio principal l10n-venezuela ==="
git clone --branch $BRANCH $DEPTH https://github.com/andyengit/l10n-venezuela.git "$CUSTOM_DIR/l10n-venezuela"

echo ""
echo "=== Clonando repositorios OCA ==="

declare -A REPOS=(
  ["web"]="https://github.com/OCA/web.git"
  ["currency"]="https://github.com/OCA/currency.git"
  ["partner-contact"]="https://github.com/OCA/partner-contact.git"
  ["account-reconcile"]="https://github.com/OCA/account-reconcile.git"
  ["account-invoicing"]="https://github.com/OCA/account-invoicing.git"
  ["server-brand"]="https://github.com/OCA/server-brand.git"
  ["server-ux"]="https://github.com/OCA/server-ux.git"
  ["social"]="https://github.com/OCA/social.git"
)

for name in "${!REPOS[@]}"; do
  url="${REPOS[$name]}"
  echo "  -> Clonando $name desde $url ..."
  git clone --branch $BRANCH $DEPTH "$url" "$OCA_DIR/$name"
done

echo ""
echo "=== Clonando fork de bank-statement-import ==="
git clone --branch $BRANCH $DEPTH https://github.com/poweredbyandy/bank-statement-import.git "$OCA_DIR/bank-statement-import"

echo ""
echo "=== ¡Listo! ==="
echo ""
echo "Agrega las siguientes rutas al addons_path de tu odoo.conf:"
echo "  $CUSTOM_DIR/l10n-venezuela,"
echo "  $OCA_DIR/web,"
echo "  $OCA_DIR/currency,"
echo "  $OCA_DIR/partner-contact,"
echo "  $OCA_DIR/account-reconcile,"
echo "  $OCA_DIR/account-invoicing,"
echo "  $OCA_DIR/bank-statement-import,"
echo "  $OCA_DIR/server-brand,"
echo "  $OCA_DIR/server-ux,"
echo "  $OCA_DIR/social"
```

### Uso rápido (copiar y pegar)

Si prefieres comandos sueltos sin script:

```bash
BRANCH="18.0"

# Repositorio principal
git clone -b $BRANCH --depth 1 https://github.com/andyengit/l10n-venezuela.git custom/l10n-venezuela

# OCA
git clone -b $BRANCH --depth 1 https://github.com/OCA/web.git oca/web
git clone -b $BRANCH --depth 1 https://github.com/OCA/currency.git oca/currency
git clone -b $BRANCH --depth 1 https://github.com/OCA/partner-contact.git oca/partner-contact
git clone -b $BRANCH --depth 1 https://github.com/OCA/account-reconcile.git oca/account-reconcile
git clone -b $BRANCH --depth 1 https://github.com/OCA/account-invoicing.git oca/account-invoicing
git clone -b $BRANCH --depth 1 https://github.com/OCA/server-brand.git oca/server-brand
git clone -b $BRANCH --depth 1 https://github.com/OCA/server-ux.git oca/server-ux
git clone -b $BRANCH --depth 1 https://github.com/OCA/social.git oca/social

# Fork propio (NO usar el de OCA directamente)
git clone -b $BRANCH --depth 1 https://github.com/poweredbyandy/bank-statement-import.git oca/bank-statement-import
```

### Ejemplo de `addons_path` en `odoo.conf`

```ini
addons_path =
    /ruta/odoo/addons,
    /ruta/odoo/odoo/addons,
    /ruta/custom/l10n-venezuela,
    /ruta/oca/web,
    /ruta/oca/currency,
    /ruta/oca/partner-contact,
    /ruta/oca/account-reconcile,
    /ruta/oca/account-invoicing,
    /ruta/oca/bank-statement-import,
    /ruta/oca/server-brand,
    /ruta/oca/server-ux,
    /ruta/oca/social
```
