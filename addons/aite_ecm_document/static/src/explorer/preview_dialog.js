/** @odoo-module **/

import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class EcmPreviewDialog extends Component {
    static template = "aite_ecm_document.PreviewDialog";
    static components = { Dialog };
    static props = {
        doc: Object,
        close: Function,
    };

    get contentUrl() {
        return `/web/content/${this.props.doc.attachment_id}?download=false`;
    }

    get downloadUrl() {
        return `/web/content/${this.props.doc.attachment_id}?download=true`;
    }

    get isPdf() {
        return this.props.doc.file_extension === "pdf";
    }

    get isImage() {
        return ["jpg", "jpeg", "png", "gif", "webp", "bmp"].includes(this.props.doc.file_extension);
    }

    get isText() {
        return ["txt", "csv", "xml", "json"].includes(this.props.doc.file_extension);
    }

    get pdfViewerUrl() {
        return `/web/static/lib/pdfjs/web/viewer.html?file=${encodeURIComponent(this.contentUrl)}`;
    }
}
