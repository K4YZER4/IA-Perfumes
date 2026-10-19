"""
Diccionario de sinonimos v1 ( Perfume Advisor ).

Objetivo: cuando el usuario escribe en espanol un termino generico
("fresco", "marino", "dulce"...) el modelo debe poder compararlo contra
el vocabulario REAL que existe en el dataset (en ingles).

Regla importante: el diccionario se aplica DOS veces:
  1. Al construir los documentos del indice (train.py)
  2. Al procesar la consulta del usuario (predict.py)

Si solo se aplicara a la consulta, el vector de "elegante" no tendria
por que parecerse a documentos que nunca contuvieron "woody, amber".
"""

# Cada clave se expande a los terminos del dataset que representan ese concepto.
# Los terminos deben existir en el corpus (family / subfamily / fragrances /
# ingredients / description) para que TF-IDF les pueda dar peso.
SYNONYMS: dict[str, list[str]] = {
    # --- estacional / sensacion ---
    "verano": ["fresh", "fresher", "citrus", "aquatic", "watery", "crisp"],
    "invierno": ["amber", "oriental", "woods", "spicy", "warm"],
    "calor": ["fresh", "citrus", "aromatic", "light"],
    "frio": ["amber", "woody", "vanilla", "gourmand"],

    # --- familia / perfil ---
    "fresco": ["fresh", "fresher", "crisp", "citrus", "green", "aromatic"],
    "fresca": ["fresh", "fresher", "crisp", "citrus", "green", "aromatic"],
    "marino": ["marine", "sea water", "sea breeze", "watery", "aquatic", "salty"],
    "marina": ["marine", "sea water", "sea breeze", "watery", "aquatic", "salty"],
    "oceanico": ["marine", "sea water", "ocean", "watery", "aquatic"],
    "acuatico": ["watery", "aquatic", "marine", "sea water"],
    "acuatica": ["watery", "aquatic", "marine", "sea water"],
    "dulce": ["gourmand", "vanilla", "sweet", "fruity"],
    "dulces": ["gourmand", "vanilla", "sweet", "fruity"],
    "ambar": ["amber", "ambery", "oriental"],
    "ambarado": ["amber", "ambery", "oriental"],
    "madera": ["woods", "woody", "cedarwood", "sandalwood", "vetiver"],
    "leñoso": ["woods", "woody", "cedarwood"],
    "leñosa": ["woods", "woody", "cedarwood"],
    "especiado": ["spicy", "spices", "pepper"],
    "especiada": ["spicy", "spices", "pepper"],
    "floral": ["floral", "flower", "white flower"],
    "flores": ["floral", "flower", "jasmine", "rose"],
    "chico": ["male", "for men", "masculine"],
    "hombre": ["male", "for men", "masculine"],
    "mujer": ["female", "for women", "feminine"],
    "unisex": ["unisex"],

    # --- abstractos (los mas ambiguos, se mapean a perfiles tipicos) ---
    "elegante": ["woody", "amber", "powdery", "floral", "soft"],
    "nocturno": ["oriental", "amber", "spicy", "woods", "gourmand"],
    "noche": ["oriental", "amber", "spicy", "woods"],
    "diario": ["fresh", "fresher", "citrus", "aromatic", "soft"],
    "oficina": ["fresh", "soft", "citrus", "white flower"],
    "deportivo": ["fresh", "aromatic", "citrus", "aquatic"],
    "romantico": ["floral", "rose", "vanilla", "powdery"],
    "seductor": ["amber", "oriental", "vanilla", "spicy"],
    "limpio": ["musk skin", "soft", "fresh", "white flower"],
    "femenino": ["floral", "white flower", "fruity", "powdery"],
    "masculino": ["woods", "aromatic", "woody", "spicy"],
    "potente": ["leather", "tobacco", "oud", "spicy", "woods"],
    "suave": ["soft", "fresh", "white flower", "musk skin"],
    "cálido": ["amber", "vanilla", "oriental", "gourmand"],
    "fugaz": ["citrus", "fresh", "fresher"],
    "duradero": ["oud", "tobacco", "leather", "amber", "woods"],
}


def expand(text: str) -> str:
    """Expande los terminos claves del texto con sus sinonimos.

    Se busca por palabra completa para no expandir substrings raros
    (por ejemplo "flor" dentro de "florido" via startsWith no aplica aqui,
    se usa coincidencia de palabra completa con regex).
    """
    import re

    lowered = text.lower()
    additions: list[str] = []
    for key, values in SYNONYMS.items():
        # coincidencia de palabra completa
        if re.search(rf"\b{re.escape(key)}\b", lowered):
            additions.extend(values)
    if not additions:
        return text
    return text + " " + " ".join(additions)
