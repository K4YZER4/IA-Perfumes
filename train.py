"""
Perfume Advisor - train.py

Entrenamiento MANUAL del modelo de recomendacion basado en contenido.

Este script:
  1. Lee data/perfumes.csv (dataset local de Hugging Face, delimiter '|')
  2. Valida y deduplica por brand + name
  3. Genera un perfumeId estable: slug(brand)--slug(name)
  4. Construye un documento de texto por perfume
  5. Aplica el diccionario de sinonimos al INDICE
  6. Ajusta TF-IDF sobre todos los documentos
  7. Guarda los artefactos en model/

NO conecta a PostgreSQL. FastAPI solo carga los artefactos ya entrenados.

Uso:
    python train.py
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

from synonyms import expand

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "perfumes.csv"
MODEL_DIR = BASE_DIR / "model"

DELIMITER = "|"
MIN_DOC_FREQ = 2  # terminos que aparecen en >= 2 perfumes
MAX_FEATURES = 8000


def slugify(value: str) -> str:
    """ slug(brand) y slug(name) para construir el perfumeId.

    'Afnan 9PM'          -> 'afnan-9pm'
    'Acqua di Gio'       -> 'acqua-di-gio'
    'Dior Sauvage Elixir'-> 'dior-sauvage-elixir'
    """
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def make_perfume_id(brand: str, name: str) -> str:
    """Clave estable compartida con el futuro importador de PostgreSQL."""
    return f"{slugify(brand)}--{slugify(name)}"


def parse_ingredients(raw: str) -> str:
    """ Convierte la lista python del CSV en texto plano.

    "['Jasmine', 'Lemon', 'Bergamot']" -> "Jasmine Lemon Bergamot"
    """
    if not isinstance(raw, str) or not raw.strip():
        return ""
    inner = raw.strip().strip("[]")
    parts = [p.strip().strip("'\"") for p in inner.split(",")]
    return " ".join(p for p in parts if p)


def build_document(row: pd.Series) -> str:
    """ Construye el documento TF-IDF de un perfume.

    Orden: marca, familia, subfamilia, acordes (fragrances), notas
    (ingredients), descripcion, genero. Todo en minusculas.
    """
    fields = [
        str(row.get("brand", "")),
        str(row.get("family", "")),
        str(row.get("subfamily", "")),
        str(row.get("fragrances", "")),
        parse_ingredients(row.get("ingredients", "")),
        str(row.get("description", "")),
        str(row.get("gender", "")),
    ]
    text = " ".join(fields)
    text = text.lower()
    text = re.sub(r"\s+", " ", text).strip()
    # Se expanden los sinonimos tambien en el indice (decision del plan)
    return expand(text)


def main() -> None:
    print("=" * 70)
    print("PERFUME ADVISOR - Entrenamiento del modelo TF-IDF")
    print("=" * 70)

    # ------------------------------------------------------------------
    # 1. Lectura
    # ------------------------------------------------------------------
    if not DATA_PATH.exists():
        raise SystemExit(f"No se encontro el dataset: {DATA_PATH}")

    df = pd.read_csv(DATA_PATH, delimiter=DELIMITER, dtype=str, keep_default_na=False)
    print(f"\n[1] Filas leidas: {len(df)}")

    # ------------------------------------------------------------------
    # 2. Validacion: sin nombre no se importa
    # ------------------------------------------------------------------
    df["name_perfume"] = df["name_perfume"].str.strip()
    df["brand"] = df["brand"].str.strip()
    invalid = df["name_perfume"] == ""
    failed_rows = int(invalid.sum())
    if failed_rows:
        print(f"    Filas sin nombre descartadas: {failed_rows}")
    df = df[~invalid].copy()

    # ------------------------------------------------------------------
    # 3. Deduplicacion por brand + name
    #    (el dataset trae 70 duplicados; idempotencia futura: externalId
    #     o brandId+name, aqui usamos lo mismo para no divergir)
    # ------------------------------------------------------------------
    before = len(df)
    df = df.drop_duplicates(subset=["brand", "name_perfume"], keep="first")
    dup_removed = before - len(df)
    print(f"    Duplicados brand+name eliminados: {dup_removed}")
    print(f"    Documentos finales: {len(df)}")

    # ------------------------------------------------------------------
    # 4. perfumeId estable
    # ------------------------------------------------------------------
    df["perfumeId"] = df.apply(lambda r: make_perfume_id(r["brand"], r["name_perfume"]), axis=1)
    repeated_ids = int(df["perfumeId"].duplicated().sum())
    if repeated_ids:
        # collision de slug: se fuerza unicidad sufijando el indice
        print(f"    Collisiones de perfumeId resueltas: {repeated_ids}")
        seen: dict[str, int] = {}
        fixed = []
        for pid in df["perfumeId"]:
            if pid in seen:
                seen[pid] += 1
                fixed.append(f"{pid}-{seen[pid]}")
            else:
                seen[pid] = 0
                fixed.append(pid)
        df["perfumeId"] = fixed

    # ------------------------------------------------------------------
    # 5. Documentos + sinonimos aplicados al indice
    # ------------------------------------------------------------------
    print("\n[2] Construyendo documentos...")
    df["document"] = df.apply(build_document, axis=1)
    empty_docs = int((df["document"].str.strip() == "").sum())
    if empty_docs:
        print(f"    Documentos vacios: {empty_docs}")
    print(f"    Ejemplo ({df.iloc[0]['perfumeId']}):")
    print(f"    {df.iloc[0]['document'][:200]}...")

    # ------------------------------------------------------------------
    # 6. TF-IDF
    # ------------------------------------------------------------------
    print("\n[3] Ajustando TF-IDF...")
    vectorizer = TfidfVectorizer(
        lowercase=True,
        stop_words="english",
        ngram_range=(1, 2),     # unigramas + bigramas ("sea water")
        min_df=MIN_DOC_FREQ,
        max_features=MAX_FEATURES,
        sublinear_tf=True,      # log(1 + tf), suaviza los terminos repetidos
    )
    matrix = vectorizer.fit_transform(df["document"])
    print(f"    Matriz: {matrix.shape[0]} documentos x {matrix.shape[1]} terminos")
    print(f"    Densidad: {matrix.nnz / (matrix.shape[0] * matrix.shape[1]):.4%}")

    # ------------------------------------------------------------------
    # 7. Artefactos
    # ------------------------------------------------------------------
    print("\n[4] Guardando artefactos en model/ ...")
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    joblib.dump(vectorizer, MODEL_DIR / "vectorizer.joblib")
    joblib.dump(matrix, MODEL_DIR / "tfidf_matrix.npz")  # joblib preserva la sparse matrix

    metadata = df[
        ["perfumeId", "brand", "name_perfume", "family", "subfamily",
         "gender", "years", "image_name"]
    ].rename(columns={
        "name_perfume": "name",
        "years": "releaseYear",
        "image_name": "imageName",
    })
    metadata.to_json(MODEL_DIR / "perfumes.json", orient="records", force_ascii=False, indent=1)

    vocab = vectorizer.get_feature_names_out().tolist()
    (MODEL_DIR / "vocabulary.txt").write_text("\n".join(vocab), encoding="utf-8")

    manifest = {
        "dataset": str(DATA_PATH.name),
        "documents": int(matrix.shape[0]),
        "terms": int(matrix.shape[1]),
        "min_df": MIN_DOC_FREQ,
        "max_features": MAX_FEATURES,
        "ngram_range": [1, 2],
        "failedRows": failed_rows,
        "duplicatesRemoved": dup_removed,
        "emptyDocuments": empty_docs,
    }
    (MODEL_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"    vectorizer.joblib   ({matrix.shape[1]} terminos)")
    print(f"    tfidf_matrix.npz    ({matrix.shape[0]} x {matrix.shape[1]})")
    print(f"    perfumes.json       ({len(metadata)} registros)")
    print(f"    vocabulary.txt      ({len(vocab)} terminos)")
    print(f"    manifest.json")
    print("\n[OK] Entrenamiento completado.")


if __name__ == "__main__":
    main()
