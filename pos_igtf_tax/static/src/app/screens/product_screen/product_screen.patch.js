/** @odoo-module */

import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

// Pachacutec: v18.0.1.0.46 - FUSIÓN DE ESTABILIDAD
// Bloquea la adición manual del producto IGTF.

patch(ProductScreen.prototype, {
    async addProductToOrder(product) {
        if (product.isIgtfProduct) {
            this.dialog.add(AlertDialog, {
                title: _t('Acción No Válida'),
                body: _t('No puedes agregar manualmente el producto IGTF. Este se calcula automáticamente basado en los pagos en divisas.'),
            });
            return;
        }

        return super.addProductToOrder(...arguments);
    }
});