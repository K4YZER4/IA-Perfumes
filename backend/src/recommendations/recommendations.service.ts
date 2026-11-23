import {
  BadRequestException,
  Injectable,
  ServiceUnavailableException,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import axios from 'axios';
import { PrismaService } from '../prisma/prisma.service';
import { RecommendDto } from './dto/recommend.dto';

interface AiResult {
  perfumeId: string;
  puntuacion: number;
  queryScore: number;
  profileScore: number;
  dislikeFactor: number;
}

interface AiResponse {
  consulta: string;
  totalCatalogo: number;
  excluidosHate: number;
  resultados: AiResult[];
}

@Injectable()
export class RecommendationsService {
  constructor(
    private readonly prisma: PrismaService,
    private readonly config: ConfigService,
  ) {}

  async recommend(userId: string, dto: RecommendDto) {
    const inventory = await this.prisma.inventoryItem.findMany({
      where: { userId },
      include: { perfume: true },
    });

    const preferencias = inventory
      .filter((item) => item.perfume?.externalId)
      .map((item) => ({
        perfumeId: item.perfume.externalId,
        opinion: item.opinion,
      }));

    const aiUrl = this.config.get<string>('AI_SERVICE_URL') || 'http://localhost:8000';

    let data: AiResponse;
    try {
      const response = await axios.post<AiResponse>(
        `${aiUrl}/predict`,
        {
          consulta: dto.consulta.trim(),
          preferencias,
          topK: dto.topK ?? 10,
          genero: dto.gender ?? null,
        },
        { timeout: 15000 },
      );
      data = response.data;
    } catch (error: any) {
      if (error.response?.status === 422) {
        throw new BadRequestException(
          error.response.data?.detail ||
            'La consulta no contiene términos reconocidos por el modelo',
        );
      }
      throw new ServiceUnavailableException(
        'El servicio de recomendaciones (Python) no está disponible. ' +
          'Inicia ai-service con: uvicorn predict:app --port 8000',
      );
    }

    const externalIds = data.resultados.map((item) => item.perfumeId);
    const perfumes = await this.prisma.perfume.findMany({
      where: { externalId: { in: externalIds } },
    });
    const perfumeMap = new Map(perfumes.map((perfume) => [perfume.externalId, perfume]));

    // Fallback: si algun perfume recomendado por IA no esta en la base de datos de PostgreSQL,
    // se crea en demanda para no perder nunca una recomendacion en la UI
    for (const item of data.resultados) {
      if (!perfumeMap.has(item.perfumeId)) {
        try {
          const parts = item.perfumeId.split('--');
          const brandFormatted = parts[0]?.replace(/-/g, ' ') || 'Marca';
          const nameFormatted = parts.slice(1).join(' ')?.replace(/-/g, ' ') || item.perfumeId;
          const created = await this.prisma.perfume.create({
            data: {
              externalId: item.perfumeId,
              brand: brandFormatted.charAt(0).toUpperCase() + brandFormatted.slice(1),
              name: nameFormatted.charAt(0).toUpperCase() + nameFormatted.slice(1),
            },
          });
          perfumeMap.set(item.perfumeId, created);
        } catch {
          // Ignorar si hubo carrera de insercion concurrente
        }
      }
    }

    const resultados = data.resultados
      .map((item) => {
        const perfume = perfumeMap.get(item.perfumeId);
        if (!perfume) {
          return null;
        }
        return {
          ...perfume,
          puntuacion: item.puntuacion,
          queryScore: item.queryScore,
          profileScore: item.profileScore,
          dislikeFactor: item.dislikeFactor,
        };
      })
      .filter((item) => item !== null);

    return {
      consulta: data.consulta,
      totalCatalogo: data.totalCatalogo,
      excluidosHate: data.excluidosHate,
      resultados,
    };
  }
}
