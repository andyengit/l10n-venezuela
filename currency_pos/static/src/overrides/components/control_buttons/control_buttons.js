import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { patch } from "@web/core/utils/patch";
import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { _t } from "@web/core/l10n/translation";

patch(ControlButtons.prototype, {
    /**
     * Get the current exchange currency for display
     */
    get exchangeCurrency() {
        return this.pos.getExchangeCurrencyForDisplay();
    },
    /**
     * Override getPricelistList to filter out pricelists with different currencies
     * Only show pricelists that match the POS currency
     */
    getPricelistList() {
        const companyCurrencyId = this.pos.company.currency_id.id;
        return super.getPricelistList().filter((pricelist) => pricelist.item.currency_id?.id === companyCurrencyId);
    },

    /**
     * Get the list of available currencies for exchange selection
     */
    getExchangeCurrencyList() {
        const currencyList = [];
        const currentExchangeCurrency = this.exchangeCurrency;

        // Add company currency first
        const companyCurrency = this.pos.company.currency_id;
        if (companyCurrency) {
            currencyList.push({
                id: companyCurrency.id,
                label: `${companyCurrency.name} (${companyCurrency.symbol})`,
                isSelected: (!currentExchangeCurrency) ||
                           (currentExchangeCurrency?.id === companyCurrency.id),
                item: companyCurrency,
            });
        }

        // Add other currencies from the system
        const currencyModel = this.pos.models["res.currency"];
        if (currencyModel) {
            currencyModel.forEach((currency) => {
                if (currency.id !== companyCurrency?.id) {
                    currencyList.push({
                        id: currency.id,
                        label: `${currency.name} (${currency.symbol})`,
                        isSelected: currentExchangeCurrency &&
                                   currentExchangeCurrency.id === currency.id,
                        item: currency,
                    });
                }
            });
        }

        return currencyList;
    },

    /**
     * Handle exchange currency selection
     */
    async clickExchangeCurrency() {
        const selectionList = this.getExchangeCurrencyList();
        const selectedCurrency = await makeAwaitable(this.dialog, SelectionPopup, {
            title: _t("Seleccionar moneda de cambio"),
            list: selectionList,
        });

        if (selectedCurrency) {
            // Update the global POS exchange currency
            this.pos.setExchangeCurrency(selectedCurrency);
        }
    }
});
