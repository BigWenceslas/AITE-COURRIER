/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { EcmExplorer } from "@aite_ecm_document/explorer/explorer";

patch(EcmExplorer.prototype, {
    /** Ouvre le document dans l'application de bureau (protocole Office / LibreOffice). */
    openDesktop(rec, uri) {
        if (!uri) {
            return;
        }
        window.location.assign(uri);
    },

    /** Édition dans le navigateur (Collabora / OnlyOffice). */
    editOnline(rec) {
        if (rec.wopi_edit_url) {
            window.open(rec.wopi_edit_url, "_blank");
        }
    },

    /** Google Docs : ouverture, rapatriement, fin d'édition (actions serveur). */
    async googleAction(rec, method) {
        const action = await this.orm.call("aite.ecm.document", method, [[rec.id]]);
        if (action && action.type) {
            await this.action.doAction(action, { onClose: () => this.refreshAll() });
        } else {
            await this.refreshAll();
        }
    },
});
