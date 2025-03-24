import {
  Controller,
  Get,
  Post,
  Body,
  Param,
  UseGuards,
  Req,
} from '@nestjs/common';
import { AuthService } from './auth.service';
import { LoginDto } from './dto/auth.dto';
import { UserIdParamsDto } from './dto/auth.dto';
import { ResetPasswordDto } from './dto/auth.dto';
import { Roles } from '@firewall-backend/decorators';
import { UserRole } from '@firewall-backend/enums';
import { AuthGuard, RolesGuard } from '@firewall-backend/guards';
import { ApiBearerAuth, ApiTags } from '@nestjs/swagger';
import { Request } from 'express';

@ApiBearerAuth()
@ApiTags('Auth')
@Controller('auth')
export class AuthController {
  constructor(private readonly authService: AuthService) {}

  @Get('/first-login')
  checkFirstLogin() {
    return this.authService.checkIfFirstLogin();
  }

  @Post('/first-login/reset-password')
  resetAdminPassword(@Body() body: ResetPasswordDto) {
    return this.authService.resetAdminPassword(body);
  }

  @Post('/login')
  login(@Body() body: LoginDto) {
    return this.authService.authenticateUser(body);
  }

  @Post('/reset-password')
  @Roles(UserRole.Admin, UserRole.ReadOnly, UserRole.User)
  @UseGuards(AuthGuard, RolesGuard)
  resetPassword(@Body() body: ResetPasswordDto, @Req() req: Request) {
    return this.authService.resetPassword(
      req.user.user_id,
      body,
      req.user.user_id
    );
  }

  @Post('/reset-password/:user_id')
  @Roles(UserRole.Admin)
  @UseGuards(AuthGuard, RolesGuard)
  resetPasswordById(
    @Param() params: UserIdParamsDto,
    @Body() body: ResetPasswordDto,
    @Req() req: Request
  ) {
    return this.authService.resetPassword(
      params.user_id,
      body,
      req.user.user_id
    );
  }
}
