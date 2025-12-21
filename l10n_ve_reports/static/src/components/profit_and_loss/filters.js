/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { AccountReport } from "@l10n_ve_reports/components/account_report/account_report";
import { AccountReportFilters } from "@l10n_ve_reports/components/account_report/filters/filters";

export class ProfitAndLossFilters extends AccountReportFilters {
    static template = "l10n_ve_reports.ProfitAndLossFilters";
    static components = {
        ...AccountReportFilters.components,
        Dropdown,
        DropdownItem,
    };

    //------------------------------------------------------------------------------------------------------------------
    // Currency Conversion
    //------------------------------------------------------------------------------------------------------------------
    async onCurrencyChange(currencyId) {
        const id = currencyId ? (typeof currencyId === 'number' ? currencyId : parseInt(currencyId)) : false;
        await this.filterClicked({ optionKey: "convert_to_currency", optionValue: id, reload: true });
    }

    async onCurrencyRateDateChange(ev) {
        const date = ev.target.value;
        await this.filterClicked({ optionKey: "currency_rate_date", optionValue: date, reload: true });
    }

    async onUseDocumentDateChange(ev) {
        const useDocumentDate = ev.target.checked;
        await this.filterClicked({ optionKey: "use_document_date", optionValue: useDocumentDate, reload: true });
    }

    get selectedCurrencyName() {
        if (!this.controller.options.convert_to_currency) {
            return _t("Sin conversión");
        }
        const currency = this.controller.options.available_currencies.find(
            c => c.id === this.controller.options.convert_to_currency
        );
        return currency ? currency.name : _t("Sin conversión");
    }

}

AccountReport.registerCustomComponent(ProfitAndLossFilters);

