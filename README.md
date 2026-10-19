# IA-Perfumes — Perfume Advisor

Sistema de recomendación de perfumes basado en **modelo de contenido con TF-IDF**, expuesto como API con **FastAPI**. Dado un pedido en lenguaje natural (y opcionalmente un perfil de gustos LOVE/LIKE/DISLIKE/HATE), devuelve el ranking de perfumes más afines del catálogo.

## Cómo funciona

1. **`train.py`** lee `data/perfumes.csv` (26,319 perfumes, delimiter `|`), deduplica por `brand + name`, construye un documento de texto por perfume (marca, familia, subfamilia, acordes, notas, descripción, género), expande sinónimos y ajusta **TF-IDF** (unigramas + bigramas, `min_df=2`, `max_features=8000`).
2. Los artefactos entrenados se guardan en `model/` (vectorizador, matriz dispersa, metadatos, vocabulario y manifiesto).
3. **`predict.py`** (FastAPI) solo *carga* los artefactos; no entrena en runtime ni conecta a base de datos.

### Fórmula de ranking

```
baseScore    = 0.60 · cos(consulta, candidato) + 0.40 · cos(perfil, candidato)
perfil       = Σ peso(opinión) · vector(perfume)     LOVE +5 · LIKE +3 · DISLIKE -3 · HATE -5
HATE         → exclusión directa
DISLIKE      → factor multiplicativo 1 − 0.40 · max(cos(candidato, perfume_dislike))
finalScore   = baseScore · dislikeFactor
```

## Requisitos

- Python 3.12
- `pip install -r requirements.txt`

## Uso rápido

**Windows (doble clic):**

| Archivo | Qué hace |
|---|---|
| `iniciar.bat` | Entrena si hace falta, arranca el servidor en `http://127.0.0.1:8000` y abre el Swagger (`/docs`) |
| `demo.bat` | Entrena si hace falta y corre `demo.py`, una demostración por consola del modelo |

**Manual:**

```bash
python train.py        # entrena y genera los artefactos en model/
uvicorn predict:app --port 8000
```

El modelo ya viene entrenado en `model/`, así que solo basta con arrancar el servidor.

## Endpoints

- `GET /health` → estado y tamaño del catálogo
- `POST /predict` → recomendaciones

Ejemplo:

```bash
curl -X POST http://127.0.0.1:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"consulta": "perfume fresco marino para hombre", "topK": 5}'
```

```json
{
  "consulta": "perfume fresco marino para hombre",
  "totalCatalogo": 26249,
  "excluidosHate": 0,
  "resultados": [
    { "perfumeId": "...", "puntuacion": 0.4123, "queryScore": 0.51, "profileScore": 0.27, "dislikeFactor": 1.0 }
  ]
}
```

## Estructura del proyecto

```
ai-service/
├── data/perfumes.csv        # dataset (Hugging Face, 26,319 perfumes)
├── model/                   # artefactos entrenados (vectorizer, matriz TF-IDF, metadatos)
├── train.py                 # entrenamiento TF-IDF
├── predict.py               # API FastAPI (/health, /predict)
├── synonyms.py              # diccionario de sinónimos aplicado a consultas e índice
├── demo.py                  # demostración por consola
├── test_aceptacion.py       # pruebas de aceptación (TestClient)
├── iniciar.bat              # servidor con Swagger
└── demo.bat                 # demostración
```

## Dataset

`data/perfumes.csv` proviene de un dataset público de Hugging Face con columnas `brand | name_perfume | family | subfamily | fragrances | ingredients | origin | gender | years | description | image_name`.
