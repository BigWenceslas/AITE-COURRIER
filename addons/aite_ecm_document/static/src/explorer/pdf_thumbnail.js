/** @odoo-module **/

import { loadJS } from "@web/core/assets";

let pdfLibPromise = null;

/** Charge pdf.js livré avec Odoo (chemin classique, puis variante ESM). */
function loadPdfLib() {
    if (!pdfLibPromise) {
        pdfLibPromise = (async () => {
            try {
                await loadJS("/web/static/lib/pdfjs/build/pdf.js");
                const lib = window.pdfjsLib || window["pdfjs-dist/build/pdf"];
                if (lib) {
                    lib.GlobalWorkerOptions.workerSrc = "/web/static/lib/pdfjs/build/pdf.worker.js";
                    return lib;
                }
            } catch (e) {
                // variante ESM (pdf.js 4.x)
            }
            const lib = await import(/* webpackIgnore: true */ "/web/static/lib/pdfjs/build/pdf.mjs");
            lib.GlobalWorkerOptions.workerSrc = "/web/static/lib/pdfjs/build/pdf.worker.mjs";
            return lib;
        })();
    }
    return pdfLibPromise;
}

/**
 * Rend la première page d'un PDF en JPEG (base64 sans préfixe).
 * @param {string} url URL du PDF (ex. /web/content/<attachment>)
 * @param {number} width largeur cible en pixels
 */
export async function renderPdfThumbnail(url, width = 360) {
    const lib = await loadPdfLib();
    const pdf = await lib.getDocument({ url, withCredentials: true }).promise;
    try {
        const page = await pdf.getPage(1);
        const base = page.getViewport({ scale: 1 });
        const viewport = page.getViewport({ scale: width / base.width });
        const canvas = document.createElement("canvas");
        canvas.width = Math.ceil(viewport.width);
        canvas.height = Math.ceil(viewport.height);
        await page.render({ canvasContext: canvas.getContext("2d"), viewport }).promise;
        return canvas.toDataURL("image/jpeg", 0.82).split(",")[1];
    } finally {
        try {
            pdf.destroy();
        } catch (e) {
            // ignoré
        }
    }
}
