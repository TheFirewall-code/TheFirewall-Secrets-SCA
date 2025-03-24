import { PaginationRequestDto } from '@firewall-backend/dto';
import { IsString } from 'class-validator';

export class GetSsoConfigQueryDto extends PaginationRequestDto {}

export class SsoConfigParamsDto {
  @IsString()
  name: string;
}

export class SsoCallbackQueryDto {
  @IsString()
  code: string;

  @IsString()
  state: string;
}
