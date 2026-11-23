import { Controller, Get, Param, Query } from '@nestjs/common';
import { PerfumesService } from './perfumes.service';

@Controller('perfumes')
export class PerfumesController {
  constructor(private readonly perfumesService: PerfumesService) {}

  @Get()
  findAll(
    @Query('search') search?: string,
    @Query('brand') brand?: string,
    @Query('family') family?: string,
    @Query('subfamily') subfamily?: string,
    @Query('gender') gender?: string,
    @Query('limit') limit?: string,
  ) {
    return this.perfumesService.findAll({ search, brand, family, subfamily, gender, limit });
  }

  @Get(':id')
  findOne(@Param('id') id: string) {
    return this.perfumesService.findOne(id);
  }
}
