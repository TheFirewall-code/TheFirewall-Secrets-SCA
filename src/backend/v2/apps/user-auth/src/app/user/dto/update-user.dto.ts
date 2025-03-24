import { UserRole } from '@firewall-backend/enums';
import { IsBoolean, IsEmail, IsEnum, IsOptional } from 'class-validator';

export class UpdateUserDto {
  @IsEnum(UserRole)
  @IsOptional()
  role?: UserRole;

  @IsBoolean()
  @IsOptional()
  active?: boolean;

  @IsEmail()
  @IsOptional()
  userEmail?: string;
}
