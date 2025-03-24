import { PaginationRequestDto } from '@firewall-backend/dto';
import { IsNumber, IsOptional, IsString } from 'class-validator';

export class GetUsersQueryDto extends PaginationRequestDto {
  @IsString()
  @IsOptional()
  username?: string;
}

export class UserIdParamsDto {
  @IsNumber()
  user_id: number;
}
