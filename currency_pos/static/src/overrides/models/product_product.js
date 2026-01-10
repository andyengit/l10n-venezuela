import { ProductProduct } from "@point_of_sale/app/models/product_product";
import { roundPrecision } from "@web/core/utils/numbers";
import { patch } from "@web/core/utils/patch";

patch(ProductProduct.prototype, {
    /**
     * Convert an amount from one currency to another using the available currency rates
     * @param {number} amount - The amount to convert
     * @param {Object} fromCurrency - The source currency object
     * @param {Object} toCurrency - The target currency object
     * @returns {number} - The converted amount
     */
    convertCurrency(amount, fromCurrency, toCurrency) {
        console.log('convertCurrency called with:', amount, fromCurrency?.name, toCurrency?.name);

        // Validate inputs
        if (!amount || isNaN(amount) || !fromCurrency || !toCurrency) {
            console.log('Invalid inputs, returning original amount');
            return amount || 0;
        }

        if (fromCurrency.id === toCurrency.id) {
            console.log('Same currency, returning original amount');
            return amount;
        }

        try {
            // Get currency rates from the models
            const currencyRates = this.models["res.currency.rate"]?.readAll() || [];
            console.log('Available currency rates:', currencyRates);

            // Get company currency (base currency)
            const company = this.models['res.company']?.getFirst();
            const companyCurrency = company?.currency_id;
            console.log('Company currency:', companyCurrency?.name);

            if (!companyCurrency) {
                console.log('No company currency, returning original');
                return amount; // No company currency, return original
            }

            // If converting to company currency, use inverse of from rate
            if (toCurrency.id === companyCurrency.id) {
                console.log('Converting TO company currency');
                const fromRate = currencyRates.find(rate => {
                    const currencyId = Array.isArray(rate.currency_id) ? rate.currency_id[0] : (rate.currency_id?.id || rate.currency_id);
                    return currencyId === fromCurrency.id;
                });
                console.log('Found fromRate:', fromRate);

                if (fromRate) {
                    const rateValue = fromRate.inverse_rate || (1 / fromRate.rate) || 1;
                    console.log('Using rate value for TO company:', rateValue);
                    const result = amount * rateValue;
                    console.log('Result:', result);
                    return result;
                }
            }

            // If converting from company currency, use direct rate
            if (fromCurrency.id === companyCurrency.id) {
                console.log('Converting FROM company currency');
                const toRate = currencyRates.find(rate => {
                    const currencyId = Array.isArray(rate.currency_id) ? rate.currency_id[0] : (rate.currency_id?.id || rate.currency_id);
                    return currencyId === toCurrency.id;
                });
                console.log('Found toRate:', toRate);

                if (toRate) {
                    const rateValue = toRate.inverse_rate || (1 / toRate.rate) || 1;
                    console.log('Using rate value for FROM company:', rateValue);
                    const result = amount / rateValue;
                    console.log('Result:', result);
                    return result;
                }
            }

            // For cross-currency conversion: from -> company -> to
            const fromRate = currencyRates.find(rate => {
                const currencyId = Array.isArray(rate.currency_id) ? rate.currency_id[0] : (rate.currency_id?.id || rate.currency_id);
                return currencyId === fromCurrency.id;
            });

            const toRate = currencyRates.find(rate => {
                const currencyId = Array.isArray(rate.currency_id) ? rate.currency_id[0] : (rate.currency_id?.id || rate.currency_id);
                return currencyId === toCurrency.id;
            });

            if (fromRate && toRate) {
                const fromRateValue = fromRate.inverse_rate || (1 / fromRate.rate) || 1;
                const toRateValue = toRate.inverse_rate || (1 / toRate.rate) || 1;

                // Convert: amount -> company currency -> target currency
                const amountInCompany = amount * fromRateValue;
                const finalAmount = amountInCompany / toRateValue;

                return finalAmount;
            }

            return amount; // If no rates found, return original amount
        } catch (error) {
            console.warn("Error in convertCurrency:", error);
            return amount; // Return original amount on error
        }
    },


    // Override the get_price method to handle currency conversion in pricelist rules
    get_price(
        pricelist,
        quantity,
        price_extra = 0,
        recurring = false,
        list_price = false,
        original_line = false,
        related_lines = []
    ) {
        // Call parent method to get base behavior
        const result = super.get_price(...arguments);

        // If no rule was found, return the base result
        const rule = this.getPricelistRule(pricelist, quantity);
        if (!rule) {
            return result;
        }

        // Only override behavior for fixed price rules with different currencies
        if (rule.compute_price === "fixed") {
            const posConfig = this.models["pos.config"]?.getFirst();
            const posCurrency = posConfig?.currency_id;
            const ruleCurrency = rule.currency_id;

            // Get currency ids safely
            let ruleCurrencyId, posCurrencyId;
            if (ruleCurrency) {
                if (Array.isArray(ruleCurrency)) {
                    ruleCurrencyId = ruleCurrency[0];
                } else if (ruleCurrency.id) {
                    ruleCurrencyId = ruleCurrency.id;
                } else {
                    ruleCurrencyId = ruleCurrency;
                }
            }
            if (posCurrency) {
                if (Array.isArray(posCurrency)) {
                    posCurrencyId = posCurrency[0];
                } else if (posCurrency.id) {
                    posCurrencyId = posCurrency.id;
                } else {
                    posCurrencyId = posCurrency;
                }
            }

            if (ruleCurrencyId && posCurrencyId && ruleCurrencyId !== posCurrencyId) {
                // Calculate base price without the fixed price rule
                let basePrice = (list_price || this.lst_price) + (price_extra || 0);

                // Apply base calculation if needed
                if (rule.base === "pricelist") {
                    if (rule.base_pricelist_id) {
                        basePrice = this.get_price(rule.base_pricelist_id, quantity, 0, true, list_price);
                    }
                } else if (rule.base === "standard_price") {
                    basePrice = this.standard_price;
                }

                // Apply currency conversion to the fixed price
                // Get the full currency objects from models
                const fromCurrencyObj = this.models["res.currency"]?.get(ruleCurrencyId);
                const toCurrencyObj = this.models["res.currency"]?.get(posCurrencyId);

                if (fromCurrencyObj && toCurrencyObj) {
                    const convertedFixedPrice = this.convertCurrency(rule.fixed_price, fromCurrencyObj, toCurrencyObj);

                    // Apply other rules (discount, surcharge, etc.) to the converted fixed price
                    let finalPrice = convertedFixedPrice;

                    if (rule.price_discount) {
                        finalPrice -= finalPrice * (rule.price_discount / 100);
                    }
                    if (rule.price_round) {
                        finalPrice = roundPrecision(finalPrice, rule.price_round);
                    }
                    if (rule.price_surcharge) {
                        finalPrice += rule.price_surcharge;
                    }
                    if (rule.price_min_margin) {
                        finalPrice = Math.max(finalPrice, basePrice + rule.price_min_margin);
                    }
                    if (rule.price_max_margin) {
                        finalPrice = Math.min(finalPrice, basePrice + rule.price_max_margin);
                    }

                    return finalPrice;
                }
            }
        }

        // For all other cases, return the parent result
        return result;
    }
});
