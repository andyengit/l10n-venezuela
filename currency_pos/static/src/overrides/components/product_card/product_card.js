import { ProductCard } from "@point_of_sale/app/generic_components/product_card/product_card";
import { patch } from "@web/core/utils/patch";

patch(ProductCard.prototype, {
    get productPrice() {
        if (!this.props.product) {
            return "";
        }

        try {
            // Get the current pricelist from the POS
            const currentOrder = this.env.services.pos.get_order();
            const pricelist = currentOrder?.pricelist_id;
            console.log('ProductCard: Current pricelist:', pricelist?.name, 'ID:', pricelist?.id);

            // Calculate the price using the extended get_price method
            const price = this.props.product.get_price(pricelist, 1);

            // Format the price using Odoo utils
            return this.env.utils.formatCurrency(price);
        } catch (error) {
            console.warn("Error calculating product price:", error);
            return "";
        }
    },

    get productPricesInOtherCurrencies() {
        if (!this.props.product) {
            return [];
        }

        try {
            const prices = [];
            const posCurrency = this.env.services.pos.currency;

            // Get current order and pricelist
            const currentOrder = this.env.services.pos.get_order();
            const currentPricelist = currentOrder?.pricelist_id;

            // Get all currencies except the POS currency
            const currencies = this.env.services.pos.models["res.currency"].readAll()
                .filter(currency => currency.id !== posCurrency.id);


            for (const currency of currencies) {
                try {
                    // Calculate price in POS currency first
                    const price = this.props.product.get_price(currentPricelist, 1);

                    // Convert to target currency using the convertCurrency function
                    const convertedPrice = this.props.product.convertCurrency(price, posCurrency, currency);

                    // Format manually with currency symbol to ensure correct display
                    const formattedPrice = `${currency.symbol || currency.name} ${convertedPrice.toLocaleString('es-ES', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;

                    prices.push({
                        currency: currency,
                        price: formattedPrice
                    });
                } catch (error) {
                    console.warn("Error calculating price for currency " + currency.name + ":", error);
                }
            }

            return prices;
        } catch (error) {
            console.warn("Error calculating prices in other currencies:", error);
            return [];
        }
    }
});
