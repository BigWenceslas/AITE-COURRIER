#!/bin/bash
# ---------------------------------------------------------------------------
# Campagne protocolaire WebDAV — AITE ECM
# Cas SC-11.2 à SC-11.25 du dossier de recette docs/uat/DOSSIER_UAT.md
#
#   bash docs/uat/scripts/campagne_webdav.sh
#   BASE_URL=http://serveur:8069 bash docs/uat/scripts/campagne_webdav.sh
#
# Prérequis : jeu de données de recette chargé (aite_ecm_demo + seed_demo.py)
#             et serveur démarré avec une base unique résolvable
#             (db_name dans odoo.conf, ou --db-filter).
#
# Le script est idempotent : le document d'essai part en corbeille au dernier
# cas, on peut donc l'enchaîner sans réinitialiser la base.
# Résultat attendu : TOTAL : 32 réussis, 0 échoués
# (24 références SC-11.2 à SC-11.25, SC-11.6 comptant pour 9 exécutions)
# ---------------------------------------------------------------------------
set -u

BASE_URL="${BASE_URL:-http://localhost:8169}"
ADMIN="${ADMIN:-demo.admin:demo1234}"
AGENT="${AGENT:-demo.agent1:demo1234}"
U="$BASE_URL/webdav/aite_ecm"
CT="-H Content-Type:application/octet-stream"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

enc() { python3 -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))" "$1"; }
code() { curl -sS -o "$TMP/body" -w "%{http_code}" --max-time 40 "$@"; }

P=0; F=0
chk() {
  if [ "$2" = "$3" ]; then
    echo "  PASS  $1 (HTTP $3)"; P=$((P + 1))
  else
    echo "  FAIL  $1 — attendu $2, obtenu $3"; F=$((F + 1))
  fi
}

printf 'PK\x03\x04 UAT v1 contenu' > "$TMP/f1.docx"
printf 'PK\x03\x04 UAT v2 contenu modifie' > "$TMP/f2.docx"
DOC="Juridique et contrats/campagne-uat.docx"
NEW="Juridique et contrats/UAT-campagne/campagne-uat-renomme.docx"

echo "== A. Découverte et authentification =="
chk "SC-11.2  OPTIONS"                200 "$(code -X OPTIONS -u "$ADMIN" "$U")"
chk "SC-11.3  PROPFIND sans identifiants"  401 "$(code -X PROPFIND -H 'Depth: 0' "$U")"
chk "SC-11.4  PROPFIND mot de passe erroné" 401 "$(code -X PROPFIND -H 'Depth: 0' -u 'demo.admin:faux' "$U")"

echo "== B. Navigation dans le plan de classement =="
chk "SC-11.5  PROPFIND racine Depth:1" 207 "$(code -X PROPFIND -H 'Depth: 1' -u "$ADMIN" "$U")"
for d in "Juridique et contrats" "Achats et fournisseurs" "Finance et comptabilité" \
         "Qualité et procédures" "Ressources humaines" "Direction générale" \
         "Archives et éliminations" "Courrier" "Sans classement"; do
  chk "SC-11.6  PROPFIND « $d »" 207 "$(code -X PROPFIND -H 'Depth: 1' -u "$ADMIN" "$U/$(enc "$d")")"
done
chk "SC-11.7  PROPFIND dossier inexistant" 404 "$(code -X PROPFIND -H 'Depth: 1' -u "$ADMIN" "$U/Inexistant")"

echo "== C. Dépôt d'un fichier neuf et relecture =="
chk "SC-11.8  PUT création"  201 "$(code -X PUT -u "$ADMIN" $CT --data-binary @"$TMP/f1.docx" "$U/$(enc "$DOC")")"
chk "SC-11.9  GET au même chemin" 200 "$(code -u "$ADMIN" "$U/$(enc "$DOC")")"
echo "        contenu relu : $(tr -d '\0' < "$TMP/body" | tail -c 20)"
chk "SC-11.10 PUT nouvelle version (sans doublon)" 204 "$(code -X PUT -u "$ADMIN" $CT --data-binary @"$TMP/f2.docx" "$U/$(enc "$DOC")")"
chk "SC-11.11 GET relit la v2" 200 "$(code -u "$ADMIN" "$U/$(enc "$DOC")")"
echo "        contenu relu : $(tr -d '\0' < "$TMP/body" | tail -c 20)"
chk "SC-11.12 HEAD annonce la taille" 200 "$(code -I -u "$ADMIN" "$U/$(enc "$DOC")")"
echo "        $(curl -sS -I -u "$ADMIN" --max-time 40 "$U/$(enc "$DOC")" | grep -i content-length | tr -d '\r')"
chk "SC-11.13 corps illisible refusé" 415 "$(code -X PUT -u "$ADMIN" --data-binary @"$TMP/f1.docx" "$U/$(enc 'Sans classement/forme-uat.docx')")"
chk "SC-11.14 fichier temporaire ~\$" 403 "$(code -X PUT -u "$ADMIN" $CT --data-binary @"$TMP/f1.docx" "$U/$(enc 'Juridique et contrats/~$tmp.docx')")"
chk "SC-11.15 fichier .tmp" 403 "$(code -X PUT -u "$ADMIN" $CT --data-binary @"$TMP/f1.docx" "$U/$(enc 'Juridique et contrats/x.tmp')")"

echo "== D. Verrous collaboratifs =="
chk "SC-11.16 LOCK" 200 "$(code -X LOCK -u "$ADMIN" -H 'Timeout: Second-3600' "$U/$(enc "$DOC")")"
chk "SC-11.17 écriture d'un collègue refusée" 423 "$(code -X PUT -u "$AGENT" $CT --data-binary @"$TMP/f1.docx" "$U/$(enc "$DOC")")"
chk "SC-11.18 UNLOCK" 204 "$(code -X UNLOCK -u "$ADMIN" "$U/$(enc "$DOC")")"
chk "SC-11.19 le collègue peut écrire" 204 "$(code -X PUT -u "$AGENT" $CT --data-binary @"$TMP/f2.docx" "$U/$(enc "$DOC")")"

echo "== E. Classement =="
chk "SC-11.20 MKCOL" 201 "$(code -X MKCOL -u "$ADMIN" "$U/$(enc 'Juridique et contrats/UAT-campagne')")"
chk "SC-11.21 MOVE" 201 "$(code -X MOVE -u "$ADMIN" -H "Destination: $U/$(enc "$NEW")" "$U/$(enc "$DOC")")"
chk "SC-11.22 GET au nouvel emplacement" 200 "$(code -u "$ADMIN" "$U/$(enc "$NEW")")"
chk "SC-11.23 DELETE (corbeille)" 204 "$(code -X DELETE -u "$ADMIN" "$U/$(enc "$NEW")")"

echo "== F. Divers =="
chk "SC-11.24 COPY refusé" 403 "$(code -X COPY -u "$ADMIN" -H "Destination: $U/x" "$U/$(enc 'Juridique et contrats')")"
chk "SC-11.25 PROPPATCH acquitté" 207 "$(code -X PROPPATCH -u "$ADMIN" "$U/$(enc 'Juridique et contrats')")"

echo
echo "TOTAL : $P réussis, $F échoués"
[ "$F" -eq 0 ]
