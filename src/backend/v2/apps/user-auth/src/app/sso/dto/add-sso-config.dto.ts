import { IsEnum, IsOptional, IsString, IsUrl } from 'class-validator';
import { SsoConfigType } from '../enums/sso-config-type.enum';

export class AddSsoConfigDto {
  @IsEnum(SsoConfigType)
  type: SsoConfigType;

  @IsString()
  issuer: string;

  @IsUrl()
  authorizationUrl: string;

  @IsUrl()
  tokenUrl: string;

  @IsUrl()
  userInfoUrl: string;

  @IsUrl()
  @IsOptional()
  jwksUri?: string;

  @IsString()
  clientId: string;

  @IsString()
  clientSecret: string;

  @IsUrl()
  callbackUrl: string;
}
