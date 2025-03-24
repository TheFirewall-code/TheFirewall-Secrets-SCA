import { IsArray, IsOptional, IsString, ValidateNested } from 'class-validator';
import { Type } from 'class-transformer';
import { PaginationRequestDto } from './pagination.dto';
import { IsPrimitive } from '@firewall-backend/decorators';

export class GetFilterValuesQueryDto extends PaginationRequestDto {
  @IsString()
  filter_key!: string;

  @IsString()
  @IsOptional()
  search?: string;
}

export class FilterKeyValue {
  @IsString()
  filter_key!: string;

  @IsPrimitive()
  value!: string;
}

export class ApplyFiltersDto {
  @IsArray()
  @ValidateNested({ each: true })
  @Type(() => FilterKeyValue)
  filters!: FilterKeyValue[];
}
