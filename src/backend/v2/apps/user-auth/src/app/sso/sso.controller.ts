import {
  BadRequestException,
  Body,
  Controller,
  Delete,
  Get,
  Param,
  Post,
  Query,
  Req,
  Res,
  UseGuards,
} from '@nestjs/common';
import { Request, Response } from 'express';
import { SsoService } from './sso.service';
import * as querystring from 'querystring';
import { AuthGuard, RolesGuard } from '@firewall-backend/guards';
import { Roles } from '@firewall-backend/decorators';
import { AddSsoConfigDto } from './dto/add-sso-config.dto';
import { ApiBearerAuth, ApiTags } from '@nestjs/swagger';
import { InjectPinoLogger, PinoLogger } from 'nestjs-pino';
import {
  GetSsoConfigQueryDto,
  SsoCallbackQueryDto,
  SsoConfigParamsDto,
} from './dto/get-sso-config-query.dto';
import { JwtService } from '@nestjs/jwt';
import { Base64 } from '@firewall-backend/utils';
import { UserRole } from '@firewall-backend/enums';

@ApiBearerAuth()
@ApiTags('SSO')
@Controller('sso')
export class SsoController {
  constructor(
    private readonly ssoService: SsoService,
    private readonly jwtService: JwtService,
    @InjectPinoLogger(SsoController.name) private readonly logger: PinoLogger
  ) {}

  // To check for token without AuthGuard
  async isAdmin(request: Request) {
    const [type, token] = request.headers.authorization?.split(' ') ?? [];
    if (type !== 'Bearer') {
      return false;
    }

    try {
      const payload = await this.jwtService.verifyAsync(token, {
        secret: process.env['SECRET_KEY'],
      });

      return payload?.role && payload.role === UserRole.Admin;
    } catch (err) {
      this.logger.error({ err }, 'Error while checking for admin');
      return false;
    }
  }

  @Post('config/:name')
  @UseGuards(AuthGuard)
  addConfig(
    @Param() params: SsoConfigParamsDto,
    @Body() addSsoConfigDto: AddSsoConfigDto,
    @Req() req: Request
  ) {
    return this.ssoService.addSsoConfig(
      params.name,
      addSsoConfigDto,
      req.user.user_id
    );
  }

  @Get('config')
  async getAllSsoConfig(
    @Query() query: GetSsoConfigQueryDto,
    @Req() req: Request
  ) {
    return this.ssoService.getAllSsoConfig(query, await this.isAdmin(req));
  }

  @Get('config/:name')
  async getSsoConfig(@Param() params: SsoConfigParamsDto, @Req() req: Request) {
    return this.ssoService.getSsoConfig(params.name, await this.isAdmin(req));
  }

  @Get(':name/login')
  async redirectToSso(
    @Param() params: SsoConfigParamsDto,
    @Res() res: Response
  ) {
    const base64 = new Base64();

    const state = base64.encode(params.name);

    const config = await this.ssoService.getSsoConfig(params.name, true);

    if (!config) {
      throw new BadRequestException(`No SSO config found for ${params.name}`);
    }

    const redirectUrl = `${config.authorizationUrl}?${querystring.stringify({
      client_id: config.clientId,
      response_type: 'code',
      scope: 'openid profile email',
      redirect_uri: config.callbackUrl,
      state: state,
    })}`;

    this.logger.info({ redirectUrl }, 'Redirect URL');

    res.redirect(redirectUrl);
  }

  @Get('callback')
  async ssoCallback(@Query() query: SsoCallbackQueryDto) {
    const base64 = new Base64();

    return await this.ssoService.ssoLogin(
      base64.decode(query.state),
      query.code
    );
  }

  @Delete('config/:name')
  @Roles(UserRole.Admin)
  @UseGuards(AuthGuard, RolesGuard)
  deleteConfig(@Param() params: SsoConfigParamsDto) {
    return this.ssoService.deleteSsoConfig(params.name);
  }
}
