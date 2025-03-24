import { IsArray, IsNumber, IsOptional, Min } from 'class-validator';

export class PaginationRequestDto {
  @IsOptional()
  @IsNumber()
  @Min(1)
  page?: number;

  @IsOptional()
  @IsNumber()
  @Min(1)
  limit?: number;
}

export class PaginationResponseDto<Type> {
  @IsNumber()
  current_page!: number;

  @IsNumber()
  current_limit!: number;

  @IsNumber()
  total_count!: number;

  @IsNumber()
  total_pages!: number;

  @IsArray()
  data!: Type[];
}
