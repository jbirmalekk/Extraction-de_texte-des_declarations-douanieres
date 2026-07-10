"""
Parseur pour PDF douane à texte embarqué (layout TTN/SA digital).

Les valeurs sont regroupées en bloc vertical juste après les libellés
Exportateur / Importateur, sans grille visuelle comme le scan.
"""

from __future__ import annotations

import re
from typing import Any

_DATE_RE = re.compile(r"^\d{2}-\d{2}-\d{4}$")
_NUM_DECL_RE = re.compile(r"^\d{4,7}$")
_CODE_MATRICULE_RE = re.compile(r"^\d{6,8}[A-Z]$", re.IGNORECASE)
_CL_CODE_LINE_RE = re.compile(
    r"(\d{3,5})\s*:\s*([A-Z][A-Z0-9 &.\-]{4,80})",
    re.IGNORECASE,
)
_AUTH_KEY_RE = re.compile(r"\b([A-Z]\d{3}[A-Z]{2,4}\d[A-Z])\b")
_NDP_RE = re.compile(r"\b(\d{11})\b")


def _norm_lines(text: str) -> list[str]:
    out: list[str] = []
    for raw in (text or "").splitlines():
        line = re.sub(r"\s+", " ", raw).strip()
        if line:
            out.append(line)
    return out


def _find_party_value_block_start(lines: list[str]) -> int | None:
    for i in range(len(lines) - 1):
        a = re.sub(r"[^A-Za-z]", "", lines[i]).upper()
        b = re.sub(r"[^A-Za-z]", "", lines[i + 1]).upper()
        if a == "EXPORTATEUR" and b == "IMPORTATEUR":
            return i + 2
    return None


def _is_value_block_terminator(line: str) -> bool:
    up = line.upper()
    if up.startswith("CODE ") or "NDP" in up or "DESIGNATION" in up:
        return True
    if "المورد" in line or "المصدر" in line:
        return True
    if _NDP_RE.search(line) and len(line) <= 20:
        return True
    return False


def _collect_value_block(lines: list[str], start: int, *, max_lines: int = 48) -> list[str]:
    block: list[str] = []
    for line in lines[start : start + max_lines]:
        if _is_value_block_terminator(line):
            break
        block.append(line)
    return block


def _format_country_code_label(short: str, long_label: str) -> str:
    s = short.strip().upper()
    l = long_label.strip().upper().replace(".", "")
    if "TUNISIE" in l or s == "TN":
        return "TN TUNISIE"
    if "U.S.A" in long_label.upper() or l == "USA" or s == "US":
        return "US USA"
    return f"{s} {l.title()}"


def _parse_country_quad(block: list[str], idx: int) -> tuple[dict[str, str], int]:
    """4 pays en layout vertical: 4 codes courts puis 4 libellés."""
    if idx + 8 > len(block):
        return {}, idx
    shorts = [block[idx + j].strip() for j in range(4)]
    longs = [block[idx + 4 + j].strip() for j in range(4)]
    if not all(re.match(r"^[A-Z]{2}$", s) for s in shorts[:2]):
        return {}, idx
    if not any("TUNISIE" in l.upper() or "U.S" in l.upper() for l in longs):
        return {}, idx
    pairs = [_format_country_code_label(shorts[j], longs[j]) for j in range(4)]
    # Ordre bloc TTN digital: achat, provenance, 1ère dest., dest. finale
    return {
        "pays_achat": pairs[0],
        "pays_provenance": pairs[1],
        "pays_premiere_destination": pairs[2],
        "pays_destination_finale": pairs[3],
        "pays_destination": pairs[3],
    }, idx + 8


