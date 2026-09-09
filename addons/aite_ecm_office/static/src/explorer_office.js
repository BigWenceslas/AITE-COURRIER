/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { EcmExplorer } from "@aite_ecm_document/explorer/explorer";

patch(EcmExplorer.prototype, {
    async openOffice(rec, libre = false) {
        const method = libre ? "action_open_libreoffice" : "action_open_office";
        const action = await this.orm.call("aite.ecm.document", method, [[rec.id]]);
        if (action) {
            await this.action.doAction(action);
            await this.refreshAll();
        }
    },
    async openGoogle(rec) {
        const action = await this.orm.call("aite.ecm.document", "action_open_google", [[rec.id]]);
        if (action) {
            await this.action.doAction(action);
            await this.refreshAll();
        }
    },
    async googlePull(rec) {
        await this.orm.call("aite.ecm.document", "action_google_pull", [[rec.id]]);
        await this.refreshAll();
    },
    async googleFinish(rec) {
        await this.orm.call("aite.ecm.document", "action_google_finish", [[rec.id]]);
        await this.refreshAll();
    },
});
