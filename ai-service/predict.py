"""
Perfume Advisor - predict.py

FastAPI que CARGA los artefactos entrenados por train.py.
No entrena nada en runtime y NO conecta a PostgreSQL.

Pipeline de prediccion:
  1. consulta -> sinonimos -> vector consulta
  2. vectorPerfil = suma(peso(opinion) * vector(perfume))
  3. queryScore   = cos(vectorConsulta, candidato)
     profileScore = cos(vectorPerfil,   candidato)
  4. baseScore    = 0.60 * queryScore + 0.40 * profileScore
  5. HATE  -> exclusion directa
  6. DISLIKE -> dislikeMatch = max(cos(candidato, dislike))
                dislikeFactor = 1 - (0.40 * dislikeMatch)
  7. finalScore = baseScore * dislikeFactor
  8. ranking topK

Ejecutar:
    uvicorn predict:app --port 8000
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import joblib
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sklearn.preprocessing import normalize

from synonyms import expand

BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "model"

# ----------------------------------------------------------------------
# Pesos de opinion (definidos en el plan del proyecto)
# ----------------------------------------------------------------------
OPINION_WEIGHTS: dict[str, float] = {
    "LOVE": 5.0,
    "LIKE": 3.0,
    "NEUTRAL": 0.0,
    "DISLIKE": -3.0,
    "HATE": -5.0,
}

QUERY_WEIGHT = 0.60     # 60% consulta actual
PROFILE_WEIGHT = 0.40   # 40% perfil personal
DISLIKE_PENALTY = 0.40  # baja hasta 40% con coincidencia maxima


# ----------------------------------------------------------------------
# Modelos de peticion/respuesta
# ----------------------------------------------------------------------
class Preferencia(BaseModel):
    perfumeId: str
    opinion: Literal["LOVE", "LIKE", "NEUTRAL", "DISLIKE", "HATE"]


class PredictRequest(BaseModel):
    consulta: str = Field(..., min_length=1, description="Peticion en lenguaje natural")
    preferencias: list[Preferencia] = Field(default_factory=list)
    topK: int = Field(default=10, ge=1, le=50)
    genero: Literal["Todos", "Hombre", "Mujer", "Unisex"] | None = None
    excluirColeccion: bool = Field(default=True, description="Excluir perfumes ya calificados por el usuario")


class Resultado(BaseModel):
    perfumeId: str
    puntuacion: float
    queryScore: float
    profileScore: float
    dislikeFactor: float


class PredictResponse(BaseModel):
    consulta: str
    totalCatalogo: int
    excluidosHate: int
    resultados: list[Resultado]


# ----------------------------------------------------------------------
# Carga de artefactos (una sola vez al arrancar)
# ----------------------------------------------------------------------
def load_artifacts() -> None:
    if not (MODEL_DIR / "vectorizer.joblib").exists():
        raise SystemExit("No hay artefactos. Ejecuta primero: python train.py")

    app.state.vectorizer = joblib.load(MODEL_DIR / "vectorizer.joblib")
    app.state.matrix = joblib.load(MODEL_DIR / "tfidf_matrix.npz").tocsr()
    app.state.metadata = json.loads((MODEL_DIR / "perfumes.json").read_text(encoding="utf-8"))
    app.state.ids = [m["perfumeId"] for m in app.state.metadata]
    app.state.id_to_idx = {pid: i for i, pid in enumerate(app.state.ids)}

    # Vectores L2-normalizados: cos(a, b) = a_norm @ b_norm.T
    app.state.matrix_norm = normalize(app.state.matrix, norm="l2", axis=1)

    # Vectores propios de cada perfume para el perfil y los DISLIKE
    # (son los mismos renglones de la matriz, ya normalizados)
    app.state.perfume_vectors = app.state.matrix_norm

    print(
        f"[load_artifacts] {len(app.state.ids)} perfumes | "
        f"{app.state.matrix.shape[1]} terminos"
    )


app = FastAPI(title="Perfume Advisor - Modelo de recomendacion", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
load_artifacts()


# ----------------------------------------------------------------------
# Utilidades
# ----------------------------------------------------------------------
def vectorize_text(text: str) -> np.ndarray:
    """Texto -> vector TF-IDF (1 x terminos) normalizado L2."""
    expanded = expand(text, is_query=True)
    vec = app.state.vectorizer.transform([expanded])
    return normalize(vec, norm="l2", axis=1).toarray()[0]


def build_profile(preferencias: list[Preferencia]) -> np.ndarray | None:
    """ vectorPerfil = suma(peso * vector(perfume)), luego L2.

    Regla del plan:
        LOVE +5 · LIKE +3 · NEUTRAL 0 · DISLIKE -3 · HATE -5
    """
    profile = np.zeros(app.state.matrix.shape[1], dtype=np.float64)
    has_weight = False
    for pref in preferencias:
        weight = OPINION_WEIGHTS[pref.opinion]
        if weight == 0.0:
            continue
        idx = app.state.id_to_idx.get(pref.perfumeId)
        if idx is None:
            continue  # perfumeId desconocido: se ignora con tolerancia
        profile += weight * app.state.perfume_vectors[idx].toarray().ravel()
        has_weight = True

    if not has_weight:
        return None
    norm = np.linalg.norm(profile)
    if norm == 0:
        return None
    return profile / norm


def dislike_match_vector(preferencias: list[Preferencia]) -> np.ndarray | None:
    """ dislikeMatch(j) = max( cos(candidato_j, perfume_DISLIKE) )

    Devuelve un vector con el maximo de similitud de CADA candidato
    contra cualquier perfume marcado DISLIKE. Sin DISLIKE -> None.
    """
    dislike_idxs = [
        app.state.id_to_idx[p.perfumeId]
        for p in preferencias
        if p.opinion == "DISLIKE" and p.perfumeId in app.state.id_to_idx
    ]
    if not dislike_idxs:
        return None

    # (n_dislikes x terminos) @ (terminos x n_catalogo) -> (n_dislikes x n_catalogo)
    dislike_rows = app.state.perfume_vectors[dislike_idxs]
    sims = (dislike_rows @ app.state.matrix_norm.T).toarray()
    return sims.max(axis=0)


# ----------------------------------------------------------------------
# Endpoints
# ----------------------------------------------------------------------
@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "perfumes": len(app.state.ids),
        "terms": int(app.state.matrix.shape[1]),
    }


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest) -> PredictResponse:
    ids = app.state.ids
    n = len(ids)

    # 1. Vector consulta
    query_vec = vectorize_text(req.consulta)
    if not np.any(query_vec):
        raise HTTPException(
            status_code=422,
            detail="La consulta no contiene terminos conocidos por el modelo. "
                   "Prueba con palabras como fresco, marino, dulce, floral, madera...",
        )

    # 2. Score de consulta contra todo el catalogo
    query_scores = app.state.matrix_norm @ query_vec  # (n,)

    # 3. Score de perfil
    profile_vec = build_profile(req.preferencias)
    if profile_vec is None:
        profile_scores = np.zeros(n)
    else:
        profile_scores = app.state.matrix_norm @ profile_vec

    # 4. baseScore = 0.60 * query + 0.40 * perfil
    base_scores = QUERY_WEIGHT * query_scores + PROFILE_WEIGHT * profile_scores

    # 5. Exclusion de HATE, perfumes en coleccion (si aplica) y filtro de genero
    exclude_idxs = set()
    hate_idxs = {
        app.state.id_to_idx[p.perfumeId]
        for p in req.preferencias
        if p.opinion == "HATE" and p.perfumeId in app.state.id_to_idx
    }
    exclude_idxs.update(hate_idxs)

    if req.excluirColeccion:
        for p in req.preferencias:
            if p.perfumeId in app.state.id_to_idx:
                exclude_idxs.add(app.state.id_to_idx[p.perfumeId])

    excluded = len(hate_idxs)
    mask = np.ones(n, dtype=bool)
    for idx in exclude_idxs:
        mask[idx] = False

    if req.genero and req.genero != "Todos":
        target_genders = {
            "Hombre": {"Male", "Unisex"},
            "Mujer": {"Female", "Unisex"},
            "Unisex": {"Unisex"},
        }.get(req.genero)

        if target_genders:
            gender_mask = np.array([m.get("gender") in target_genders for m in app.state.metadata], dtype=bool)
            mask &= gender_mask

    # 6. Penalizacion multiplicativa por DISLIKE
    dm = dislike_match_vector(req.preferencias)
    if dm is None:
        dislike_factors = np.ones(n)
    else:
        dislike_factors = 1.0 - (DISLIKE_PENALTY * np.clip(dm, 0.0, 1.0))

    final_scores = base_scores * dislike_factors

    # 7. Ranking (solo los no excluidos)
    candidate_idxs = np.flatnonzero(mask)
    order = np.argsort(-final_scores[candidate_idxs])
    top = candidate_idxs[order[: req.topK]]

    # 8. Respuesta
    resultados = [
        Resultado(
            perfumeId=ids[i],
            puntuacion=round(float(final_scores[i]), 4),
            queryScore=round(float(query_scores[i]), 4),
            profileScore=round(float(profile_scores[i]), 4),
            dislikeFactor=round(float(dislike_factors[i]), 4),
        )
        for i in top
    ]

    return PredictResponse(
        consulta=req.consulta,
        totalCatalogo=n,
        excluidosHate=excluded,
        resultados=resultados,
    )
