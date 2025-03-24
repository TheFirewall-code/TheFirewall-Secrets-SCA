import { UserRole } from '@firewall-backend/enums';
import { IsBoolean, IsEmail, IsEnum, IsString } from 'class-validator';

export class CreateUserDto {
  @IsString()
  username: string;

  @IsEnum(UserRole)
  role: UserRole;

  @IsEmail()
  userEmail: string;

  @IsBoolean()
  active: boolean;

  @IsString()
  password: string;
}
