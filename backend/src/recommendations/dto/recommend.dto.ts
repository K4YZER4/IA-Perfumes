import { IsIn, IsInt, IsNotEmpty, IsOptional, IsString, Max, Min } from 'class-validator';

export class RecommendDto {
  @IsString()
  @IsNotEmpty()
  consulta: string;

  @IsOptional()
  @IsInt()
  @Min(1)
  @Max(50)
  topK?: number;

  @IsOptional()
  @IsString()
  @IsIn(['Todos', 'Hombre', 'Mujer', 'Unisex'])
  gender?: 'Todos' | 'Hombre' | 'Mujer' | 'Unisex';
}