def parse_embedded_party_block(text: str) -> dict[str, Any]:
    lines = _norm_lines(text)
    start = _find_party_value_block_start(lines)
    if start is None:
        return {}

    block = _collect_value_block(lines, start)
    if len(block) < 8:
        return {}

    out: dict[str, Any] = {}
    i = 0

    # Importateur (étranger) — premières lignes du bloc
    if i < len(block) and not _DATE_RE.match(block[i]) and not _NUM_DECL_RE.match(block[i]):
        if len(block[i]) >= 3 and block[i].upper() not in {"SA", "EXW", "USD"}:
            out["importateur_nom"] = block[i].strip()
            out["importateur"] = out["importateur_nom"]
            i += 1
    if i < len(block) and re.match(r"^[A-Z]{2,3}$", block[i].upper()):
        out["importateur_pays"] = f"US {block[i].upper()}" if block[i].upper() in {"USA", "US"} else block[i].upper()
        i += 1

    # Numéro D.A.E. (souvent 6 chiffres avant la date)
    if i < len(block) and _NUM_DECL_RE.match(block[i]) and len(block[i]) >= 5:
        out["numero_dae"] = block[i]
        i += 1

    if i < len(block) and _DATE_RE.match(block[i]):
        out["date_declaration"] = block[i]
        i += 1

    # Adresse + raison sociale exportateur (ordre fixe sur ce modèle)
    if i < len(block) and re.search(r"\d", block[i]) and len(block[i]) > 12:
        out["adresse_exportateur"] = block[i]
        i += 1
    if i < len(block) and re.search(r"[A-Z]{4,}", block[i]) and not _CODE_MATRICULE_RE.match(block[i]):
        out["exportateur_nom"] = re.sub(r"\s+", " ", block[i]).strip()
        out["exportateur"] = out["exportateur_nom"]
        i += 1
    if i < len(block) and _CODE_MATRICULE_RE.match(block[i]):
        out["exportateur_code"] = block[i].upper()
        i += 1

    # Doublons nom/adresse (ignorer si identiques)
    while i < len(block) and (
        block[i] == out.get("exportateur_nom")
        or block[i] == out.get("adresse_exportateur")
    ):
        i += 1

    if i < len(block) and ("SFAX" in block[i].upper() or "SEKIT" in block[i].upper()):
        out["adresse_entreposage"] = block[i]
        i += 1

    if i < len(block) and re.match(r"^[A-Z]{2}$", block[i].upper()):
        out["type_declaration"] = block[i].upper()
        i += 1

    if i < len(block) and block[i].isdigit() and len(block[i]) <= 3:
        out["nbre_articles"] = block[i]
        out["nombre_articles"] = block[i]
        i += 1
    if i < len(block) and block[i].isdigit() and len(block[i]) <= 3:
        out["nombre_colis"] = block[i]
        i += 1

    if i < len(block) and _NUM_DECL_RE.match(block[i]) and len(block[i]) == 4:
        out["numero_declaration"] = block[i]
        i += 1

    countries, i = _parse_country_quad(block, i)
    out.update(countries)
    if out.get("importateur_pays") and "US" in str(out["importateur_pays"]).upper():
        for key in ("pays_destination_finale", "pays_premiere_destination", "pays_achat"):
            val = out.get(key) or ""
            if val.startswith("US "):
                out["pays_destination_finale"] = val
                out["pays_destination"] = val
                break
        else:
            out["pays_destination_finale"] = "US USA"
            out["pays_destination"] = "US USA"

    # Finances / transport dans la suite du bloc
    while i < len(block):
        line = block[i]
        up = line.upper()
        if up in {"EXW", "FOB", "CIF", "CFR", "DAP", "FCA", "DDP"}:
            out["mode_livraison"] = up
        elif up == "USD" or up == "EUR" or up == "TND":
            out["devise"] = up
        elif re.match(r"^\d+\.\d{3}$", line):
            if "montant_ptfn" not in out:
                out["montant_ptfn"] = line
            elif "taux_conversion" not in out:
                out["taux_conversion"] = line
            elif "valeur_dinars" not in out:
                out["valeur_dinars"] = line
        elif up == "AVION" or up == "NAVIRE" or up == "CAMION":
            out["mode_transport"] = up
            out["transport_international_identite"] = up
        elif _DATE_RE.match(line) and line != out.get("date_declaration"):
            out["engagement"] = line
        elif line.isdigit() and len(line) <= 2 and "transport_international_mode" not in out:
            out["transport_international_mode"] = line
        i += 1

    return out


def parse_embedded_supplier_line(text: str) -> dict[str, Any]:
    """Ligne « 5751:FAB EQUIPEMENTS MECANIQUES » (المورد) = exportateur tunisien."""
    for line in _norm_lines(text):
        m = re.search(r"(\d{3,5})\s*:\s*([A-Z][A-Z0-9 &.\-]{4,80})", line, re.IGNORECASE)
        if not m:
            continue
        code, name = m.group(1), re.sub(r"\s+", " ", m.group(2)).strip()
        if len(name) < 4:
            continue
        return {
            "exportateur_nom": name,
            "exportateur": name,
            "code_exportateur": code,
        }
    return {}


def parse_embedded_article_section(text: str) -> dict[str, Any]:
    lines = _norm_lines(text)
    out: dict[str, Any] = {}
    # Désignation : bloc avant le code NDP 11 chiffres
    ndp_idx = None
    for i, line in enumerate(lines):
        if _NDP_RE.fullmatch(line.strip()):
            ndp_idx = i
            break
    if ndp_idx is not None:
        out["code_sh_ndp"] = lines[ndp_idx].strip()
        des_lines: list[str] = []
        for j in range(max(0, ndp_idx - 6), ndp_idx):
            ln = lines[j]
            if len(ln) > 15 and re.search(r"[A-Z]{3,}", ln) and not _DATE_RE.match(ln):
                if not ln.isdigit() and "CODE" not in ln.upper():
                    des_lines.append(ln.rstrip("*."))
        if des_lines:
            out["designation_marchandises"] = re.sub(r"\s+", " ", " ".join(des_lines))[:500]

        tail = lines[ndp_idx + 1 : ndp_idx + 16]
        nums = [t for t in tail if re.match(r"^[\d.]+$", t)]
        if len(nums) >= 1:
            out["code_pays_origine"] = tail[0] if re.match(r"^[A-Z]{2}$", tail[0]) else None
        if len(tail) >= 2 and re.match(r"^\d{2}$", tail[1]):
            out["code_qcs"] = tail[1]
        if len(tail) >= 3 and re.match(r"^\d{1,3}$", tail[2]):
            out["qcs"] = tail[2]
        for t in tail:
            if re.match(r"^\d+\.\d{3}$", t):
                out["pfn"] = t
                out["montant_ptfn"] = t
                break
    return out


