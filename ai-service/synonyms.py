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
    "brisa marina": ["marine", "sea water", "sea breeze", "watery", "aquatic", "salty"],
    "agua marina": ["marine", "sea water", "sea breeze", "watery", "aquatic", "salty"],
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

    # --- notas adicionales y conceptos clave ---
    "salado": ["salty", "sea water", "marine", "aquatic"],
    "salada": ["salty", "sea water", "marine", "aquatic"],
    "facil de gustar": ["fresh", "citrus", "clean", "soft", "pleasant", "aromatic"],
    "facil": ["fresh", "citrus", "clean", "soft"],
    "versatil": ["fresh", "citrus", "clean", "aromatic", "woody"],
    "vainilla": ["vanilla", "gourmand", "sweet"],
    "lavanda": ["lavender", "aromatic", "fresh"],
    "bergamota": ["bergamot", "citrus", "fresh"],
    "limon": ["lemon", "citrus", "fresh"],
    "cedro": ["cedarwood", "woods", "woody"],
    "sandalo": ["sandalwood", "woody", "woods"],
    "cafe": ["coffee", "gourmand", "warm"],
    "cuero": ["leather", "tobacco", "spicy"],
    "tabaco": ["tobacco", "warm", "spicy"],
    "manzana": ["apple", "fruity", "fresh"],
    "canela": ["cinnamon", "spicy", "warm"],
    "coco": ["coconut", "sweet", "fruity"],

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


def expand(text: str, is_query: bool = False) -> str:
    """Expande los terminos claves del texto con sus sinonimos.

    - Si is_query es True (consulta del usuario): busca frases, sinonimos y typos con difflib.
    - Si is_query es False (construccion del indice de perfumes): coincidencia exacta de terminos
      en espanol/ingles olfativos para evitar que nombres propios en descripciones (ej. 'Marina')
      se auto-corrijan a 'marino' por fuzzy matching.
    """
    import difflib
    import re

    lowered = text.lower()
    additions: list[str] = []

    # 1. Chequeo de frases compuestas directas (ej. "facil de gustar", "brisa marina")
    for key, values in SYNONYMS.items():
        if " " in key and key in lowered:
            additions.extend(values)

    # 2. Tokenizar palabras individuales para buscar sinonimos y typos
    tokens = re.findall(r"\b[a-záéíóúñ]+\b", lowered)
    synonym_single_keys = [k for k in SYNONYMS.keys() if " " not in k]

    for token in tokens:
        matched_key = None
        if token in SYNONYMS:
            matched_key = token
        elif is_query:
            # Solo en consultas del usuario corregimos typos (ej. mqarino -> marino)
            # Excluimos nombres propios comunes como 'marina' si no es query intencional
            if token != "marina":
                close = difflib.get_close_matches(token, synonym_single_keys, n=1, cutoff=0.75)
                if close:
                    matched_key = close[0]

        if matched_key:
            additions.extend(SYNONYMS[matched_key])

    if not additions:
        return text

    # Eliminar duplicados manteniendo orden
    seen = set()
    unique_additions = [x for x in additions if not (x in seen or seen.add(x))]
    return text + " " + " ".join(unique_additions)
