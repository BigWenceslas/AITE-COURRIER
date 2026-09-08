# -*- coding: utf-8 -*-
import base64
import io
import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Dépendances OPTIONNELLES — la solution reste installable et fonctionnelle
# sans elles : l'extraction du texte natif des PDF (pypdf, livré avec Odoo)
# couvre déjà les documents bureautiques ; l'OCR n'est qu'un repli pour les
# scans et images.
# ---------------------------------------------------------------------------
try:  # lecteur PDF embarqué avec Odoo (pypdf, anciennement PyPDF2)
    from pypdf import PdfReader
except ImportError:
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        PdfReader = None

try:
    import pytesseract
except ImportError:
    pytesseract = None

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    from pdf2image import convert_from_bytes
except ImportError:
    convert_from_bytes = None

# Longueur en dessous de laquelle une couche texte PDF est considérée vide
# (page scannée) et déclenche le repli OCR.
_MIN_NATIVE_TEXT_LEN = 40
# Taille maximale du texte injecté dans index_content (garde-fou).
_MAX_INDEX_LEN = 200_000


class AiteCourrierDocumentVersion(models.Model):
    """Extraction du texte des versions (indexation plein texte).

    Le traitement est **asynchrone** : la création d'une version PDF/image la
    place en file (« pending ») ; le cron :meth:`_cron_process_ocr` traite par
    lots. Le texte extrait est stocké sur la version (``ocr_text``) et
    recopié dans ``ir.attachment.index_content`` pour bénéficier de la
    recherche native d'Odoo.
    """

    _inherit = 'aite.courrier.document.version'

    OCR_EXTENSIONS = ('pdf', 'jpg', 'jpeg', 'png', 'tif', 'tiff')

    ocr_state = fields.Selection(
        selection=[
            ('none', "Non concerné"),
            ('pending', "En attente"),
            ('done', "Indexé"),
            ('error', "Erreur"),
        ],
        string="Indexation", default='none', copy=False, index=True,
        help="État de l'extraction plein texte de cette version.",
    )
    ocr_text = fields.Text(
        string="Texte extrait", copy=False,
        help="Contenu textuel extrait de la pièce (couche texte PDF ou OCR).",
    )
    ocr_date = fields.Datetime(string="Indexé le", copy=False, readonly=True)

    # ------------------------------------------------------------------ #
    # Mise en file à la création
    # ------------------------------------------------------------------ #
    @api.model_create_multi
    def create(self, vals_list):
        versions = super().create(vals_list)
        to_queue = versions.filtered(
            lambda v: (v.file_extension or '') in self.OCR_EXTENSIONS)
        if to_queue:
            to_queue.write({'ocr_state': 'pending'})
        return versions

    def action_reprocess_ocr(self):
        """Bouton UI : remet la version en file d'indexation."""
        self.write({'ocr_state': 'pending', 'ocr_text': False})
        return True

    # ------------------------------------------------------------------ #
    # Cron de traitement par lots
    # ------------------------------------------------------------------ #
    @api.model
    def _cron_process_ocr(self, limit=20):
        """Traite les versions en attente d'indexation (lot de ``limit``)."""
        pending = self.sudo().search(
            [('ocr_state', '=', 'pending')], limit=limit, order='id')
        for version in pending:
            version._process_ocr()
        return True

    def _process_ocr(self):
        """Extrait le texte d'UNE version et met à jour son état.

        Toute erreur est absorbée (état « error » + audit) : l'indexation ne
        doit jamais interrompre le cron ni bloquer un utilisateur.
        """
        self.ensure_one()
        attachment = self.attachment_id.sudo()
        try:
            raw = base64.b64decode(attachment.datas or b'')
            text = self._extract_text(raw) or ''
            self.sudo().write({
                'ocr_text': text,
                'ocr_state': 'done',
                'ocr_date': fields.Datetime.now(),
            })
            if text:
                attachment.write({'index_content': text[:_MAX_INDEX_LEN]})
        except Exception as exc:  # noqa: BLE001 — robustesse du cron
            _logger.warning("OCR en échec sur la version %s : %s",
                            self.id, exc)
            self.sudo().write({'ocr_state': 'error'})
            self.env['aite.courrier.audit.log']._log(
                self.env, _("Échec indexation OCR"), 'err',
                'aite.courrier.document', self.document_id.id,
                self.document_id.name,
                _("%s — %s") % (self.version, exc), 'system')
        return True

    # ------------------------------------------------------------------ #
    # Extraction
    # ------------------------------------------------------------------ #
    def _extract_text(self, raw):
        self.ensure_one()
        extension = self.file_extension or ''
        if extension == 'pdf':
            return self._extract_pdf_text(raw)
        if extension in ('jpg', 'jpeg', 'png', 'tif', 'tiff'):
            return self._ocr_image(raw)
        return ''

    @api.model
    def _extract_pdf_text(self, raw):
        """Texte d'un PDF : couche native d'abord, OCR en repli.

        La couche texte (pypdf) couvre les PDF bureautiques sans dépendance
        externe. Si elle est vide/insignifiante (scan), on tente l'OCR
        Tesseract page à page (nombre de pages plafonné par le paramètre
        ``aite_courrier.ocr_max_pages``).
        """
        text = ''
        if PdfReader is not None:
            try:
                reader = PdfReader(io.BytesIO(raw))
                pages = [(page.extract_text() or '') for page in reader.pages]
                text = '\n'.join(pages).strip()
            except Exception as exc:  # PDF corrompu / chiffré
                _logger.info("Lecture pypdf impossible : %s", exc)
        if len(text) >= _MIN_NATIVE_TEXT_LEN:
            return text
        ocr = self._ocr_pdf(raw)
        return ocr if len(ocr) > len(text) else text

    @api.model
    def _ocr_pdf(self, raw):
        """OCR d'un PDF scanné via pdf2image + Tesseract (si disponibles)."""
        if not (pytesseract and convert_from_bytes):
            return ''
        max_pages = int(self.env['ir.config_parameter'].sudo().get_param(
            'aite_courrier.ocr_max_pages', 10))
        try:
            images = convert_from_bytes(
                raw, dpi=200, first_page=1, last_page=max_pages)
            chunks = [pytesseract.image_to_string(image, lang='fra+eng')
                      for image in images]
            return '\n'.join(chunks).strip()
        except Exception as exc:  # binaires absents (poppler/tesseract)…
            _logger.info("OCR PDF indisponible : %s", exc)
            return ''

    @api.model
    def _ocr_image(self, raw):
        """OCR d'une image via Pillow + Tesseract (si disponibles)."""
        if not (pytesseract and Image):
            return ''
        try:
            image = Image.open(io.BytesIO(raw))
            return (pytesseract.image_to_string(image, lang='fra+eng')
                    or '').strip()
        except Exception as exc:
            _logger.info("OCR image indisponible : %s", exc)
            return ''
