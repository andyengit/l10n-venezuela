import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { _t } from "@web/core/l10n/translation";
import { onMounted, onWillUnmount } from "@odoo/owl";

/**
 * Currency selection button for Payment Screen
 * Adds a floating button in the top-left corner for currency selection
 */

patch(PaymentScreen.prototype, {
    setup() {
        super.setup();
        this.pos = this.env.services.pos;

        // Listen for exchange currency changes to update the UI
        onMounted(() => {
            this.currencyEventListener = () => this.render();
            this.pos.currencyEventBus?.addEventListener("change:exchange_currency_id", this.currencyEventListener);
        });
        onWillUnmount(() => {
            if (this.currencyEventListener) {
                this.pos.currencyEventBus?.removeEventListener("change:exchange_currency_id", this.currencyEventListener);
            }
        });
    },

    /**
     * Get the current exchange currency for display (reactive getter)
     */
    get exchangeCurrency() {
        return this.pos.getExchangeCurrencyForDisplay();
    },

    /**
     * Handle exchange currency selection from payment screen
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
     * Get the converted total due amount
     */
    getConvertedTotalDue() {
        const exchangeCurrency = this.exchangeCurrency;
        if (!exchangeCurrency) {
            return null;
        }

        const totalDue = this.currentOrder.getTotalDue();
        const companyCurrency = this.pos.company.currency_id;

        if (!companyCurrency || exchangeCurrency.id === companyCurrency.id) {
            return null; // No conversion needed
        }

        // Use the convertCurrency function from any product
        const products = this.pos.models["product.product"]?.readAll() || [];
        const sampleProduct = products.length > 0 ? products[0] : null;

        if (sampleProduct && sampleProduct.convertCurrency) {
            const convertedTotal = sampleProduct.convertCurrency(totalDue, companyCurrency, exchangeCurrency);

            // Format the converted total with currency symbol
            const formattedTotal = convertedTotal.toFixed(2);
            const currencySymbol = exchangeCurrency.symbol || exchangeCurrency.name || 'USD';
            return `${currencySymbol}${formattedTotal}`;
        }

        return null;
    },

    /**
     * Check if total due conversion should be shown
     */
    shouldShowTotalDueConversion() {
        const exchangeCurrency = this.exchangeCurrency;
        const companyCurrency = this.pos.company.currency_id;
        const totalDue = this.currentOrder.getTotalDue();

        return exchangeCurrency && companyCurrency &&
               exchangeCurrency.id !== companyCurrency.id &&
               totalDue > 0;
    }
});
