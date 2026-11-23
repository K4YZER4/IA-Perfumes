import { ConflictException, Injectable, NotFoundException } from '@nestjs/common';
import { RATING_TO_OPINION } from '../common/opinions';
import { PrismaService } from '../prisma/prisma.service';
import { CreateInventoryDto } from './dto/create-inventory.dto';
import { UpdateInventoryDto } from './dto/update-inventory.dto';

@Injectable()
export class InventoryService {
  constructor(private readonly prisma: PrismaService) {}

  findAll(userId: string) {
    return this.prisma.inventoryItem.findMany({
      where: { userId },
      include: { perfume: true },
      orderBy: { createdAt: 'desc' },
    });
  }

  async create(userId: string, dto: CreateInventoryDto) {
    const perfume = await this.prisma.perfume.findFirst({
      where: {
        OR: [{ id: dto.perfumeId }, { externalId: dto.perfumeId }],
      },
    });

    if (!perfume) {
      throw new NotFoundException('Perfume no encontrado');
    }

    const existing = await this.prisma.inventoryItem.findUnique({
      where: {
        userId_perfumeId: {
          userId,
          perfumeId: perfume.id,
        },
      },
    });

    if (existing) {
      throw new ConflictException('Ese perfume ya está en tu inventario');
    }

    return this.prisma.inventoryItem.create({
      data: {
        userId,
        perfumeId: perfume.id,
        rating: dto.rating,
        opinion: RATING_TO_OPINION[dto.rating],
        personalDescription: dto.personalDescription?.trim() || null,
      },
      include: { perfume: true },
    });
  }

  async update(userId: string, itemId: string, dto: UpdateInventoryDto) {
    const item = await this.prisma.inventoryItem.findFirst({
      where: { id: itemId, userId },
    });

    if (!item) {
      throw new NotFoundException('Elemento de inventario no encontrado');
    }

    return this.prisma.inventoryItem.update({
      where: { id: item.id },
      data: {
        rating: dto.rating ?? item.rating,
        opinion: dto.rating ? RATING_TO_OPINION[dto.rating] : item.opinion,
        personalDescription:
          dto.personalDescription === undefined
            ? item.personalDescription
            : dto.personalDescription.trim() || null,
      },
      include: { perfume: true },
    });
  }

  async remove(userId: string, itemId: string) {
    const item = await this.prisma.inventoryItem.findFirst({
      where: { id: itemId, userId },
    });

    if (!item) {
      throw new NotFoundException('Elemento de inventario no encontrado');
    }

    await this.prisma.inventoryItem.delete({ where: { id: item.id } });
    return { success: true };
  }
}
