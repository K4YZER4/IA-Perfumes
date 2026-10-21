"""
Perfume Advisor - combine_datasets.py

Construye el catalogo MAESTRO combinando 3 fuentes publicas:

  1. data/perfumes.csv              -> doevent/perfume (Hugging Face, MIT, 26,319)
  2. data/raw/parfumo_42k.jsonl     -> junyeong-nero/perfume-dataset (Parfumo, 42,095)
  3. data/raw/fragrantica_68k.csv   -> anvo2/perfume-rec-assets (Fragrantica, 68,511)

El pipeline:
  1. Descarga los faltantes (Hugging Face, se cachean en data/raw/)
  2. Normaliza cada fuente al esquema comun
  3. Fusiona por clave slug(brand)--slug(name) (la misma que genera train.py)
  4. Enriquece: solo rellena campos VACIOS, nunca pisa datos existentes
  5. Escribe data/master/perfumes_master.csv + merge_report.json

La familia olfativa de las fuentes nuevas se INFIERE a partir de los acordes
(heuristica, marcada como "derived" en el informe). Las columnas extra no
afectan a train.py porque este usa row.get(...) con valores por defecto.

Uso:
    python combine_datasets.py                 # descarga si hace falta y combina
    python combine_datasets.py --no-download   # usa solo lo ya descargado
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import unicodedata
import urllib.request
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "data" / "raw"
MASTER_DIR = BASE_DIR / "data" / "master"
CURRENT_CSV = BASE_DIR / "data" / "perfumes.csv"
MASTER_CSV = MASTER_DIR / "perfumes_master.csv"
REPORT_JSON = MASTER_DIR / "merge_report.json"

SOURCES = {
    "parfumo": {
        "url": "https://huggingface.co/datasets/junyeong-nero/perfume-dataset/resolve/main/data.jsonl",
        "path": RAW_DIR / "parfumo_42k.jsonl",
    },
    "fragrantica": {
        "url": "https://huggingface.co/datasets/anvo2/perfume-rec-assets/resolve/main/data/catalog_70k.csv",
        "path": RAW_DIR / "fragrantica_68k.csv",
    },
}

DELIMITER = "|"

# Esquema comun del catalogo maestro (las 11 primeras columnas son las del
# dataset actual, las ultimas son campos nuevos que train.py ignora).
MASTER_COLUMNS = [
    "brand", "name_perfume", "family", "subfamily", "fragrances",
    "ingredients", "origin", "gender", "years", "description", "image_name",
    "rating", "rating_count", "concentration", "perfumers", "source", "source_url",
]

# Campos que se pueden rellenar si estan vacios (enriquecimiento).
ENRICH_FIELDS = [c for c in MASTER_COLUMNS if c not in ("brand", "name_perfume", "source")]

# Vocabulario de familias del dataset actual (train.py depende de el).
FAMILY_VALUES = [
    "LEATHER", "CHYPRE", "AROMATIC FOUGERE", "FLORAL", "CITRUS",
    "AMBERY (ORIENTAL)", "WOODY",
]

# Mapa accord (fragrantica) -> familia. Se recorre en orden de dominancia,
# el primer accord que empate decide la familia.
ACCORD_TO_FAMILY = {
    "leather": "LEATHER",
    "mossy": "CHYPRE", "chypre": "CHYPRE",
    "aromatic": "AROMATIC FOUGERE", "fougere": "AROMATIC FOUGERE",
    "lavender": "AROMATIC FOUGERE",
    "floral": "FLORAL", "white floral": "FLORAL", "yellow floral": "FLORAL",
    "powdery": "FLORAL", "tuberose": "FLORAL", "rose": "FLORAL",
    "citrus": "CITRUS", "aldehydic": "CITRUS",
    "amber": "AMBERY (ORIENTAL)", "vanilla": "AMBERY (ORIENTAL)",
    "balsamic": "AMBERY (ORIENTAL)", "oriental": "AMBERY (ORIENTAL)",
    "gourmand": "AMBERY (ORIENTAL)",
    "woody": "WOODY", "sandalwood": "WOODY", "cedar": "WOODY",
}

GENDER_MAP_FRAG = {
    "for women": "Female",
    "for men": "Male",
    "for women and men": "Unisex",
}


# ----------------------------------------------------------------------
# Utilidades
# ----------------------------------------------------------------------
def slugify(value: str) -> str:
    """Igual que train.slugify: base del perfumeId estable."""
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def perfume_key(brand: str, name: str) -> str:
    return f"{slugify(brand)}--{slugify(name)}"


def parse_pylist(raw) -> list[str]:
    """Convierte "['Jasmine', 'Lemon']" (o una lista real) en lista de textos."""
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    if not isinstance(raw, str) or not raw.strip():
        return []
    try:
        value = ast.literal_eval(raw.strip())
        if isinstance(value, list):
            return [str(x).strip() for x in value if str(x).strip()]
    except (ValueError, SyntaxError):
        pass
    inner = raw.strip().strip("[]")
    return [p.strip().strip("'\"") for p in inner.split(",") if p.strip().strip("'\"")]


def infer_family(accords: list[str]) -> str:
    """Infiere una de las 7 familias del dataset a partir de los acordes."""
    for accord in accords:
        family = ACCORD_TO_FAMILY.get(accord.strip().lower())
        if family:
            return family
    return ""


def clean_text(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip()
    return "" if text.lower() in ("nan", "none", "null") else text


def download(name: str, url: str, path: Path) -> None:
    if path.exists():
        print(f"  [cache] {path.name} ya existe ({path.stat().st_size / 1e6:.1f} MB)")
        return
    print(f"  [download] {url}")
    tmp = path.with_suffix(path.suffix + ".part")
    with urllib.request.urlopen(url, timeout=120) as response, open(tmp, "wb") as out:
        total = int(response.headers.get("Content-Length") or 0)
        done = 0
        while True:
            chunk = response.read(1 << 20)
            if not chunk:
                break
            out.write(chunk)
            done += len(chunk)
            if total:
                print(f"    {done / 1e6:6.1f} / {total / 1e6:.1f} MB", end="\r")
    tmp.replace(path)
    print(f"  [ok] {path.name} ({path.stat().st_size / 1e6:.1f} MB)")


# ----------------------------------------------------------------------
# Carga de fuentes
# ----------------------------------------------------------------------
def load_current() -> pd.DataFrame:
    """Dataset base (26,319 filas)."""
    df = pd.read_csv(CURRENT_CSV, delimiter=DELIMITER, dtype=str, keep_default_na=False)
    df["source"] = "doevent"
    df["source_url"] = ""
    for col in ("rating", "rating_count", "concentration", "perfumers"):
        if col not in df.columns:
            df[col] = ""
    return df[MASTER_COLUMNS]


def load_parfumo(path: Path) -> pd.DataFrame:
    """junyeong-nero/perfume-dataset: 42,095 registros de Parfumo (JSONL)."""
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            accords = parse_pylist(r.get("main_accords"))
            notes = (
                parse_pylist(r.get("top_notes"))
                + parse_pylist(r.get("middle_notes"))
                + parse_pylist(r.get("base_notes"))
            )
            rating = clean_text(r.get("rating"))
            rows.append({
                "brand": clean_text(r.get("brand_name")),
                "name_perfume": clean_text(r.get("perfume_name")),
                "family": infer_family(accords),
                "subfamily": "",
                "fragrances": " ".join(accords),
                "ingredients": " ".join(dict.fromkeys(notes)),  # sin duplicados, conserva orden
                "origin": "",
                "gender": "",
                "years": clean_text(r.get("release_year")),
                "description": clean_text(r.get("description")),
                "image_name": "",
                "rating": rating,
                "rating_count": clean_text(r.get("review_count")),
                "concentration": clean_text(r.get("concentration")),
                "perfumers": ", ".join(parse_pylist(r.get("perfumer"))),
                "source": "parfumo",
                "source_url": clean_text(r.get("source_url")),
            })
    return pd.DataFrame(rows, columns=MASTER_COLUMNS)


NOTES_RE = {
    "top": re.compile(r"top notes? (?:are|is) ([^;.<]+)", re.IGNORECASE),
    "middle": re.compile(r"middle notes? (?:are|is) ([^;.<]+)", re.IGNORECASE),
    "base": re.compile(r"base notes? (?:are|is) ([^;.<]+)", re.IGNORECASE),
}


def extract_notes_from_description(desc: str) -> str:
    """Fragrantica describe las notas en el texto: 'Top notes are X; middle...'."""
    found: list[str] = []
    for pattern in NOTES_RE.values():
        match = pattern.search(desc)
        if match:
            found += [p.strip() for p in match.group(1).split(",") if p.strip()]
    return ", ".join(dict.fromkeys(found))


def split_fragrantica_name(raw_name: str, brands_by_lastword: dict[str, list[str]]) -> tuple[str, str]:
    """ El campo Name de Fragrantica trae marca y género pegados al nombre:

        '9am Afnanfor women'        -> ('Afnan', '9am')
        '9am Dive Afnanfor women...'-> ('Afnan', '9am Dive')

    Se quita el sufijo 'for women/men', y la marca se localiza por su ultima
    palabra (indice) + verificacion de sufijo. Sin marca conocida, el texto
    entero queda como nombre.
    """
    text = re.sub(r"\s*for (women and men|men|women)\s*$", "", raw_name.strip(), flags=re.IGNORECASE)
    words = text.split()
    if len(words) >= 2:
        candidates = brands_by_lastword.get(words[-1].lower(), [])
        low = text.lower()
        for brand in sorted(candidates, key=len, reverse=True):
            if low.endswith(brand.lower()):
                name = text[: len(text) - len(brand)].strip(" -–—,/")
                if name:
                    return brand, name
    return "", text.strip()


def load_fragrantica(path: Path, brands_by_lastword: dict[str, list[str]]) -> tuple[pd.DataFrame, int]:
    """anvo2/perfume-rec-assets: 68,511 registros de Fragrantica.

    Devuelve (DataFrame, cantidad omitidas por no tener marca identificada)."""
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    df.columns = [c.strip() for c in df.columns]
    rows = []
    skipped = 0
    for r in df.itertuples(index=False):
        record = r._asdict() if hasattr(r, "_asdict") else dict(zip(df.columns, r))
        name_raw = clean_text(record.get("Name"))
        if not name_raw:
            continue
        gender = GENDER_MAP_FRAG.get(clean_text(record.get("Gender")).lower(), "")
        description = clean_text(record.get("Description"))
        accords = parse_pylist(record.get("Main Accords") or record.get("accords"))
        ingredients = extract_notes_from_description(description)
        brand, name = split_fragrantica_name(name_raw, brands_by_lastword)
        if not brand:
            skipped += 1
            continue  # sin marca conocida no hay perfumeId fiable: se omite
        rows.append({
            "brand": brand,
            "name_perfume": name,
            "family": infer_family(accords),
            "subfamily": "",
            "fragrances": " ".join(accords),
            "ingredients": ingredients,
            "origin": "",
            "gender": gender,
            "years": "",
            "description": description,
            "image_name": "",
            "rating": clean_text(record.get("Rating Value")),
            "rating_count": re.sub(r"[^0-9]", "", clean_text(record.get("Rating Count"))),
            "concentration": "",
            "perfumers": ", ".join(parse_pylist(record.get("Perfumers"))),
            "source": "fragrantica",
            "source_url": clean_text(record.get("url")),
        })
    return pd.DataFrame(rows, columns=MASTER_COLUMNS), skipped


# ----------------------------------------------------------------------
# Fusion
# ----------------------------------------------------------------------
def build_brand_index(*frames: pd.DataFrame) -> dict[str, list[str]]:
    """Indice de marcas por ultima palabra (para parsear los nombres de Fragrantica)."""
    index: dict[str, list[str]] = {}
    for df in frames:
        for brand in df["brand"].unique():
            brand = brand.strip()
            if not brand:
                continue
            last = brand.split()[-1].lower()
            index.setdefault(last, [])
            if brand not in index[last]:
                index[last].append(brand)
    return index


def merge_into(master: pd.DataFrame, extra: pd.DataFrame, report: dict, label: str) -> pd.DataFrame:
    """Añade filas nuevas; si la clave ya existe, solo rellena campos vacios."""
    index = {key: i for i, key in enumerate(master["key"])}
    new_rows: list[list[str]] = []
    new_keys: list[str] = []
    added = enriched = 0
    for record in extra.to_dict("records"):
        key = record["key"]
        if key in index:
            i = index[key]
            for field in ENRICH_FIELDS:
                if record[field] and not master.at[i, field]:
                    master.at[i, field] = record[field]
                    enriched += 1
        else:
            new_rows.append([record[c] for c in MASTER_COLUMNS])
            new_keys.append(key)
            index[key] = len(master) + len(new_rows) - 1
            added += 1
    if new_rows:
        add = pd.DataFrame(new_rows, columns=MASTER_COLUMNS)
        add["key"] = new_keys
        master = pd.concat([master, add], ignore_index=True)
    report["sources"][label] = {"rows": int(len(extra)), "added": added, "enriched_fields": enriched}
    print(f"  {label:<12} {len(extra):>7,} filas -> +{added:,} nuevas, {enriched:,} campos rellenados")
    return master


def main() -> None:
    parser = argparse.ArgumentParser(description="Combina los datasets de perfumes")
    parser.add_argument("--no-download", action="store_true", help="no descargar nada")
    args = parser.parse_args()

    print("=" * 70)
    print("PERFUME ADVISOR - Catalogo maestro combinado")
    print("=" * 70)

    # ------------------------------------------------------------------
    # 1. Descargas
    # ------------------------------------------------------------------
    print("\n[1] Fuentes")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if not args.no_download:
        for name, spec in SOURCES.items():
            download(name, spec["url"], spec["path"])
    for name, spec in SOURCES.items():
        if not spec["path"].exists():
            raise SystemExit(f"Falta {spec['path'].name}. Ejecuta sin --no-download.")

    # ------------------------------------------------------------------
    # 2. Carga
    # ------------------------------------------------------------------
    print("\n[2] Carga y normalizacion")
    current = load_current()
    print(f"  doevent     {len(current):>7,} filas (dataset base)")
    parfumo = load_parfumo(SOURCES["parfumo"]["path"])
    print(f"  parfumo     {len(parfumo):>7,} filas")
    brands_index = build_brand_index(current, parfumo)
    fragrantica, skipped = load_fragrantica(SOURCES["fragrantica"]["path"], brands_index)
    print(f"  fragrantica {len(fragrantica):>7,} filas (se omitieron {skipped:,} sin marca identificada)")

    # ------------------------------------------------------------------
    # 3. Fusion
    # ------------------------------------------------------------------
    print("\n[3] Fusion (clave slug(brand)--slug(name))")
    current["key"] = [perfume_key(b, n) for b, n in zip(current["brand"], current["name_perfume"])]
    parfumo["key"] = [perfume_key(b, n) for b, n in zip(parfumo["brand"], parfumo["name_perfume"])]
    fragrantica["key"] = [perfume_key(b, n) for b, n in zip(fragrantica["brand"], fragrantica["name_perfume"])]

    # Filas sin nombre o con clave vacia se descartan; duplicados internos tambien
    for df in (current, parfumo, fragrantica):
        bad = (df["name_perfume"].str.strip() == "") | df["key"].isin(("", "--"))
        if bad.any():
            df.drop(df.index[bad], inplace=True)
        df.drop_duplicates(subset=["key"], keep="first", inplace=True)
        df.reset_index(drop=True, inplace=True)  # indices contiguos para .at[]

    master = current.copy()
    report: dict = {"sources": {}}
    master = merge_into(master, parfumo, report, "parfumo")
    master = merge_into(master, fragrantica, report, "fragrantica")

    # ------------------------------------------------------------------
    # 4. Salida
    # ------------------------------------------------------------------
    print("\n[4] Salida")
    MASTER_DIR.mkdir(parents=True, exist_ok=True)
    out = master[MASTER_COLUMNS].copy()
    out.drop(out.index[out["name_perfume"].str.strip() == ""], inplace=True)
    out.to_csv(MASTER_CSV, sep=DELIMITER, index=False, encoding="utf-8")

    report.update({
        "baseRows": int(len(current)),
        "totalRows": int(len(out)),
        "columns": MASTER_COLUMNS,
        "derivedFamily": "familia inferida desde acordes para las fuentes nuevas",
        "output": str(MASTER_CSV.relative_to(BASE_DIR)),
    })
    REPORT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"  {MASTER_CSV.name}: {len(out):,} perfumes, {MASTER_CSV.stat().st_size / 1e6:.1f} MB")
    print(f"  {REPORT_JSON.name}")
    print("\n[OK] Catalogo maestro listo.")
    print("     Siguiente paso: python train.py")


if __name__ == "__main__":
    main()
