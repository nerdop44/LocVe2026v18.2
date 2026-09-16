/** @odoo-module */

import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";
import { patch } from "@web/core/utils/patch";
import { onMounted } from "@odoo/owl";

// Pachacutec: v18.0.1.0.46 - FUSIÓN DE ESTABILIDAD
// Estilo visual para líneas IGTF en la interfaz.

patch(Orderline.prototype, {
    setup() {
        super.setup();

        onMounted(() => {
            if (this.props.line?.x_is_igtf_line) {
                if (this.el) {
                    this.el.classList.add("igtf-line");
                }
            }
        });
    }
});