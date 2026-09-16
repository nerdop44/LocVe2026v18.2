/** @odoo-module */

import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

// Pachacutec: v135 - Migración MoneyDetailsPopupUSD Odoo 18
export class MoneyDetailsPopupUSD extends Component {
    static template = "pos_show_dual_currency.MoneyDetailsPopupUSD";
    static props = false;

    setup() {
        this.pos = useService("pos");
        this.currency_ref = this.pos.res_currency_ref;
        this.state = useState({
            moneyDetailsRef: Object.fromEntries(this.pos.bills.map(bill => ([bill.value, 0]))),
            total_ref: 0,
        });

        if (this.props.manualInputCashCountUSD) {
            this.reset();
        }
    }

    get firstHalfMoneyDetailsRef() {
        const moneyDetailsKeysRef = Object.keys(this.state.moneyDetailsRef).sort((a, b) => a - b);
        return moneyDetailsKeysRef.slice(0, Math.ceil(moneyDetailsKeysRef.length / 2));
    }

    get lastHalfMoneyDetailsRef() {
        const moneyDetailsKeysRef = Object.keys(this.state.moneyDetailsRef).sort((a, b) => a - b);
        return moneyDetailsKeysRef.slice(Math.ceil(moneyDetailsKeysRef.length / 2), moneyDetailsKeysRef.length);
    }

    updateMoneyDetailsAmountRef() {
        let total_ref = Object.entries(this.state.moneyDetailsRef).reduce(
            (acc, [value, qty]) => acc + parseFloat(value) * (qty || 0), 0
        );
        this.state.total_ref = this.pos.round_decimals_currency(total_ref);
    }

    confirm() {
        let moneyDetailsNotesRef = this.state.total_ref ? 'Ref Currency Money details: \n' : null;
        this.pos.bills.forEach(bill => {
            if (this.state.moneyDetailsRef[bill.value]) {
                moneyDetailsNotesRef += `  - ${this.state.moneyDetailsRef[bill.value]} x ${this.pos.format_currency_ref(bill.value)}\n`;
            }
        });
        const payload = { 
            total_ref: this.state.total_ref, 
            moneyDetailsNotesRef, 
            moneyDetailsRef: { ...this.state.moneyDetailsRef } 
        };
        this.props.onConfirm(payload);
    }

    reset() {
        for (let key in this.state.moneyDetailsRef) {
            this.state.moneyDetailsRef[key] = 0;
        }
        this.state.total_ref = 0;
    }

    discard() {
        this.reset();
        this.props.onDiscard();
    }
}
