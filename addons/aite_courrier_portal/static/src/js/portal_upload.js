/** @odoo-module **/

/**
 * Dépôt de pièces jointes du portail : retour visuel sur la sélection.
 *
 * Le tiers choisit plusieurs fichiers d'un coup (ou les dépose par
 * glisser-déposer) et voit aussitôt ce qui partira — avec le format et la
 * taille contrôlés côté navigateur, pour ne pas découvrir un refus après
 * l'envoi. Le serveur refait les mêmes contrôles : celui-ci n'est qu'un
 * confort, jamais une garantie.
 */

const UNITS = ["o", "Ko", "Mo", "Go"];

function humanSize(bytes) {
    let value = bytes;
    let unit = 0;
    while (value >= 1024 && unit < UNITS.length - 1) {
        value /= 1024;
        unit += 1;
    }
    return `${value < 10 && unit > 0 ? value.toFixed(1) : Math.round(value)} ${UNITS[unit]}`;
}

function extensionOf(name) {
    const dot = name.lastIndexOf(".");
    return dot === -1 ? "" : name.slice(dot + 1).toLowerCase();
}

function setup(zone) {
    const input = zone.querySelector('input[type="file"]');
    const list = zone.parentElement.querySelector(".o_aite_filelist");
    if (!input || !list) {
        return;
    }
    const allowed = (zone.dataset.allowed || "")
        .split(",")
        .map((e) => e.trim().toLowerCase())
        .filter(Boolean);
    const maxBytes = parseInt(zone.dataset.maxMb || "0", 10) * 1024 * 1024;

    const render = () => {
        list.replaceChildren();
        for (const file of input.files) {
            const extension = extensionOf(file.name);
            const badFormat = allowed.length && !allowed.includes(extension);
            const badSize = maxBytes && file.size > maxBytes;

            const item = document.createElement("li");
            if (badFormat || badSize) {
                item.classList.add("o_aite_file_bad");
            }

            const icon = document.createElement("i");
            icon.className = badFormat || badSize ? "fa fa-exclamation-triangle" : "fa fa-file-o";
            item.appendChild(icon);

            const name = document.createElement("span");
            name.className = "o_aite_filename";
            name.textContent = file.name;
            item.appendChild(name);

            const size = document.createElement("span");
            size.className = "o_aite_filesize";
            if (badFormat) {
                size.textContent = `format .${extension || "?"} non accepté`;
            } else if (badSize) {
                size.textContent = `trop volumineux (${humanSize(file.size)})`;
            } else {
                size.textContent = humanSize(file.size);
            }
            item.appendChild(size);

            list.appendChild(item);
        }
    };

    input.addEventListener("change", render);

    // Glisser-déposer : l'input couvre déjà la zone, le navigateur alimente
    // donc `input.files` tout seul. Reste le retour visuel du survol.
    for (const event of ["dragenter", "dragover"]) {
        zone.addEventListener(event, () => zone.classList.add("o_aite_drop_over"));
    }
    for (const event of ["dragleave", "drop"]) {
        zone.addEventListener(event, () => zone.classList.remove("o_aite_drop_over"));
    }
}

function start() {
    document.querySelectorAll(".o_aite_drop").forEach(setup);
}

// Le module peut être évalué après le chargement du document : on ne peut
// pas se contenter d'attendre `DOMContentLoaded`, qui serait déjà passé.
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
} else {
    start();
}
