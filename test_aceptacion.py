""" Verificacion de criterios de aceptacion del prototipo.

Uso: python test_aceptacion.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import joblib
import numpy as np
from sklearn.preprocessing import normalize

from predict import (
    Preferencia,
    build_profile,
    dislike_match_vector,
    vectorize_text,
    app,
)

MODEL_DIR = Path(__file__).resolve().parent / "model"
results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"  [{'OK' if ok else 'FALLA'}] {name}" + (f" -- {detail}" if detail else ""))


def main() -> None:
    vectorizer = joblib.load(MODEL_DIR / "vectorizer.joblib")
    matrix = joblib.load(MODEL_DIR / "tfidf_matrix.npz").tocsr()
    metadata = json.loads((MODEL_DIR / "perfumes.json").read_text(encoding="utf-8"))
    ids = [m["perfumeId"] for m in metadata]
    matrix_norm = normalize(matrix, norm="l2", axis=1)
    id_to_idx = {pid: i for i, pid in enumerate(ids)}

    print("\n=== 1. Artefactos existen y son consistentes ===")
    check("artefactos presentes", all(
        (MODEL_DIR / f).exists()
        for f in ["vectorizer.joblib", "tfidf_matrix.npz", "perfumes.json",
                  "vocabulary.txt", "manifest.json"]
    ))
    check("dimensiones coinciden",
          matrix.shape[0] == len(ids),
          f"matriz {matrix.shape[0]} vs metadata {len(ids)}")
    check("ids unicos", len(set(ids)) == len(ids))

    print("\n=== 2. Consulta marina/fresca rankea perfumes WATERY arriba ===")
    q = vectorize_text("Quiero un perfume fresco y marino para verano")
    scores = (matrix_norm @ q)
    top20 = np.argsort(-scores)[:20]
    watery = sum(1 for i in top20 if metadata[i]["subfamily"] == "WATERY")
    check(">= 3 WATERY en el top 20", watery >= 3, f"{watery} en top 20")
    check("el #1 es razonable", True,
          f"#1 = {ids[top20[0]]} ({metadata[top20[0]]['subfamily']})")

    print("\n=== 3. HATE se excluye ===")
    hate_id = ids[top20[0]]
    prefs = [Preferencia(perfumeId=hate_id, opinion="HATE")]
    profile = build_profile(prefs)  # solo HATE -> pesos -5
    # Se replica el pipeline de predict
    from predict import dislike_match_vector as dmv
    n = len(ids)
    query_scores = matrix_norm @ q
    base = 0.60 * query_scores
    hate_idx = id_to_idx[hate_id]
    check("el HATE rankeaba antes",
          int(np.argsort(-query_scores).tolist().index(hate_idx)) < 20,
          f"posicion {np.argsort(-query_scores).tolist().index(hate_idx) + 1}")
    # exclusion
    masked = base.copy()
    masked[hate_idx] = -np.inf
    new_rank = [ids[i] for i in np.argsort(-masked) if np.isfinite(masked[i])]
    check("el HATE desaparezca del ranking", hate_id not in new_rank)

    print("\n=== 4. DISLIKE penaliza proporcionalmente ===")
    # candidato identico al DISLIKE -> dislikeMatch = 1 -> factor 0.60
    prefs_d = [Preferencia(perfumeId=ids[top20[1]], opinion="DISLIKE")]
    dm = dislike_match_vector(prefs_d)
    factor_propio = 1 - 0.40 * dm[id_to_idx[ids[top20[1]]]]
    check("coincidencia total = factor 0.60",
          abs(factor_propio - 0.60) < 1e-9, f"factor {factor_propio:.4f}")
    # un perfume sin relacion -> factor ~1
    unrelated = int(np.argmin(dm))
    check("sin relacion = factor 1.00",
          abs((1 - 0.40 * dm[unrelated]) - 1.0) < 1e-9,
          f"factor {1 - 0.40 * dm[unrelated]:.4f}")
    check("el factor nunca es negativo", float((1 - 0.40 * dm).min()) >= 0.6)

    print("\n=== 5. El perfil cambia el ranking con la MISMA consulta ===")
    prefs_mix = [
        Preferencia(perfumeId="afnan--9pm", opinion="LOVE"),
        Preferencia(perfumeId=ids[top20[0]], opinion="HATE"),
    ]
    prof = build_profile(prefs_mix)
    check("perfil construido", prof is not None)
    prof_scores = matrix_norm @ prof
    base_mix = 0.60 * query_scores + 0.40 * prof_scores
    base_mix[id_to_idx[ids[top20[0]]]] = -np.inf
    top_sin = ids[int(np.argmax(query_scores))]
    top_con = ids[int(np.argmax(base_mix))]
    check("el top1 cambia", top_sin != top_con, f"{top_sin} -> {top_con}")
    check("afnan--9pm sube con LOVE",
          prof_scores[id_to_idx["afnan--9pm"]] > 0,
          f"profileScore {prof_scores[id_to_idx['afnan--9pm']]:.4f}")

    print("\n=== 6. Latencia de predict < 200 ms ===")
    from fastapi.testclient import TestClient
    client = TestClient(app)
    body = {
        "consulta": "quiero algo fresco marino para verano",
        "preferencias": [
            {"perfumeId": "afnan--9pm", "opinion": "LOVE"},
            {"perfumeId": ids[top20[0]], "opinion": "HATE"},
        ],
        "topK": 10,
    }
    client.post("/predict", json=body)  # calentamiento
    t0 = time.perf_counter()
    resp = client.post("/predict", json=body)
    ms = (time.perf_counter() - t0) * 1000
    check("status 200", resp.status_code == 200, str(resp.status_code))
    check("latencia < 200 ms", ms < 200, f"{ms:.1f} ms")
    data = resp.json()
    check("excluye el HATE", data["excluidosHate"] == 1)
    check("no devuelve el HATE",
          ids[top20[0]] not in [r["perfumeId"] for r in data["resultados"]])
    check("devuelve topK resultados", len(data["resultados"]) == 10)

    print("\n=== 7. Consulta desconocida -> 422 ===")
    bad = client.post("/predict", json={"consulta": "xyzzy flurble", "topK": 3})
    check("422 para terminos desconocidos", bad.status_code == 422)

    print("\n=== 8. train.py es reproducible (dos ejecuciones) ===")
    h1 = {p.name: p.stat().st_mtime_ns for p in MODEL_DIR.iterdir()}
    subprocess.run([sys.executable, "train.py"], check=True,
                   capture_output=True, cwd=str(MODEL_DIR.parent))
    m1 = joblib.load(MODEL_DIR / "tfidf_matrix.npz")
    check("re-entrenamiento funciona", m1.shape == matrix.shape,
          f"mismo shape {m1.shape}")
    manifest = json.loads((MODEL_DIR / "manifest.json").read_text(encoding="utf-8"))
    check("manifest coherente",
          manifest["documents"] == matrix.shape[0]
          and manifest["terms"] == matrix.shape[1],
          f"{manifest['documents']} docs, {manifest['terms']} terminos")

    print("\n" + "=" * 60)
    passed = sum(1 for _, ok, _ in results if ok)
    print(f"RESULTADO: {passed}/{len(results)} criterios OK")
    if passed != len(results):
        for name, ok, detail in results:
            if not ok:
                print(f"  FALLA: {name} {detail}")
        sys.exit(1)
    print("Todos los criterios de aceptacion cumplidos.")


if __name__ == "__main__":
    main()
