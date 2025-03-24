import { Test, TestingModule } from '@nestjs/testing';
import { SsoController } from './sso.controller';
import { SsoService } from './sso.service';
import { getLoggerToken } from 'nestjs-pino';
import { SsoConfig } from './entities/sso-config.entity';
import { getRepositoryToken } from '@nestjs/typeorm';
import { JwtService } from '@nestjs/jwt';
import { mockSsoConfig } from './mock/sso.mock';
import { BadRequestException } from '@nestjs/common';
import { PaginationResponseDto } from '@firewall-backend/dto';
import { Base64 } from '@firewall-backend/utils';
import { User } from '../user/entities/user.entity';
import { mockUser } from '../user/mock/user.mock';
import { UserRole } from '@firewall-backend/enums';
import {
  SsoCallbackQueryDto,
  SsoConfigParamsDto,
} from './dto/get-sso-config-query.dto';

describe('SsoController', () => {
  let controller: SsoController;
  let service: SsoService;

  const mockSsoConfigRepository = {
    findOneBy: jest.fn().mockImplementation(() => mockSsoConfig),
    save: jest.fn().mockImplementation(() => mockSsoConfig),
    find: jest.fn().mockImplementation(() => [mockSsoConfig]),
  };

  const mockUserRepository = {
    findOneBy: jest.fn().mockImplementation(() => mockUser),
    save: jest.fn().mockImplementation(() => mockUser),
    find: jest.fn().mockImplementation(() => [mockUser]),
  };

  const mockLogger = {
    info: jest.fn(),
    error: jest.fn(),
    warn: jest.fn(),
    debug: jest.fn(),
  };

  const mockRes = {
    redirect: jest.fn(),
    status: jest.fn().mockReturnThis(),
    send: jest.fn(),
  } as any;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      controllers: [SsoController],
      providers: [
        SsoService,
        {
          provide: getRepositoryToken(SsoConfig),
          useValue: mockSsoConfigRepository,
        },
        {
          provide: getRepositoryToken(User),
          useValue: mockUserRepository,
        },
        {
          provide: JwtService,
          useValue: {
            sign: jest.fn(),
            verify: jest.fn(),
            verifyAsync: jest.fn(),
          },
        },
        {
          provide: getLoggerToken(SsoService.name),
          useValue: mockLogger,
        },
        {
          provide: getLoggerToken(SsoController.name),
          useValue: mockLogger,
        },
      ],
    }).compile();

    controller = module.get<SsoController>(SsoController);
    service = module.get<SsoService>(SsoService);
  });

  it('should be defined', () => {
    expect(controller).toBeDefined();
  });

  describe('addConfig', () => {
    it('should add a new SSO config', async () => {
      const params: SsoConfigParamsDto = { name: 'test' };
      const dto: SsoConfig = mockSsoConfig;
      const req: any = { user: { user_id: 1 } };
      jest.spyOn(service, 'addSsoConfig').mockResolvedValue(dto);

      expect(await controller.addConfig(params, dto, req)).toBe(dto);
    });
  });

  describe('getConfig', () => {
    it('should return all SSO configs', async () => {
      const result: PaginationResponseDto<SsoConfig> = {
        current_limit: 10,
        current_page: 1,
        data: [mockSsoConfig],
        total_count: 1,
        total_pages: 1,
      };
      const payload = {
        role: UserRole.Admin,
      };
      jest.spyOn(service, 'getAllSsoConfig').mockResolvedValue(result);
      jest
        .spyOn(service['jwtService'], 'verifyAsync')
        .mockReturnValue(new Promise((res) => res(payload)));

      const query = { page: 1, limit: 10 };
      const req: any = {
        user: { role: 'admin' },
        headers: { authorization: 'Bearer test' },
      };
      expect(await controller.getAllSsoConfig(query, req)).toBe(result);
    });

    it('should return an SSO config for non-admin user', async () => {
      const payload = {
        role: UserRole.Admin,
      };
      jest.spyOn(service, 'getSsoConfig').mockResolvedValue(mockSsoConfig);
      jest
        .spyOn(service['jwtService'], 'verifyAsync')
        .mockReturnValue(new Promise((res) => res(payload)));

      const params = { name: 'test' };
      const req: any = {
        user: { role: 'admin' },
        headers: { authorization: 'test' },
      };
      expect(await controller.getSsoConfig(params, req)).toBe(mockSsoConfig);
    });

    it('should return an SSO config', async () => {
      const payload = {
        role: UserRole.Admin,
      };
      jest.spyOn(service, 'getSsoConfig').mockResolvedValue(mockSsoConfig);
      jest
        .spyOn(service['jwtService'], 'verifyAsync')
        .mockReturnValue(new Promise((res) => res(payload)));

      const params = { name: 'test' };
      const req: any = {
        user: { role: 'admin' },
        headers: { authorization: 'Bearer test' },
      };
      expect(await controller.getSsoConfig(params, req)).toBe(mockSsoConfig);
    });
  });

  describe('redirectToSso', () => {
    it('should redirect to SSO login', async () => {
      const params: SsoConfigParamsDto = { name: 'test' };
      const res = {
        redirect: jest.fn(),
        status: jest.fn().mockReturnThis(),
        send: jest.fn(),
      } as any;
      const config = mockSsoConfig;
      jest.spyOn(service, 'getSsoConfig').mockResolvedValue(config);

      await controller.redirectToSso(params, res);

      expect(res.redirect).toHaveBeenCalled();
    });
  });

  describe('redirectToSso', () => {
    it('should throw exception due to null config', async () => {
      const params: SsoConfigParamsDto = { name: 'test' };
      const res = {
        redirect: jest.fn(),
        status: jest.fn().mockReturnThis(),
        send: jest.fn(),
      } as any;
      jest.spyOn(service, 'getSsoConfig').mockResolvedValue(null);

      await expect(controller.redirectToSso(params, res)).rejects.toThrow(
        BadRequestException
      );
    });
  });

  describe('ssoCallback', () => {
    it('should handle SSO callback', async () => {
      const base64 = new Base64();
      const state = base64.encode('test');

      const query: SsoCallbackQueryDto = {
        code: 'test',
        state,
      };
      const result = {
        access_token: 'test',
      };
      jest.spyOn(service, 'ssoLogin').mockResolvedValue(result);

      controller['state'] = state;

      expect(await controller.ssoCallback(query)).toEqual(result);
    });
  });

  describe('deleteConfig', () => {
    it('should delete an SSO config', async () => {
      const params: SsoConfigParamsDto = { name: 'test' };
      jest.spyOn(service, 'deleteSsoConfig').mockResolvedValue(undefined);

      expect(await controller.deleteConfig(params)).toBeUndefined();
      expect(service.deleteSsoConfig).toHaveBeenCalledWith(params.name);
    });
  });
});