def parse_embedded_footer(text: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for line in _norm_lines(text):
        m_auth = _AUTH_KEY_RE.search(line)
        if m_auth and "cle_authentification" not in out:
            out["cle_authentification"] = m_auth.group(1).upper()
        if "BR -" in line.upper() or "BR-" in line.upper():
            out["bureau_douane"] = line.strip()
            out["designation_bureau"] = line.strip()
        if line.upper().startswith("TC -") or "SFAX" in line.upper() and "ITIN" not in line.upper():
            if "itineraire" not in out and "-" in line:
                out["itineraire"] = line.replace("TC -", "TC-").strip()
        if re.match(r"^\d{3}$", line) and "code_gdt" not in out:
            pass
    # Montant liquidation : pattern 602 / 13.000 near footer
    m_liq = re.search(r"\b602\b[\s\S]{0,40}?\b(\d+\.\d{3})\b", text)
    if m_liq:
        out["code_gdt"] = "602"
        out["montant_liquidation"] = m_liq.group(1)
        out["montant_total"] = m_liq.group(1)
    # Déclarant / validation en pied de page
    lines = _norm_lines(text)
    for i, line in enumerate(lines):
        if re.search(r"ENGINEERING\s+MACHIN", line, re.I):
            name = re.sub(r"\s+", " ", line).strip()
            out.setdefault("declarant", name)
            out.setdefault("nom_declarant", name)
        if re.match(r"^\d{8}$", line):
            out.setdefault("num_repertoire", line)
        if "BR -" in line.upper() or "BR-" in line.upper():
            out.setdefault("bureau_frontiere", line.strip())
    dates = [ln for ln in lines if _DATE_RE.match(ln)]
    if len(dates) >= 2:
        out.setdefault("date_validation", dates[-1])
    return out


def parse_embedded_pdf_layout(text: str) -> dict[str, Any]:
    """Assemble tous les parseurs layout PDF texte."""
    merged: dict[str, Any] = {}
    for part in (
        parse_embedded_party_block(text),
        parse_embedded_supplier_line(text),
        parse_embedded_article_section(text),
        parse_embedded_footer(text),
    ):
        for k, v in part.items():
            if v is not None and str(v).strip():
                merged[k] = v
    if merged:
        merged["extraction_layout"] = "embedded_pdf_value_block"
    return merged


def apply_embedded_pdf_layout(parsed: dict[str, Any], text: str) -> dict[str, Any]:
    """Fusionne le layout PDF texte en priorité sur les champs parties/identification."""
    layout = parse_embedded_pdf_layout(text)
    if not layout:
        return parsed

    priority_keys = {
        "exportateur_nom",
        "exportateur",
        "exportateur_code",
        "code_exportateur",
        "adresse_exportateur",
        "importateur_nom",
        "importateur",
        "importateur_pays",
        "numero_declaration",
        "date_declaration",
        "type_declaration",
        "numero_dae",
        "nbre_articles",
        "nombre_articles",
        "nombre_colis",
        "adresse_entreposage",
        "pays_provenance",
        "pays_achat",
        "pays_premiere_destination",
        "pays_destination_finale",
        "pays_destination",
        "mode_livraison",
        "devise",
        "montant_ptfn",
        "taux_conversion",
        "valeur_dinars",
        "mode_transport",
        "transport_international_identite",
        "transport_international_mode",
        "designation_marchandises",
        "code_sh_ndp",
        "code_pays_origine",
        "code_qcs",
        "qcs",
        "pfn",
        "code_regime_financier",
        "code_delai",
        "cle_authentification",
        "bureau_douane",
        "designation_bureau",
        "itineraire",
        "code_gdt",
        "montant_liquidation",
        "montant_total",
        "declarant",
        "nom_declarant",
        "num_repertoire",
        "date_validation",
        "bureau_frontiere",
        "poids_brut",
        "poids_net",
        "coefficient_ajustement",
        "regime_douanier_precedent",
    }
    reasons = set(parsed.get("field_reject_reasons") or [])
    for key in priority_keys:
        val = layout.get(key)
        if val is None or not str(val).strip():
            continue
        parsed[key] = val
        reasons.add(f"{key}_from_embedded_pdf_layout")

    if layout.get("extraction_layout"):
        parsed["extraction_layout"] = layout["extraction_layout"]
    parsed["field_reject_reasons"] = sorted(reasons)
    return parsed
