import { Module } from '@nestjs/common';
import { PerfumesController } from './perfumes.controller';
import { PerfumesService } from './perfumes.service';

@Module({
  controllers: [PerfumesController],
  providers: [PerfumesService],
  exports: [PerfumesService],
})
export class PerfumesModule {}
