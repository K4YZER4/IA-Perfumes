# IA-Perfumes — Perfume Advisor

Sistema de recomendación de perfumes basado en **modelo de contenido con TF-IDF**, expuesto como API con **FastAPI**. Dado un pedido en lenguaje natural (y opcionalmente un perfil de gustos LOVE/LIKE/DISLIKE/HATE), devuelve el ranking de perfumes más afines del catálogo.

## Cómo funciona

1. **`combine_datasets.py`** construye el catálogo maestro combinando 3 fuentes públicas: la base actual (`doevent/perfume`, 26,319), Parfumo (42,095) y Fragrantica (43,784 con marca identificada). Descarga los crudos a `data/raw/` (no van a git), los normaliza, fusiona por `slug(brand)--slug(name)` eliminando duplicados y escribe `data/master/perfumes_master.csv` con **85,481 perfumes únicos**.
2. **`train.py`** lee `data/master/perfumes_master.csv` si existe (o `data/perfumes.csv` si no), deduplica por `brand + name`, construye un documento de texto por perfume (marca, familia, subfamilia, acordes, notas, descripción, género), expande sinónimos y ajusta **TF-IDF** (unigramas + bigramas, `min_df=2`, `max_features=8000`).
3. Los artefactos entrenados se guardan en `model/` (vectorizador, matriz dispersa, metadatos, vocabulario y manifiesto).
4. **`predict.py`** (FastAPI) solo *carga* los artefactos; no entrena en runtime ni conecta a base de datos.

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

### Regenerar el catálogo maestro

```bash
python combine_datasets.py              # descarga los crudos (si faltan) y combina
python combine_datasets.py --no-download  # usa solo lo ya descargado en data/raw/
python train.py                         # re-entrena sobre el catálogo combinado
```

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
  "totalCatalogo": 85481,
  "excluidosHate": 0,
  "resultados": [
    { "perfumeId": "...", "puntuacion": 0.4123, "queryScore": 0.51, "profileScore": 0.27, "dislikeFactor": 1.0 }
  ]
}
```

## Estructura del proyecto

```
ai-service/
├── data/
│   ├── perfumes.csv              # dataset base (Hugging Face, 26,319 perfumes)
│   ├── raw/                      # crudos descargados (no van a git; ver README de esa carpeta)
│   └── master/
│       ├── perfumes_master.csv   # catálogo combinado (85,481 perfumes)
│       └── merge_report.json     # informe de la fusión (filas por fuente, enriquecimiento)
├── model/                        # artefactos entrenados (vectorizer, matriz TF-IDF, metadatos)
├── combine_datasets.py           # descarga + normaliza + fusiona + deduplica las 3 fuentes
├── train.py                      # entrenamiento TF-IDF
├── predict.py                    # API FastAPI (/health, /predict)
├── synonyms.py                   # diccionario de sinónimos aplicado a consultas e índice
├── demo.py                       # demostración por consola
├── test_aceptacion.py            # pruebas de aceptación (TestClient)
├── iniciar.bat                   # servidor con Swagger
└── demo.bat                      # demostración
```

## Dataset

El catálogo maestro (`data/master/perfumes_master.csv`) combina tres datasets públicos de Hugging Face, fusionados por marca + nombre:

| Fuente | Dataset | Registros | Licencia |
|---|---|---:|---|
| Base | [doevent/perfume](https://huggingface.co/datasets/doevent/perfume) | 26,319 | MIT |
| Parfumo | [junyeong-nero/perfume-dataset](https://huggingface.co/datasets/junyeong-nero/perfume-dataset) | 42,095 | No declarada |
| Fragrantica | [anvo2/perfume-rec-assets](https://huggingface.co/datasets/anvo2/perfume-rec-assets) | 68,511 (43,784 usadas) | No declarada |

Columnas base (`|`): `brand | name_perfume | family | subfamily | fragrances | ingredients | origin | gender | years | description | image_name`, más las columnas nuevas `rating | rating_count | concentration | perfumers | source | source_url`. `train.py` ignora las columnas nuevas, pero el enriquecimiento mejora los documentos (descripciones y notas adicionales de las fuentes nuevas entran al índice TF-IDF).

Detalles de la fusión:

- La **familia olfativa** de las filas nuevas se infiere desde los acordes (heurística documentada en `combine_datasets.py`); las familias del dataset base se conservan tal cual.
- Filas existentes solo se **enriquecen** (campos vacíos se rellenan), nunca se pisan datos.
- En Fragrantica, marca y género vienen pegados al nombre (`"9am Afnanfor women"`): el parser separa la marca contra un índice de marcas conocidas y descarta lo que no se puede identificar (24,727 filas).
- ⚠️ Parfumo y Fragrantica **no tienen licencia clara**: aptos para uso escolar/experimental, no comercial.
