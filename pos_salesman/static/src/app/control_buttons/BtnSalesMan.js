/** @odoo-module */

import { _t } from "@web/core/l10n/translation";

import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";
import { SalesManPos } from "@pos_salesman/app/popups/SalesManPos";

import { registry } from "@web/core/registry";

export class BtnSalesMan extends Component {
    static template = "pos_salesman.BtnSalesMan";
    static props = { "*": true }; // Pachacutec: v137 - Validación OWL 18
    setup() {
        this.pos = usePos();
        this.dialog = useService("dialog");
        this.notification = useService("notification");
    }
    async onClick() {
        const order = this.pos.get_order();
        if (!order) return;

        let salesman_ids = this.pos.config.salesman_ids || [];
        // Normalización para Odoo 18: asegurar que tengamos IDs numéricos puros
        if (salesman_ids && typeof salesman_ids === 'object') {
            salesman_ids = Object.values(salesman_ids).map(id => typeof id === 'object' ? id.id : id);
        }
        
        console.log("BtnSalesMan: accessing this.pos.models['hr.employee']...");
        const employeeStore = this.pos.models['hr.employee'];
        if (employeeStore) {
            console.log("BtnSalesMan: Store found. Record count:", employeeStore.getAll().length);
            console.log("BtnSalesMan: IDs in Config (normalized):", salesman_ids);
        } else {
            console.log("BtnSalesMan: Store NOT FOUND in this.pos.models");
        }

        const salesman_list = employeeStore ? employeeStore.getAll().filter(s => salesman_ids.includes(s.id)) : [];
        console.log("BtnSalesMan: Final salesman_list (config filtered) count:", salesman_list.length);

        if (salesman_list.length === 0) {
            this.notification.add(_t("No hay vendedores configurados para este punto de venta."), {
                title: _t("Sin Vendedores"),
                type: "danger",
            });
            return;
        }

        const salesmen = salesman_list.map(s => ({
            ...s,
            image_url: `/web/image/hr.employee/${s.id}/image_128`
        }));

        this.dialog.add(SalesManPos, {
            title: _t("Seleccionar Vendedor"),
            salesmen: salesmen,
            getPayload: (salesmanId) => {
                order.set_salesman_id(salesmanId);
            },
        });
    }
    get salesmanName() {
        const order = this.pos.get_order();
        return (order && order.salesman_id) ? order.salesman_id.name : "";
    }
}

import { ActionpadWidget } from "@point_of_sale/app/screens/product_screen/action_pad/action_pad";
import { patch } from "@web/core/utils/patch";

patch(ActionpadWidget.components, {
    BtnSalesMan,
});
