export interface User {
  id: string;
  name: string;
  email: string;
  createdAt?: string;
}

export interface Perfume {
  id: string;
  externalId: string;
  brand: string;
  name: string;
  family?: string | null;
  subfamily?: string | null;
  gender?: string | null;
  releaseYear?: string | null;
  description?: string | null;
  imageUrl?: string | null;
}

export interface InventoryItem {
  id: string;
  rating: number;
  opinion: string;
  personalDescription?: string | null;
  createdAt: string;
  perfume: Perfume;
}

export interface Recommendation extends Perfume {
  puntuacion: number;
  queryScore: number;
  profileScore: number;
  dislikeFactor: number;
}

export interface RecommendationResponse {
  consulta: string;
  totalCatalogo: number;
  excluidosHate: number;
  resultados: Recommendation[];
}
