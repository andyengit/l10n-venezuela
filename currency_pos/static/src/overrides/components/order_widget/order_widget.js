import { OrderWidget } from "@point_of_sale/app/generic_components/order_widget/order_widget";
import { patch } from "@web/core/utils/patch";
import { useState, onMounted, onWillUnmount } from "@odoo/owl";

/**
 * Currency conversion functionality for order widget
 * Shows the total converted to the selected exchange currency
 */

patch(OrderWidget.prototype, {
    setup() {
        super.setup();
        // Access to POS store for currency conversion
        this.pos = this.env.services.pos;

        // Estado reactivo para forzar re-renders cuando cambia la moneda
        this.currencyState = useState({
            exchangeCurrencyId: null,
            updateKey: 0
        });

        // Listen for exchange currency changes to update the UI
        onMounted(() => {
            this.currencyEventListener = () => {
                const currentExchangeCurrencyId = this.pos.getExchangeCurrencyForDisplay()?.id;
                if (this.currencyState.exchangeCurrencyId !== currentExchangeCurrencyId) {
                    this.currencyState.exchangeCurrencyId = currentExchangeCurrencyId;
                    this.currencyState.updateKey++;
                }
            };
            this.pos.currencyEventBus?.addEventListener("change:exchange_currency_id", this.currencyEventListener);
        });

        // Limpiar event listeners cuando se desmonte el componente
        onWillUnmount(() => {
            if (this.currencyEventListener) {
                this.pos.currencyEventBus?.removeEventListener("change:exchange_currency_id", this.currencyEventListener);
            }
        });
    },

    /**
     * Get the converted total in the selected exchange currency
     */
    getConvertedTotal() {
        const exchangeCurrency = this.currencyState.exchangeCurrencyId ? this.pos.getExchangeCurrencyForDisplay() : null;
        if (!exchangeCurrency || !this.props.taxTotals) {
            return null;
        }

        const total = this.props.taxTotals.order_sign * this.props.taxTotals.order_total;

        // Get exchange rate between company currency and selected currency
        const companyCurrency = this.pos.company.currency_id;
        if (!companyCurrency || exchangeCurrency.id === companyCurrency.id) {
            return null; // No conversion needed
        }

        // Use the convertCurrency function from any product (they all have the same method)
        const products = this.pos.models["product.product"]?.readAll() || [];
        const sampleProduct = products.length > 0 ? products[0] : null;

        if (sampleProduct && sampleProduct.convertCurrency) {
            const convertedTotal = sampleProduct.convertCurrency(total, companyCurrency, exchangeCurrency);

            // Format the converted total with currency symbol
            const formattedTotal = convertedTotal.toFixed(2);
            const currencySymbol = exchangeCurrency.symbol || exchangeCurrency.name || 'USD';
            return `${currencySymbol}${formattedTotal}`;
        }

        return null;
    },

    /**
     * Check if total conversion should be shown
     */
    shouldShowTotalConversion() {
        const exchangeCurrency = this.currencyState.exchangeCurrencyId ? this.pos.getExchangeCurrencyForDisplay() : null;
        const companyCurrency = this.pos.company.currency_id;
        return exchangeCurrency && companyCurrency && exchangeCurrency.id !== companyCurrency.id && this.props.taxTotals;
    }
});
