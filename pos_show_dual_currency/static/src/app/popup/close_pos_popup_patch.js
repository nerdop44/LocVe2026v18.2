/** @odoo-module */

import { ClosePosPopup } from "@point_of_sale/app/navbar/closing_popup/closing_popup";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { MoneyDetailsPopupUSD } from "./money_details_popup_usd";
import { _t } from "@web/core/l10n/translation";
import { parseFloat } from "@web/views/fields/parsers";

// Pachacutec: v18.0.1.2.19 - Estabilización de Assets, Props y Reactividad Odoo 18
if (ClosePosPopup.props) {
    if (Array.isArray(ClosePosPopup.props)) {
        const propsObj = {};
        for (const propName of ClosePosPopup.props) {
            propsObj[propName] = { optional: true };
        }
        ClosePosPopup.props = propsObj;
    }
    Object.assign(ClosePosPopup.props, {
        default_cash_details_ref: { type: Object, optional: true },
        igtf_totals: { type: Object, optional: true },
        amount_authorized_diff_ref: { type: Number, optional: true },
    });
}


patch(ClosePosPopup.prototype, {
    setup() {
        super.setup();
        this.dialog = useService("dialog");
        this.manualInputCashCountUSD = false;
        this.moneyDetailsUSD = null;
    },

    getInitialState() {
        const state = super.getInitialState();
        state.payments_usd = {};
        const cashDetailsRef = this.props.default_cash_details_ref;
        if (this.pos.config.cash_control && cashDetailsRef && cashDetailsRef.id) {
            const ref_id = cashDetailsRef.id;
            state.payments_usd[ref_id] = {
                counted: "0",
                difference: -(cashDetailsRef.amount || 0),
                number: 0
            };
            if (!state.payments[ref_id]) {
                state.payments[ref_id] = {
                    counted: "0",
                };
            }
        }
        return state;
    },

    autoFillCashCountUSD() {
        const cashDetailsRef = this.props.default_cash_details_ref;
        if (cashDetailsRef && cashDetailsRef.id) {
            const ref_id = cashDetailsRef.id;
            const count = cashDetailsRef.amount;
            this.state.payments_usd[ref_id].counted = this.env.utils.formatCurrency(count, false);
            this.handleInputChangeUSD(ref_id);
        }
    },

    async confirm() {
        if (!this.cashControl || !this.hasDifferenceUSD()) {
            return super.confirm();
        } else if (this.hasUserAuthorityUSD()) {
            const confirmed = await this.dialog.add(ConfirmationDialog, {
                title: _t("Currency Ref Payments Difference"),
                body: _t("Do you want to accept currency ref payments difference and post a profit/loss journal entry?"),
            });
            if (confirmed) {
                return super.confirm();
            }
        } else {
            await this.dialog.add(ConfirmationDialog, {
                title: _t("Currency Ref Payments Difference"),
                body: _.str.sprintf(
                    _t("The maximum difference by currency ref allowed is %s.\nContact your manager to accept."),
                    this.pos.format_currency_ref(this.props.amount_authorized_diff_ref)
                ),
            });
        }
    },

    openDetailsPopupUSD() {
        const ref_id = this.props.default_cash_details_ref?.id;
        if (!ref_id || !this.state.payments_usd[ref_id]) return;

        const action = _t("Cash control USD - closing");
        this.dialog.add(MoneyDetailsPopupUSD, {
            moneyDetails: this.moneyDetailsUSD || null,
            action: action,
            getPayload: (payload) => {
                if (payload) {
                    const { total, moneyDetailsNotes, moneyDetails } = payload;
                    const formattedTotal = this.env.utils.formatCurrency(total, false);
                    this.state.payments_usd[ref_id].counted = formattedTotal;
                    this.state.payments_usd[ref_id].difference =
                        Math.round((total - this.props.default_cash_details_ref.amount) * 10000) / 10000;
                    
                    if (this.state.payments[ref_id]) {
                        this.state.payments[ref_id].counted = formattedTotal;
                    }

                    if (moneyDetailsNotes) {
                        this.state.notes = (this.state.notes ? this.state.notes + "\n" : "") + moneyDetailsNotes;
                    }
                    this.moneyDetailsUSD = moneyDetails;
                }
            },
            context: "Closing USD",
        });
    },

    handleInputChangeUSD(paymentId) {
        const ref_id = this.props.default_cash_details_ref?.id;
        if (!this.state.payments_usd || !this.state.payments_usd[paymentId]) return;

        let expectedAmount = 0;
        if (paymentId === ref_id) {
            this.manualInputCashCountUSD = true;
            expectedAmount = this.props.default_cash_details_ref.amount;
        } else {
            expectedAmount = this.props.non_cash_payment_methods.find(pm => paymentId === pm.id)?.amount || 0;
        }
        
        const rawCounted = this.state.payments_usd[paymentId].counted;
        const parsedCounted = this.env.utils.isValidFloat(rawCounted) ? parseFloat(rawCounted) : 0;

        this.state.payments_usd[paymentId].difference =
            Math.round((parsedCounted - expectedAmount) * 10000) / 10000;

        if (this.state.payments[paymentId]) {
            this.state.payments[paymentId].counted = rawCounted.toString();
        }
    },

    getDifference(paymentId) {
        const ref_id = this.props.default_cash_details_ref?.id;
        if (ref_id && paymentId === ref_id) {
            if (!this.state.payments_usd || !this.state.payments_usd[paymentId]) {
                return 0;
            }
            return this.state.payments_usd[paymentId].difference;
        }
        return super.getDifference(paymentId);
    },

    hasDifferenceUSD() {
        if (!this.state.payments_usd) return false;
        return Object.entries(this.state.payments_usd).find(pm => pm[1].difference != 0);
    },

    hasUserAuthorityUSD() {
        if (!this.state.payments_usd) return true;
        const absDifferences = Object.entries(this.state.payments_usd).map(pm => Math.abs(pm[1].difference));
        const maxDiff = absDifferences.length ? Math.max(...absDifferences) : 0;
        return this.pos.get_cashier().role === 'manager' || this.props.amount_authorized_diff_ref == null || maxDiff <= this.props.amount_authorized_diff_ref;
    },

    async closeSession() {
        if (!this.closeSessionClicked) {
            this.closeSessionClicked = true;
            const ref_id = this.props.default_cash_details_ref?.id;
            const sessionId = this.pos.pos_session?.id || this.pos.session?.id;
            if (this.pos.config.cash_control && ref_id && this.state.payments_usd && this.state.payments_usd[ref_id]) {
                const rawCounted = this.state.payments_usd[ref_id].counted;
                const parsedCounted = this.env.utils.isValidFloat(rawCounted) ? parseFloat(rawCounted) : 0;
                const response = await this.pos.data.call('pos.session', 'post_closing_cash_details_ref', [
                    [sessionId]
                ], {
                    counted_cash: parsedCounted,
                });
                if (response && !response.successful) {
                    this.closeSessionClicked = false;
                    return this.handleClosingError(response);
                }
            }
            await this.pos.data.call('pos.session', 'update_closing_control_state_session_ref', [
                [sessionId],
                this.state.notes
            ]);
            this.closeSessionClicked = false;
        }
        super.closeSession();
    }
});
