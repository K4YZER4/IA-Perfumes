# Datasets crudos (descargados)

Estos archivos **no se suben a git** (`.gitignore`) porque se regeneran con:

```bash
python combine_datasets.py
```

| Archivo | Fuente | Registros | Licencia |
|---|---|---:|---|
| `../perfumes.csv` | [doevent/perfume](https://huggingface.co/datasets/doevent/perfume) (ya incluido en el repo) | 26,319 | MIT |
| `parfumo_42k.jsonl` | [junyeong-nero/perfume-dataset](https://huggingface.co/datasets/junyeong-nero/perfume-dataset) (rastreo de Parfumo) | 42,095 | No declarada |
| `fragrantica_68k.csv` | [anvo2/perfume-rec-assets](https://huggingface.co/datasets/anvo2/perfume-rec-assets) (rastreo de Fragrantica) | 68,511 | No declarada |

> ⚠️ Los datasets de Parfumo y Fragrantica no tienen licencia clara. Son aptos para
> uso escolar/experimental, pero no para explotación comercial sin revisar los
> términos de cada sitio.

La salida combinada queda en `../master/perfumes_master.csv`.
