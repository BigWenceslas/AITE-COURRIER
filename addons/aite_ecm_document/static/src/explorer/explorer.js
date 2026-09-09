/** @odoo-module **/

import { Component, onWillStart, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { useDebounced } from "@web/core/utils/timing";
import { EcmPreviewDialog } from "./preview_dialog";
import { renderPdfThumbnail } from "./pdf_thumbnail";

const PAGE = 60;
const ICONS = {
    pdf: "fa-file-pdf-o",
    doc: "fa-file-word-o", docx: "fa-file-word-o", odt: "fa-file-word-o", rtf: "fa-file-word-o",
    xls: "fa-file-excel-o", xlsx: "fa-file-excel-o", ods: "fa-file-excel-o", csv: "fa-file-excel-o",
    ppt: "fa-file-powerpoint-o", pptx: "fa-file-powerpoint-o", odp: "fa-file-powerpoint-o",
    jpg: "fa-file-image-o", jpeg: "fa-file-image-o", png: "fa-file-image-o", gif: "fa-file-image-o",
    tif: "fa-file-image-o", tiff: "fa-file-image-o",
    zip: "fa-file-archive-o", eml: "fa-envelope-o", msg: "fa-envelope-o",
    txt: "fa-file-text-o", xml: "fa-file-code-o", json: "fa-file-code-o",
};

export class EcmExplorer extends Component {
    static template = "aite_ecm_document.Explorer";
    static props = { "*": true };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.fileInput = useRef("fileInput");
        this.versionInput = useRef("versionInput");
        this.scanInput = useRef("scanInput");
        this.state = useState({
            meta: null,
            records: [],
            total: 0,
            loading: true,
            uploading: 0,
            search: "",
            folderId: (this.props.action && this.props.action.context && this.props.action.context.ecm_folder_id) || false,
            tagIds: [],
            typeId: false,
            resModel: false,
            stateFilter: false,
            mine: false,
            checkedOut: false,
            trash: false,
            order: "date",
            view: "grid",
            selected: {},
            expanded: {},
            dragging: false,
            newFolderName: "",
            creatingFolder: false,
        });
        this.debouncedReload = useDebounced(() => this.reload(), 300);
        this.thumbQueue = new Set();
        onWillStart(async () => {
            await this.loadMeta();
            await this.reload();
        });
    }

    // ------------------------------------------------------------------ //
    // Chargement
    // ------------------------------------------------------------------ //
    async loadMeta() {
        this.state.meta = await this.orm.call("aite.ecm.document", "explorer_meta", []);
        this.folderTree = this.buildTree(this.state.meta.folders);
        const expanded = {};
        for (const f of this.state.meta.folders) {
            if (!f.parent_id) {
                expanded[f.id] = true;
            }
        }
        for (const id of this.ancestorsOf(this.state.folderId)) {
            expanded[id] = true;
        }
        this.state.expanded = Object.assign(expanded, this.state.expanded);
    }

    buildTree(folders) {
        const byId = {};
        for (const f of folders) {
            byId[f.id] = Object.assign({ children: [], subtotal: 0 }, f);
        }
        const roots = [];
        for (const f of Object.values(byId)) {
            if (f.parent_id && byId[f.parent_id]) {
                byId[f.parent_id].children.push(f);
            } else {
                roots.push(f);
            }
        }
        const compute = (node) => {
            node.subtotal = node.count + node.children.reduce((s, c) => s + compute(c), 0);
            return node.subtotal;
        };
        roots.forEach(compute);
        this.foldersById = byId;
        return roots;
    }

    ancestorsOf(folderId) {
        const ids = [];
        let current = folderId && this.foldersById && this.foldersById[folderId];
        while (current && current.parent_id) {
            ids.push(current.parent_id);
            current = this.foldersById[current.parent_id];
        }
        return ids;
    }

    get searchParams() {
        return {
            folder_id: this.state.folderId,
            include_sub: true,
            tag_ids: this.state.tagIds,
            type_id: this.state.typeId,
            res_model: this.state.resModel,
            state: this.state.stateFilter,
            mine: this.state.mine,
            checked_out: this.state.checkedOut,
            search: this.state.search,
            order: this.state.order,
            trash: this.state.trash,
            limit: PAGE,
        };
    }

    async reload(append = false) {
        this.state.loading = true;
        const params = Object.assign({}, this.searchParams, {
            offset: append ? this.state.records.length : 0,
        });
        try {
            const res = await this.orm.call("aite.ecm.document", "explorer_search", [params]);
            this.state.records = append ? this.state.records.concat(res.records) : res.records;
            this.state.total = res.total;
            if (!append) {
                this.state.selected = {};
            }
        } finally {
            this.state.loading = false;
        }
        this.scheduleThumbnails();
    }

    async refreshAll() {
        await this.loadMeta();
        await this.reload();
    }

    // ------------------------------------------------------------------ //
    // Vignettes PDF (générées par le navigateur, comme l'app Documents)
    // ------------------------------------------------------------------ //
    scheduleThumbnails() {
        for (const rec of this.state.records) {
            if (rec.thumbnail_status === "client" && rec.attachment_id && !this.thumbQueue.has(rec.id)) {
                this.thumbQueue.add(rec.id);
                this.generateThumbnail(rec);
            }
        }
    }

    async generateThumbnail(rec) {
        try {
            const b64 = await renderPdfThumbnail(`/web/content/${rec.attachment_id}?download=false`);
            await this.orm.call("aite.ecm.document", "explorer_set_thumbnail", [rec.id, b64]);
            rec.thumbnail_url = `data:image/jpeg;base64,${b64}`;
            rec.thumbnail_status = "present";
        } catch (e) {
            rec.thumbnail_status = "error";
        }
    }

    // ------------------------------------------------------------------ //
    // Facettes
    // ------------------------------------------------------------------ //
    selectFolder(folderId) {
        this.state.folderId = folderId;
        this.state.trash = false;
        if (folderId && this.foldersById[folderId]) {
            this.state.expanded[folderId] = true;
        }
        this.reload();
    }

    toggleExpand(folderId, ev) {
        ev.stopPropagation();
        this.state.expanded[folderId] = !this.state.expanded[folderId];
    }

    toggleTag(tagId) {
        const idx = this.state.tagIds.indexOf(tagId);
        if (idx >= 0) {
            this.state.tagIds.splice(idx, 1);
        } else {
            this.state.tagIds.push(tagId);
        }
        this.reload();
    }

    setType(typeId) {
        this.state.typeId = this.state.typeId === typeId ? false : typeId;
        this.reload();
    }

    setResModel(model) {
        this.state.resModel = this.state.resModel === model ? false : model;
        this.reload();
    }

    setStateFilter(key) {
        this.state.stateFilter = this.state.stateFilter === key ? false : key;
        this.state.trash = false;
        this.reload();
    }

    toggleMine() {
        this.state.mine = !this.state.mine;
        this.reload();
    }

    toggleCheckedOut() {
        this.state.checkedOut = !this.state.checkedOut;
        this.reload();
    }

    showTrash() {
        this.state.trash = !this.state.trash;
        this.state.stateFilter = false;
        this.reload();
    }

    onSearchInput(ev) {
        this.state.search = ev.target.value;
        this.debouncedReload();
    }

    setOrder(ev) {
        this.state.order = ev.target.value;
        this.reload();
    }

    clearFilters() {
        Object.assign(this.state, {
            folderId: false, tagIds: [], typeId: false, resModel: false, stateFilter: false,
            mine: false, checkedOut: false, trash: false, search: "",
        });
        this.reload();
    }

    get activeFilterCount() {
        const s = this.state;
        return (s.folderId ? 1 : 0) + s.tagIds.length + (s.typeId ? 1 : 0) + (s.resModel ? 1 : 0)
            + (s.stateFilter ? 1 : 0) + (s.mine ? 1 : 0) + (s.checkedOut ? 1 : 0) + (s.trash ? 1 : 0);
    }

    get currentFolder() {
        return this.state.folderId && this.foldersById ? this.foldersById[this.state.folderId] : null;
    }

    get breadcrumb() {
        const parts = [];
        let current = this.currentFolder;
        while (current) {
            parts.unshift(current);
            current = current.parent_id ? this.foldersById[current.parent_id] : null;
        }
        return parts;
    }

    get canUploadHere() {
        if (this.state.trash) {
            return false;
        }
        return !this.currentFolder || this.currentFolder.can_write;
    }

    // ------------------------------------------------------------------ //
    // Sélection
    // ------------------------------------------------------------------ //
    isSelected(rec) {
        return !!this.state.selected[rec.id];
    }

    toggleSelect(rec, ev) {
        if (ev) {
            ev.stopPropagation();
        }
        if (this.state.selected[rec.id]) {
            delete this.state.selected[rec.id];
        } else {
            this.state.selected[rec.id] = true;
        }
    }

    selectOnly(rec) {
        this.state.selected = { [rec.id]: true };
    }

    selectAll() {
        const all = {};
        for (const rec of this.state.records) {
            all[rec.id] = true;
        }
        this.state.selected = Object.keys(all).length === Object.keys(this.state.selected).length ? {} : all;
    }

    get selectedRecords() {
        return this.state.records.filter((r) => this.state.selected[r.id]);
    }

    get selectedIds() {
        return this.selectedRecords.map((r) => r.id);
    }

    get inspected() {
        const recs = this.selectedRecords;
        return recs.length === 1 ? recs[0] : null;
    }

    // ------------------------------------------------------------------ //
    // Affichage
    // ------------------------------------------------------------------ //
    iconFor(rec) {
        return ICONS[rec.file_extension] || "fa-file-o";
    }

    formatSize(bytes) {
        if (!bytes) {
            return "";
        }
        if (bytes > 1024 * 1024) {
            return (bytes / 1024 / 1024).toFixed(1) + " Mo";
        }
        return Math.max(1, Math.round(bytes / 1024)) + " Ko";
    }

    formatDate(value) {
        if (!value) {
            return "";
        }
        const d = new Date(value.replace(" ", "T") + "Z");
        return d.toLocaleDateString();
    }

    stateClass(rec) {
        return { draft: "text-bg-secondary", final: "text-bg-success", archived: "text-bg-dark" }[rec.state] || "text-bg-secondary";
    }

    // ------------------------------------------------------------------ //
    // Actions sur les documents
    // ------------------------------------------------------------------ //
    openRecord(rec) {
        this.action.doAction({
            type: "ir.actions.act_window", res_model: "aite.ecm.document", res_id: rec.id,
            views: [[false, "form"]], target: "current",
        });
    }

    newDocument() {
        this.action.doAction({
            type: "ir.actions.act_window", res_model: "aite.ecm.document",
            views: [[false, "form"]], target: "current",
            context: { default_folder_id: this.state.folderId || false, default_type_id: this.state.typeId || false },
        });
    }

    preview(rec) {
        if (!rec.attachment_id) {
            this.notification.add(_t("Ce document n'a pas encore de fichier."), { type: "warning" });
            return;
        }
        this.dialog.add(EcmPreviewDialog, { doc: rec });
    }

    download(rec) {
        if (rec.attachment_id) {
            window.open(`/web/content/${rec.attachment_id}?download=true`, "_blank");
        }
    }

    async bulk(actionName, ids, params = {}) {
        ids = ids || this.selectedIds;
        if (!ids.length) {
            return;
        }
        const res = await this.orm.call("aite.ecm.document", "explorer_bulk", [actionName, ids, params]);
        if (res.errors.length) {
            for (const err of res.errors) {
                this.notification.add(`${err.reference || ""} — ${err.message}`, { type: "danger", sticky: true });
            }
        }
        if (res.done) {
            this.notification.add(_t("%s document(s) traité(s).", res.done), { type: "success" });
        }
        await this.refreshAll();
    }

    async share(rec) {
        const action = await this.orm.call("aite.ecm.document", "explorer_share", [rec.id]);
        if (!action) {
            this.notification.add(_t("Le module de partage sécurisé (aite_ecm_share) n'est pas installé."), { type: "warning" });
            return;
        }
        await this.action.doAction(action, { onClose: () => this.reload() });
    }

    async shareSelection(ev, mode) {
        const userId = ev.target.value ? parseInt(ev.target.value) : false;
        ev.target.value = "";
        if (userId) {
            await this.bulk(mode === "write" ? "share_write" : "share_read", null, { user_ids: [userId] });
        }
    }

    async extraAction(rec, action) {
        if (action.kind === "url") {
            if (action.url.startsWith("http")) {
                window.open(action.url, "_blank");
            } else {
                window.location.href = action.url;      // schéma d'application (ms-word:…)
            }
            return;
        }
        const result = await this.orm.call("aite.ecm.document", "explorer_call", [rec.id, action.method]);
        if (result && typeof result === "object" && result.type) {
            await this.action.doAction(result, { onClose: () => this.refreshAll() });
        } else {
            await this.refreshAll();
        }
    }

    async wfWizard(rec) {
        const action = await this.orm.call("aite.ecm.document", "explorer_wf_wizard", [rec.id]);
        if (!action) {
            this.notification.add(_t("Le module de circuits ECM (aite_ecm_workflow) n'est pas installé."), { type: "warning" });
            return;
        }
        await this.action.doAction(action, { onClose: () => this.refreshAll() });
    }

    async moveSelection(ev) {
        const folderId = ev.target.value ? parseInt(ev.target.value) : false;
        ev.target.value = "";
        if (folderId === false && !ev.target.dataset.allowRoot) {
            return;
        }
        await this.bulk("move", null, { folder_id: folderId });
    }

    async tagSelection(ev) {
        const tagId = ev.target.value ? parseInt(ev.target.value) : false;
        ev.target.value = "";
        if (tagId) {
            await this.bulk("tag", null, { tag_ids: [tagId] });
        }
    }

    async setTypeSelection(ev) {
        const typeId = ev.target.value ? parseInt(ev.target.value) : false;
        ev.target.value = "";
        await this.bulk("set_type", null, { type_id: typeId });
    }

    // ------------------------------------------------------------------ //
    // Dossiers
    // ------------------------------------------------------------------ //
    startNewFolder() {
        this.state.creatingFolder = true;
        this.state.newFolderName = "";
    }

    async confirmNewFolder() {
        const name = (this.state.newFolderName || "").trim();
        if (!name) {
            this.state.creatingFolder = false;
            return;
        }
        try {
            const folder = await this.orm.call("aite.ecm.document", "explorer_create_folder", [name, this.state.folderId || false]);
            this.state.creatingFolder = false;
            await this.loadMeta();
            this.selectFolder(folder.id);
        } catch (e) {
            this.state.creatingFolder = false;
            throw e;
        }
    }

    // ------------------------------------------------------------------ //
    // Dépôt de fichiers
    // ------------------------------------------------------------------ //
    triggerUpload() {
        this.fileInput.el.click();
    }

    triggerVersionUpload() {
        this.versionInput.el.click();
    }

    triggerScan() {
        this.scanInput.el.click();
    }

    async onScanPicked(ev) {
        const files = Array.from(ev.target.files || []);
        ev.target.value = "";
        await this.uploadFiles(files, null, true);
    }

    async onFilesPicked(ev) {
        const files = Array.from(ev.target.files || []);
        ev.target.value = "";
        await this.uploadFiles(files);
    }

    async onVersionPicked(ev) {
        const files = Array.from(ev.target.files || []);
        ev.target.value = "";
        if (files.length && this.inspected) {
            await this.uploadFiles([files[0]], this.inspected.id);
        }
    }

    onDragOver(ev) {
        ev.preventDefault();
        if (this.canUploadHere) {
            this.state.dragging = true;
        }
    }

    onDragLeave(ev) {
        if (!ev.currentTarget.contains(ev.relatedTarget)) {
            this.state.dragging = false;
        }
    }

    async onDrop(ev) {
        ev.preventDefault();
        this.state.dragging = false;
        if (!this.canUploadHere) {
            return;
        }
        const files = Array.from((ev.dataTransfer && ev.dataTransfer.files) || []);
        await this.uploadFiles(files);
    }

    async uploadFiles(files, documentId = null, scan = false) {
        if (!files.length) {
            return;
        }
        const form = new FormData();
        for (const file of files) {
            form.append("ufile", file, file.name);
        }
        form.append("folder_id", this.state.folderId || "");
        form.append("type_id", this.state.typeId || "");
        if (documentId) {
            form.append("document_id", documentId);
        }
        if (scan) {
            form.append("scan", "1");
        }
        form.append("csrf_token", (window.odoo && window.odoo.csrf_token) || "");
        this.state.uploading += files.length;
        try {
            const resp = await fetch("/ecm/explorer/upload", { method: "POST", body: form, credentials: "same-origin" });
            if (!resp.ok) {
                throw new Error(`HTTP ${resp.status}`);
            }
            const results = await resp.json();
            const ok = results.filter((r) => r.ok);
            for (const r of results.filter((r) => !r.ok)) {
                this.notification.add(`${r.name} — ${r.error}`, { type: "danger", sticky: true });
            }
            if (ok.length) {
                this.notification.add(
                    documentId ? _t("Nouvelle version %s ajoutée.", ok[0].version)
                        : scan ? _t("Numérisation enregistrée : %s", ok[0].reference)
                        : _t("%s fichier(s) déposé(s).", ok.length),
                    { type: "success" }
                );
            }
        } catch (e) {
            this.notification.add(_t("Dépôt impossible : %s", e.message || e), { type: "danger" });
        } finally {
            this.state.uploading -= files.length;
        }
        await this.refreshAll();
    }

    loadMore() {
        this.reload(true);
    }
}

registry.category("actions").add("aite_ecm_explorer", EcmExplorer);
