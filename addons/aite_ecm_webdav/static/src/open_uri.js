/** @odoo-module **/

import { registry } from "@web/core/registry";

/**
 * Confie au navigateur, telle quelle, une URI de protocole applicatif
 * (``ms-word:``, ``ms-excel:``, ``vnd.libreoffice.command:``…).
 *
 * ``ir.actions.act_url`` ne convient pas à ces adresses : le client web les
 * traite comme des URL ordinaires et les normalise — les barres verticales
 * deviennent ``%7C``, le ``//`` du schéma imbriqué se réduit à ``/``. Le
 * navigateur ne reconnaît alors plus le protocole, résout l'adresse comme un
 * chemin relatif d'Odoo, et affiche un 404 sans jamais lancer l'application.
 *
 * L'explorateur ECM procède déjà ainsi ; cette action fait de même pour les
 * boutons de la fiche document.
 */
export function openProtocolUri(env, action) {
    const uri = action.params && action.params.uri;
    if (uri) {
        window.location.assign(uri);
    }
}

registry.category("actions").add("aite_ecm_open_uri", openProtocolUri);
