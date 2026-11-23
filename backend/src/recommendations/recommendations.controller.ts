import { Body, Controller, Post, Req, UseGuards } from '@nestjs/common';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';
import { RecommendDto } from './dto/recommend.dto';
import { RecommendationsService } from './recommendations.service';

@UseGuards(JwtAuthGuard)
@Controller('recommendations')
export class RecommendationsController {
  constructor(private readonly recommendationsService: RecommendationsService) {}

  @Post()
  recommend(@Req() req: any, @Body() dto: RecommendDto) {
    return this.recommendationsService.recommend(req.user.id, dto);
  }
}
