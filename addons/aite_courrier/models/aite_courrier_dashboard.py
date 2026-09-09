# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AiteCourrier(models.Model):
    _inherit = 'aite.courrier'

    @api.model
    def get_dashboard_data(self):
        """Indicateurs agrégés pour la page tableau de bord (composant OWL).

        Réservé au pilotage (le menu est restreint aux rôles Manager / Audit /
        Administrateur). Renvoie des compteurs, des taux et des répartitions
        prêts à afficher.
        """
        Courrier = self.env['aite.courrier']
        now = fields.Datetime.now()
        month_start = fields.Date.context_today(self).replace(day=1)
        active_domain = [('state', 'in', ('nw', 'pr'))]
        overdue_domain = [('sla_deadline', '<', now),
                          ('state', 'not in', ('ar', 'rj'))]

        rejected = Courrier.search_count([('state', '=', 'rj')])
        archived = Courrier.search_count([('state', '=', 'ar')])
        closed = rejected + archived

        # Charge par étape (courriers en cours). Deux circuits peuvent avoir
        # des étapes homonymes : la clé est l'identifiant de l'étape, et le
        # libellé est complété par le circuit quand le nom est ambigu.
        by_step = []
        for step, count in Courrier._read_group(
                active_domain, ['current_step_id'], ['__count']):
            by_step.append({
                'id': step.id if step else 0,
                'label': step.name if step else "Sans étape",
                'circuit': step.circuit_id.name if step else '',
                'count': count,
            })
        seen = {}
        for row in by_step:
            seen[row['label']] = seen.get(row['label'], 0) + 1
        for row in by_step:
            if seen.get(row['label'], 0) > 1 and row['circuit']:
                row['label'] = "%s (%s)" % (row['label'], row['circuit'])
        by_step.sort(key=lambda r: r['count'], reverse=True)
        max_step = max((r['count'] for r in by_step), default=0)
        for row in by_step:
            row['pct'] = round(100.0 * row['count'] / max_step) if max_step else 0

        # Répartition par catégorie (tous courriers non brouillon).
        by_category = []
        cat_labels = dict(self._fields['category']._description_selection(self.env))
        for category, count in Courrier._read_group(
                [('state', '!=', 'draft')], ['category'], ['__count']):
            by_category.append({
                'key': category or 'none',
                'label': cat_labels.get(category, "Non défini") if category
                         else "Non défini",
                'count': count,
            })
        by_category.sort(key=lambda r: r['count'], reverse=True)

        # Délai moyen de traitement (courriers archivés) : création -> étape finale.
        durations = []
        for courrier in Courrier.search([('state', '=', 'ar')], limit=1000):
            final_hist = courrier.step_history_ids.filtered(
                lambda h: h.step_id.is_final and h.entered_date)[:1]
            if final_hist and courrier.create_date:
                delta = final_hist.entered_date - courrier.create_date
                durations.append(delta.total_seconds())
        avg_days = round(sum(durations) / len(durations) / 86400.0, 1) \
            if durations else 0.0

        return {
            'active': Courrier.search_count(active_domain),
            'overdue': Courrier.search_count(overdue_domain),
            'received_month': Courrier.search_count(
                [('date_received', '>=', month_start)]),
            'archived_month': Courrier.search_count(
                [('state', '=', 'ar'), ('write_date', '>=', month_start)]),
            'rejected': rejected,
            'reject_rate': round(100.0 * rejected / closed, 1) if closed else 0.0,
            'avg_days': avg_days,
            'by_step': by_step,
            'by_category': by_category,
            # Repères pour les domaines côté client.
            'now': fields.Datetime.to_string(now),
            'month_start': fields.Date.to_string(month_start),
        }
