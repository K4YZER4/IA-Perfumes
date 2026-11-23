import { Injectable, NotFoundException } from '@nestjs/common';
import { Prisma } from '@prisma/client';
import { PrismaService } from '../prisma/prisma.service';

@Injectable()
export class PerfumesService {
  constructor(private readonly prisma: PrismaService) {}

  async findAll(filters: {
    search?: string;
    brand?: string;
    family?: string;
    subfamily?: string;
    gender?: string;
    limit?: string;
  }) {
    const where: Prisma.PerfumeWhereInput = {};

    if (filters.search?.trim()) {
      const terms = filters.search.trim().split(/\s+/).slice(0, 5);
      const conditions: Prisma.PerfumeWhereInput[] = terms.map((term) => ({
        OR: [
          { name: { contains: term, mode: 'insensitive' } },
          { brand: { contains: term, mode: 'insensitive' } },
        ],
      }));
      where.AND = conditions;
    }

    if (filters.brand?.trim()) {
      where.brand = { contains: filters.brand.trim(), mode: 'insensitive' };
    }
    if (filters.family?.trim()) {
      where.family = { contains: filters.family.trim(), mode: 'insensitive' };
    }
    if (filters.subfamily?.trim()) {
      where.subfamily = { contains: filters.subfamily.trim(), mode: 'insensitive' };
    }
    if (filters.gender?.trim()) {
      where.gender = { equals: filters.gender.trim(), mode: 'insensitive' };
    }

    const parsedLimit = Number(filters.limit);
    const take = Number.isFinite(parsedLimit) && parsedLimit > 0 ? Math.min(parsedLimit, 100) : 50;

    return this.prisma.perfume.findMany({
      where,
      orderBy: [{ brand: 'asc' }, { name: 'asc' }],
      take,
    });
  }

  async findOne(idOrExternalId: string) {
    const perfume = await this.prisma.perfume.findFirst({
      where: {
        OR: [{ id: idOrExternalId }, { externalId: idOrExternalId }],
      },
    });

    if (!perfume) {
      throw new NotFoundException('Perfume no encontrado');
    }

    return perfume;
  }
}
