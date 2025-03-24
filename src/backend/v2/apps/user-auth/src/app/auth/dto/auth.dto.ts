import { IsNumber, IsString } from 'class-validator';

export class UserIdParamsDto {
  @IsNumber()
  user_id: number;
}

export class LoginDto {
  @IsString()
  username: string;

  @IsString()
  password: string;
}

export class ResetPasswordDto {
  @IsString()
  newPassword: string;
}
