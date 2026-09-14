#!/bin/bash
# Base neuve + installation de toute la suite + tests de tous les modules AITE.
#
#   ./docs/recette/run_tests.sh [base] [journal]
#
# Variables : ODOO_BIN, ODOO_CONF, ODOO_PORT (par défaut 8269, pour ne pas
# entrer en conflit avec une instance en cours).
set -u

DB=${1:-aite_tests}
LOG=${2:-/tmp/aite_tests.log}
ODOO_BIN=${ODOO_BIN:-./odoo-bin}
ODOO_CONF=${ODOO_CONF:-odoo.conf}
ODOO_PORT=${ODOO_PORT:-8269}

MODULES="aite_courrier_base,aite_courrier_workflow,aite_courrier_core,\
aite_courrier_validation,aite_courrier_ged,aite_courrier_capture,\
aite_courrier_ocr,aite_courrier_reponse,aite_courrier_webdav,aite_courrier,\
aite_courrier_portal,aite_ecm_document,aite_ecm_workflow,aite_ecm_dossier,\
aite_ecm_share,aite_ecm_api,aite_courrier_ecm,aite_ecm_records,aite_ecm_sae,\
aite_ecm_webdav,aite_ecm_office,aite_ecm_nextcloud,\
aite_ecm_nextcloud_courrier,aite_ecm_demo,aite_ecm"
MODULES=$(echo "$MODULES" | tr -d '\\\n')
TAGS=$(echo "$MODULES" | tr ',' '\n' | sed 's|^|/|' | paste -sd,)

echo "Base   : $DB"
echo "Modules: $(echo "$MODULES" | awk -F, '{print NF}')"
echo "Journal: $LOG"

dropdb --if-exists "$DB" >/dev/null 2>&1

# shellcheck disable=SC2086 — ODOO_BIN peut contenir « python odoo-bin »
$ODOO_BIN -c "$ODOO_CONF" -d "$DB" --http-port="$ODOO_PORT" \
    --without-demo=all -i "$MODULES" \
    --test-enable --test-tags "$TAGS" --stop-after-init \
    --log-level=test > "$LOG" 2>&1
STATUS=$?

echo
grep 'odoo.tests.stats' "$LOG" | sed -E 's/^.*stats: //'
TOTAL=$(grep 'odoo.tests.stats' "$LOG" | grep -oE '[0-9]+ tests' \
        | grep -oE '[0-9]+' | paste -sd+ | bc)
FAILED=$(grep -cE '(ERROR|FAIL): (setUpClass|Test)' "$LOG")
echo
echo "Total : ${TOTAL:-0} test(s) — ${FAILED} en échec"
if [ "$FAILED" -gt 0 ]; then
    grep -E '(ERROR|FAIL): (setUpClass|Test)' "$LOG" \
        | sed -E 's/^[0-9-]+ [0-9:,]+ [0-9]+ //' | sort -u
fi
exit $STATUS
