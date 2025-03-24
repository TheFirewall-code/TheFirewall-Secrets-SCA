import {
  BadRequestException,
  ForbiddenException,
  Injectable,
} from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import axios from 'axios';
import { AddSsoConfigDto } from './dto/add-sso-config.dto';
import { FindManyOptions, FindOneOptions, Repository } from 'typeorm';
import { SsoConfig } from './entities/sso-config.entity';
import { InjectRepository } from '@nestjs/typeorm';
import { InjectPinoLogger, PinoLogger } from 'nestjs-pino';
import { User } from '../user/entities/user.entity';
import { GetSsoConfigQueryDto } from './dto/get-sso-config-query.dto';
import { PaginationResponseDto } from '@firewall-backend/dto';
import jwkToPem from 'jwk-to-pem';
import { SsoConfigType } from './enums/sso-config-type.enum';
import { EULA } from '../eula/entities/eula.entity';
import * as querystring from 'querystring'

@Injectable()
export class SsoService {
  constructor(
    @InjectRepository(SsoConfig)
    private readonly ssoConfigRepository: Repository<SsoConfig>,
    @InjectRepository(User)
    private readonly userRepository: Repository<User>,
    @InjectRepository(EULA)
    private readonly eulaRepository: Repository<EULA>,
    private readonly jwtService: JwtService,
    @InjectPinoLogger(SsoService.name) private readonly logger: PinoLogger
  ) {}

  async addSsoConfig(
    name: string,
    addSsoConfigDto: AddSsoConfigDto,
    uid: number
  ): Promise<SsoConfig> {
    this.logger.info({ name, addSsoConfigDto, uid }, 'Adding SSO config');
    try {
      const config = await this.ssoConfigRepository.findOneBy({
        name: name,
      });

      if (config) {
        return await this.ssoConfigRepository.save({
          id: config.id,
          ...addSsoConfigDto,
          updatedByUid: uid,
        });
      }

      return await this.ssoConfigRepository.save({
        name,
        ...addSsoConfigDto,
        addedByUid: uid,
        updatedByUid: uid,
      });
    } catch (err) {
      this.logger.error(
        { err, addSsoConfigDto, uid },
        'Failed to add sso config'
      );
      throw new Error('Failed to add sso config');
    }
  }

  async getSsoConfig(name: string, isAdmin = false) {
    this.logger.info({ isAdmin, name }, 'Getting SSO config');
    try {
      const findOptions: FindOneOptions<SsoConfig> = {
        where: { name },
      };
      if (!isAdmin) {
        findOptions.select = ['id', 'name', 'type', 'createdAt', 'updatedAt'];
      }

      const config = await this.ssoConfigRepository.findOne(findOptions);
      return config;
    } catch (err) {
      this.logger.error({ err, name, isAdmin }, 'Failed to get sso config');
      throw new Error('Failed to get sso config');
    }
  }

  async getAllSsoConfig(
    getSsoConfigQueryDto: GetSsoConfigQueryDto,
    isAdmin = false
  ): Promise<PaginationResponseDto<SsoConfig>> {
    this.logger.info(
      { isAdmin, getSsoConfigQueryDto },
      'Getting all SSO configs'
    );
    try {
      const { page = 1, limit = 10 } = getSsoConfigQueryDto;
      const offset = (+page - 1) * +limit;

      const findOptions: FindManyOptions<SsoConfig> = {
        skip: offset,
        take: limit,
      };
      if (!isAdmin) {
        findOptions.select = ['id', 'name', 'type', 'createdAt', 'updatedAt'];
      }

      const configs = await this.ssoConfigRepository.find(findOptions);
      const totalCount = await this.ssoConfigRepository.count();

      return {
        current_page: +page,
        current_limit: +limit,
        total_count: totalCount,
        total_pages: Math.ceil(totalCount / +limit),
        data: configs,
      };
    } catch (err) {
      this.logger.error({ err }, 'Failed to get sso configs');
      throw new Error('Failed to get sso configs');
    }
  }

