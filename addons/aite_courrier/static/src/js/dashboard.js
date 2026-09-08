/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

export class AiteCourrierDashboard extends Component {
    static template = "aite_courrier.Dashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ data: null, loading: true });
        onWillStart(async () => {
            await this.load();
        });
    }

    async load() {
        this.state.loading = true;
        this.state.data = await this.orm.call("aite.courrier", "get_dashboard_data", []);
        this.state.loading = false;
    }

    _openList(domain, name) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: name,
            res_model: "aite.courrier",
            domain: domain,
            views: [
                [false, "list"],
                [false, "form"],
            ],
            target: "current",
        });
    }

    openActive() {
        this._openList([["state", "in", ["nw", "pr", "vl"]]], "Courriers en cours");
    }

    openOverdue() {
        this._openList(
            [
                ["sla_deadline", "<", this.state.data.now],
                ["state", "not in", ["ar", "rj"]],
            ],
            "Courriers en retard (SLA)"
        );
    }

    openReceivedMonth() {
        this._openList(
            [["date_received", ">=", this.state.data.month_start]],
            "Courriers reçus ce mois"
        );
    }

    openArchivedMonth() {
        this._openList(
            [["state", "=", "ar"], ["write_date", ">=", this.state.data.month_start]],
            "Courriers archivés ce mois"
        );
    }

    openRejected() {
        this._openList([["state", "=", "rj"]], "Courriers rejetés");
    }

    openAnalysis() {
        this.action.doAction("aite_courrier.action_courrier_analysis");
    }
}

registry.category("actions").add("aite_courrier_dashboard", AiteCourrierDashboard);
