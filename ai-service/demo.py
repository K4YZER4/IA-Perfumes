"""
Perfume Advisor - demo.py

Demostracion para la exposicion: muestra el proceso completo del modelo,
no solo el resultado final.

  1. Registro del dataset
  2. Documento construido para un perfume
  3. Matriz numerica TF-IDF
  4. Consulta convertida a vector
  5. Puntuaciones de similitud
  6. Ranking final
  7. Cambio de resultado al modificar gustos del usuario

Uso:
    python demo.py
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.preprocessing import normalize

from predict import (
    DISLIKE_PENALTY,
    OPINION_WEIGHTS,
    PROFILE_WEIGHT,
    QUERY_WEIGHT,
    Preferencia,
    dislike_match_vector,
    build_profile,
)

BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "model"


def line(char: str = "=", n: int = 70) -> None:
    print(char * n)


def top_terms(vector, vectorizer, k: int = 8) -> list[tuple[str, float]]:
    """Terminos con mayor peso de un vector."""
    arr = vector.toarray().ravel() if hasattr(vector, "toarray") else np.asarray(vector).ravel()
    order = np.argsort(-arr)[:k]
    vocab = vectorizer.get_feature_names_out()
    return [(vocab[i], float(arr[i])) for i in order if arr[i] > 0]


def score_query(matrix_norm, query_vec: np.ndarray) -> np.ndarray:
    return matrix_norm @ query_vec


def show_ranking(ids, metadata, scores, factors, n: int = 10) -> None:
    order = np.argsort(-scores)[:n]
    print(f"  {'#':>2}  {'perfumeId':<45} {'score':>7} {'factor':>7}  familia")
    print("  " + "-" * 95)
    for rank, i in enumerate(order, start=1):
        m = metadata[i]
        f = "  1.00" if factors is None else f"{factors[i]:6.2f}"
        print(
            f"  {rank:>2}  {ids[i]:<45} {scores[i]:7.4f} {f}  "
            f"{m['family']}/{m['subfamily']}"
        )


def main() -> None:
    vectorizer = joblib.load(MODEL_DIR / "vectorizer.joblib")
    matrix = joblib.load(MODEL_DIR / "tfidf_matrix.npz").tocsr()
    metadata = json.loads((MODEL_DIR / "perfumes.json").read_text(encoding="utf-8"))
    ids = [m["perfumeId"] for m in metadata]
    matrix_norm = normalize(matrix, norm="l2", axis=1)

    # ==================================================================
    line()
    print("PERFUME ADVISOR - DEMOSTRACION DEL MODELO (TF-IDF + similitud de coseno)")
    line()

    # ------------------------------------------------------------------
    line("-")
    print("1) REGISTRO DEL DATASET")
    line("-")
    print(f"   Documentos: {matrix.shape[0]} perfumes")
    print(f"   Termino (vocabulario): {matrix.shape[1]}")
    print(f"   Valores no nulos: {matrix.nnz}")
    m = metadata[0]
    print(f"   Ejemplo -> id: {m['perfumeId']} | {m['brand']} {m['name']}")
    print(f"   Familia: {m['family']} / {m['subfamily']} | {m['gender']} | {m['releaseYear']}")

    # ------------------------------------------------------------------
    line("-")
    print("2) DOCUMENTO CONSTRUIDO PARA UN PERFUME")
    line("-")
    from train import build_document, DATA_PATH
    import pandas as pd

    df = pd.read_csv(DATA_PATH, delimiter="|", dtype=str, keep_default_na=False)
    df = df[(df["brand"].str.strip() == m["brand"]) & (df["name_perfume"].str.strip() == m["name"])].iloc[0]
    doc = build_document(df)
    print(f"   perfumeId: {m['perfumeId']}")
    print(f"   documento: {doc[:400]}{'...' if len(doc) > 400 else ''}")
    print()
    print("   Termino   |  peso TF-IDF")
    for term, weight in top_terms(matrix[0], vectorizer):
        print(f"   {term:<12} {weight:.4f}")

    # ------------------------------------------------------------------
    line("-")
    print("3) MATRIZ NUMERICA TF-IDF")
    line("-")
    print(f"   forma: {matrix.shape}  (perfumes x terminos)")
    print("   (cada perfume es un vector de pesos)")
    # Se muestran 3 perfumes de la misma subfamilia y columnas donde LOS TRES
    # tienen peso, para que el fragmento se vea con valores reales (no ceros)
    same = [i for i, meta in enumerate(metadata)
            if meta["subfamily"] == metadata[0]["subfamily"]][:3]
    cols = None
    for i in same:
        nz = set(matrix[i].indices.tolist())
        cols = nz if cols is None else (cols & nz)
    if not cols or len(cols) < 4:
        cols = set()
        for i in same:
            cols |= set(matrix[i].indices.tolist())
    dense_cols = np.array(sorted(cols)[:8])
    vocab = vectorizer.get_feature_names_out()
    print(f"   fragmento (subfamilia {metadata[0]['subfamily']}, 8 de {matrix.shape[1]} columnas):")
    print("   " + "".join(f"{vocab[c][:9]:>10}" for c in dense_cols))
    for r in same:
        row = matrix[r, dense_cols].toarray().ravel()
        label = ids[r][:20]
        print(f"   {label:<20}" + "".join(f"{v:10.3f}" for v in row))

    # ==================================================================
    line()
    print("4) CONSULTA CONVERTIDA A VECTOR")
    line()
    from predict import vectorize_text

    consulta = "Quiero un perfume fresco y marino para verano"
    print(f'   consulta: "{consulta}"')
    q = vectorize_text(consulta)
    from scipy import sparse

    q_sparse = sparse.csr_matrix(q.reshape(1, -1))
    print("   terminos con peso en la consulta:")
    for term, weight in top_terms(q_sparse, vectorizer, k=12):
        print(f"     {term:<18} {weight:.4f}")

    # ==================================================================
    line("-")
    print("5) PUNTUACIONES DE SIMILITUD (solo consulta, sin perfil)")
    line("-")
    query_scores = score_query(matrix_norm, q)
    show_ranking(ids, metadata, query_scores, None, n=10)

    # ==================================================================
    line("-")
    print("6) RANKING FINAL CON PERFIL (0.60 consulta + 0.40 perfil)")
    line("-")

    # Se eligen perfumes REALES y explicitos para que el ejemplo cierre
    top_query = np.argsort(-query_scores)
    id_to_idx = {pid: i for i, pid in enumerate(ids)}

    # LOVE: Afnan 9PM (nocturno dulce, existe en el dataset)
    love_idx = id_to_idx.get("afnan--9pm")
    if love_idx is None:
        love_idx = next(
            i for i, meta in enumerate(metadata) if meta["subfamily"] == "GOURMAND"
        )
    # LIKE: un perfume fresco del top de la consulta
    fresh_idx = next(
        i for i in top_query if metadata[i]["subfamily"] in ("CITRUS", "GREEN")
    )
    # HATE: el perfume marino mejor rankeado (el #1 de la consulta)
    marine_idx = next(
        i for i in top_query if metadata[i]["subfamily"] == "WATERY"
    )
    # DISLIKE: un gourmand (dulce) distinto del que se ama
    sweet_idx = next(
        i for i, meta in enumerate(metadata)
        if meta["subfamily"] == "GOURMAND" and i != love_idx
    )

    prefs = [
        Preferencia(perfumeId=ids[love_idx], opinion="LOVE"),
        Preferencia(perfumeId=ids[fresh_idx], opinion="LIKE"),
        Preferencia(perfumeId=ids[marine_idx], opinion="HATE"),
        Preferencia(perfumeId=ids[sweet_idx], opinion="DISLIKE"),
    ]
    print("   Perfil aplicado:")
    for p in prefs:
        meta = metadata[id_to_idx[p.perfumeId]]
        print(
            f"     {p.opinion:<8} -> {p.perfumeId:<45} "
            f"({meta['brand']} {meta['name']}, {meta['subfamily']})"
        )

    profile_vec = build_profile(prefs)
    profile_scores = score_query(matrix_norm, profile_vec) if profile_vec is not None else np.zeros(len(ids))
    base_scores = QUERY_WEIGHT * query_scores + PROFILE_WEIGHT * profile_scores

    dm = dislike_match_vector(prefs)
    factors = np.ones(len(ids)) if dm is None else 1.0 - (DISLIKE_PENALTY * np.clip(dm, 0.0, 1.0))
    final_scores = base_scores * factors

    # exclusion HATE
    hate_ids = [p.perfumeId for p in prefs if p.opinion == "HATE"]
    final_masked = final_scores.copy()
    for pid in hate_ids:
        final_masked[id_to_idx[pid]] = -np.inf

    show_ranking(ids, metadata, final_masked, factors, n=10)

    # ==================================================================
    line("-")
    print("7) CAMBIO DE RESULTADO AL CAMBIAR LOS GUSTOS DEL USUARIO")
    line("-")

    # Se comprueba el destino del perfume marcado HATE (excluido) y del DISLIKE
    hate_id = next(p.perfumeId for p in prefs if p.opinion == "HATE")
    dislike_id = next(p.perfumeId for p in prefs if p.opinion == "DISLIKE")
    hate_idx = id_to_idx[hate_id]
    dislike_idx = id_to_idx[dislike_id]

    rank_before = list(np.argsort(-query_scores))
    rank_after = [i for i in np.argsort(-final_masked) if np.isfinite(final_masked[i])]

    pos_before = rank_before.index(hate_idx) + 1 if hate_idx in rank_before else None
    pos_after = rank_after.index(hate_idx) + 1 if hate_idx in rank_after else None

    print(f"   Consulta: \"{consulta}\"")
    print()
    print(f"   PERFUME HATE ({hate_id}):")
    print(f"     Posicion solo con consulta : #{pos_before} (score {query_scores[hate_idx]:.4f})")
    if pos_after is None:
        print(f"     Posicion con opiniones     : EXCLUIDO del ranking")
    else:
        print(f"     Posicion con opiniones     : #{pos_after}")
    print()
    print(f"   PERFUME DISLIKE ({dislike_id}):")
    print(f"     dislikeMatch  : {dm[dislike_idx]:.4f}")
    print(f"     dislikeFactor : {factors[dislike_idx]:.4f} "
          f"(baja {DISLIKE_PENALTY * dm[dislike_idx] * 100:.1f}%)")
    print(f"     score base    : {base_scores[dislike_idx]:.4f} -> final {final_scores[dislike_idx]:.4f}")
    print()
    print(f"   Top 1 antes : {ids[rank_before[0]]}")
    print(f"   Top 1 despues: {ids[rank_after[0]]}")
    print(f"   Cambio de ranking: {'SI' if rank_before[0] != rank_after[0] else 'NO'}")
    print()
    print("   El HATE desaparece por exclusion directa, el DISLIKE baja por")
    print("   dislikeFactor = 1 - (0.40 * dislikeMatch), y el perfil mueve el")
    print("   ranking aunque la consulta escrita sea exactamente la misma.")

    line()
    print("DEMOSTRACION COMPLETADA")
    line()


if __name__ == "__main__":
    main()