  async getTokens(
    code: string,
    config: SsoConfig
  ): Promise<{ access_token: string; id_token: string }> {
    try {
      const tokenResponse = await axios.post(
        config.tokenUrl,
        {
          grant_type: 'authorization_code',
          code: code,
          redirect_uri: config.callbackUrl,
          client_id: config.clientId,
          client_secret: config.clientSecret,
        },
        {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
        }
      );

      this.logger.info({ data: tokenResponse.data }, 'Data from auth server');

      let access_token: string, id_token: string;
      switch (config.type) {
        case SsoConfigType.Github:
          access_token = querystring.parse(tokenResponse.data)
            .access_token as string;
          break;
        default:
          access_token = tokenResponse.data.access_token;
          id_token = tokenResponse.data.id_token;
      }

      this.logger.info({ access_token, id_token }, 'Tokens');

      return { access_token, id_token };
    } catch (err) {
      this.logger.error({ err, code, config }, 'Error while getting tokens');
      throw new Error('Failed to get tokens');
    }
  }

  async getPublicKey(kid: string, jwksUri: string): Promise<string> {
    const response = await axios.get(jwksUri);
    const jwks = response.data;

    this.logger.info({ jwks }, 'jwks response');

    const key = jwks.keys.find((key: { kid: string }) => key.kid === kid);

    if (!key) {
      this.logger.error({ kid }, 'Unable to find a key with kid');
      throw new Error('Failed to get public key');
    }

    return jwkToPem(key);
  }

  async validateIdToken(idToken: string, jwksUri: string) {
    try {
      const decodedToken = this.jwtService.decode(idToken, { complete: true });
      const kid = decodedToken?.header?.kid;

      if (!kid) {
        throw new Error('Unable to find kid in id token header');
      }

      const publicKey = await this.getPublicKey(kid, jwksUri);

      return await this.jwtService.verifyAsync(idToken, { secret: publicKey });
    } catch (err) {
      this.logger.error(
        { err, idToken, jwksUri },
        'Failed to validate id token'
      );
      throw new Error('Failed to validate id token');
    }
  }

  async ssoLogin(name: string, code: string) {
    this.logger.info({ name, code }, 'SSO login');
    try {
      const config = await this.getSsoConfig(name, true);

      this.logger.info({ config }, 'SSO config');

      if (!config) {
        throw new BadRequestException(`No SSO config found: ${name}`);
      }

      const { access_token, id_token } = await this.getTokens(code, config);

      if (config.jwksUri) {
        const idTokenPayload = await this.validateIdToken(
          id_token,
          config.jwksUri
        );

        this.logger.info({ idTokenPayload }, 'ID token payload');
      }

      const userInfoResponse = await axios.get(config.userInfoUrl, {
        headers: {
          Authorization: `Bearer ${access_token}`,
        },
      });

      const payload = userInfoResponse.data;

      this.logger.info({ payload }, 'User info payload');

      const email = payload.email;
      const role = payload.firewall_role;
      let user = await this.userRepository.findOne({
        where: { userEmail: email },
      });

      const saveOptions: Partial<User> = {};
      if (!user) {
        saveOptions.username = email;
        saveOptions.userEmail = email;

        // if role is already configured in okta
        if (role) {
          saveOptions.role = role;
        }
      } else if (role && role !== user.role) {
        // if role in okta is different, update in db
        saveOptions.id = user.id;
        saveOptions.role = role;
      }

      if (Object.keys(saveOptions).length > 0) {
        user = { ...user, ...(await this.userRepository.save(saveOptions)) };
      }

      if (!user.active) {
        throw new BadRequestException(
          'Cant login in active user, contact admin'
        );
      }

      const eula = await this.eulaRepository.findOne({ where: { id: 1 } });

      if (!eula.accepted) {
        throw new ForbiddenException('EULA is not accepted');
      }

      return {
        access_token: await this.jwtService.signAsync({
          user_id: user.id,
          username: user.username,
          role: user.role,
        }),
      };
    } catch (err) {
      this.logger.error({ err }, 'Failed to authenticate with sso');

      if (err?.response?.statusCode) {
        throw err;
      }

      throw new Error('Failed to authenticate with sso');
    }
  }

  async deleteSsoConfig(name: string) {
    this.logger.info({ name }, 'Deleting SSO config');
    try {
      return await this.ssoConfigRepository.delete({ name });
    } catch (err) {
      this.logger.error({ err }, 'Failed to delete sso config');
      throw new Error('Failed to delete sso config');
    }
  }
}
