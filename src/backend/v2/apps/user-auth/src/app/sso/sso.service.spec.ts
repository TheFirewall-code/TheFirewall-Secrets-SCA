import { Test, TestingModule } from '@nestjs/testing';
import { SsoService } from './sso.service';
import { getRepositoryToken } from '@nestjs/typeorm';
import { JwtService } from '@nestjs/jwt';
import { SsoConfig } from './entities/sso-config.entity';
import { getLoggerToken } from 'nestjs-pino';
import { mockAddSsoConfigDto, mockSsoConfig } from './mock/sso.mock';
import axios from 'axios';
import { BadRequestException } from '@nestjs/common';
import { User } from '../user/entities/user.entity';
import { mockUser } from '../user/mock/user.mock';
import { PaginationResponseDto } from '@firewall-backend/dto';
import jwkToPem from 'jwk-to-pem';

// Mock jwkToPem
jest.mock('jwk-to-pem', () => jest.fn());

describe('SsoService', () => {
  let service: SsoService;

  const mockSsoConfigRepository = {
    findOneBy: jest.fn().mockImplementation(() => mockSsoConfig),
    save: jest.fn().mockImplementation(() => mockSsoConfig),
    find: jest.fn().mockImplementation(() => [mockSsoConfig]),
    findOne: jest.fn().mockImplementation(() => mockSsoConfig),
    delete: jest.fn().mockImplementation(() => {
      return { affected: 1 };
    }),
    count: jest.fn().mockImplementation(() => 1),
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

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
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
            decode: jest.fn().mockReturnValue({
              firewall_id: 'test_id',
              firewall_username: 'test_username',
              firewall_role: 'test_role',
            }),
            signAsync: jest.fn(),
            verifyAsync: jest.fn(),
          },
        },
        {
          provide: getLoggerToken(SsoService.name),
          useValue: mockLogger,
        },
      ],
    }).compile();

    service = module.get<SsoService>(SsoService);
  });

  it('should be defined', () => {
    expect(service).toBeDefined();
  });

  describe('addSsoConfig', () => {
    it('should add a new SSO config', async () => {
      const name = 'test';

      jest.spyOn(mockSsoConfigRepository, 'findOneBy').mockResolvedValue(null);
      jest
        .spyOn(mockSsoConfigRepository, 'save')
        .mockResolvedValue(mockSsoConfig);

      expect(await service.addSsoConfig(name, mockAddSsoConfigDto, 1)).toBe(
        mockSsoConfig
      );
    });

    it('should update an existing SSO config', async () => {
      const name = 'test';

      jest
        .spyOn(mockSsoConfigRepository, 'findOneBy')
        .mockResolvedValue(mockSsoConfig);
      jest
        .spyOn(mockSsoConfigRepository, 'save')
        .mockResolvedValue(mockSsoConfig);

      expect(await service.addSsoConfig(name, mockAddSsoConfigDto, 1)).toBe(
        mockSsoConfig
      );
    });

    it('should throw an error if adding SSO config fails', async () => {
      const name = 'test';

      jest
        .spyOn(mockSsoConfigRepository, 'findOneBy')
        .mockRejectedValue(new Error('Failed to add sso config'));

      await expect(
        service.addSsoConfig(name, mockSsoConfig, 1)
      ).rejects.toThrow('Failed to add sso config');
    });
  });

  describe('deleteSsoConfig', () => {
    it('should delete an SSO config', async () => {
      const name = 'test';
      jest
        .spyOn(mockSsoConfigRepository, 'delete')
        .mockResolvedValue({ affected: 1 });

      expect(await service.deleteSsoConfig(name)).toEqual({ affected: 1 });
    });

    it('should throw an error if delete fails', async () => {
      const name = 'test';
      jest
        .spyOn(mockSsoConfigRepository, 'delete')
        .mockRejectedValue(new Error('Failed to delete sso config'));

      await expect(service.deleteSsoConfig(name)).rejects.toThrow(
        'Failed to delete sso config'
      );
    });
  });

  describe('getSsoConfig', () => {
    it('should return an SSO config', async () => {
      const name = 'test';
      jest
        .spyOn(mockSsoConfigRepository, 'findOne')
        .mockResolvedValue(mockSsoConfig);

      expect(await service.getSsoConfig(name, true)).toBe(mockSsoConfig);
    });

    it('should throw an error if getting SSO config fails', async () => {
      const name = 'test';
      jest
        .spyOn(mockSsoConfigRepository, 'findOne')
        .mockRejectedValue(new Error('Failed to get sso config'));

      await expect(service.getSsoConfig(name)).rejects.toThrow(
        'Failed to get sso config'
      );
    });
  });

  describe('getAllSsoConfig', () => {
    it('should return all SSO configs', async () => {
      jest
        .spyOn(mockSsoConfigRepository, 'find')
        .mockResolvedValue([mockSsoConfig]);

      const result = await service.getAllSsoConfig(
        { page: 1, limit: 10 },
        true
      );
      const expectedResult: PaginationResponseDto<SsoConfig> = {
        current_limit: 10,
        current_page: 1,
        data: [mockSsoConfig],
        total_count: 1,
        total_pages: 1,
      };
      expect(result).toEqual(expectedResult);
    });

    it('should throw an error if getting all SSO configs fails', async () => {
      jest
        .spyOn(mockSsoConfigRepository, 'find')
        .mockRejectedValue(new Error('Failed to get sso configs'));

      await expect(
        service.getAllSsoConfig({ page: 1, limit: 10 })
      ).rejects.toThrow('Failed to get sso configs');
    });
  });

  describe('ssoLogin', () => {
    it('should handle SSO register', async () => {
      const name = 'test';
      const code = 'test_code';
      const tokenResponse = { data: { access_token: 'test_token' } };
      const userInfoResponse = {
        data: { email: 'test@example.com', firewall_role: 'admin' },
      };
      const user = {
        id: 1,
        username: 'test',
        userEmail: 'test@example.com',
        role: 'admin',
        active: true,
      };
      const config = mockSsoConfig;
      config.jwksUri = null;

      jest.spyOn(service, 'getSsoConfig').mockResolvedValue(config);
      jest.spyOn(axios, 'post').mockResolvedValue(tokenResponse);
      jest.spyOn(axios, 'get').mockResolvedValue(userInfoResponse);
      jest.spyOn(mockUserRepository, 'findOneBy').mockResolvedValue(null);
      jest.spyOn(mockUserRepository, 'save').mockResolvedValue(user);
      jest
        .spyOn(service['jwtService'], 'signAsync')
        .mockResolvedValue('signed_token');

      expect(await service.ssoLogin(name, code)).toEqual({
        access_token: 'signed_token',
      });
    });

    it('should handle SSO login', async () => {
      const name = 'test';
      const code = 'test_code';
      const tokenResponse = { data: { access_token: 'test_token' } };
      const userInfoResponse = {
        data: { email: 'test@example.com', firewall_role: 'admin' },
      };
      const user = {
        id: 1,
        username: 'test',
        userEmail: 'test@example.com',
        role: 'admin',
        active: true,
      };
      const config = mockSsoConfig;
      config.jwksUri = null;

      jest.spyOn(service, 'getSsoConfig').mockResolvedValue(config);
      jest.spyOn(axios, 'post').mockResolvedValue(tokenResponse);
      jest.spyOn(axios, 'get').mockResolvedValue(userInfoResponse);
      jest.spyOn(mockUserRepository, 'findOneBy').mockResolvedValue(mockUser);
      jest.spyOn(mockUserRepository, 'save').mockResolvedValue(user);
      jest
        .spyOn(service['jwtService'], 'signAsync')
        .mockResolvedValue('signed_token');

      expect(await service.ssoLogin(name, code)).toEqual({
        access_token: 'signed_token',
      });
    });

    it('should throw an error if SSO config is not found', async () => {
      const name = 'test';
      const code = 'test_code';
      jest.spyOn(service, 'getSsoConfig').mockResolvedValue(null);

      await expect(service.ssoLogin(name, code)).rejects.toThrow(
        BadRequestException
      );
    });

    it('should throw an error if authentication fails', async () => {
      const name = 'test';
      const code = 'test_code';

      jest.spyOn(service, 'getSsoConfig').mockResolvedValue(mockSsoConfig);
      jest
        .spyOn(axios, 'post')
        .mockRejectedValue(new Error('Failed to authenticate'));

      await expect(service.ssoLogin(name, code)).rejects.toThrow(
        'Failed to authenticate with sso'
      );
    });

    it('should validate id token', async () => {
      const name = 'test';
      const code = 'test_code';
      const tokenResponse = {
        data: { access_token: 'test_token', id_token: 'test_token' },
      };
      const axiosGetResponse = {
        data: {
          email: 'test@example.com',
          firewall_role: 'admin',
          keys: [{ kid: 'kid' }],
        },
      };
      const user = {
        id: 1,
        username: 'test',
        userEmail: 'test@example.com',
        role: 'admin',
        active: true,
      };
      const decodedPayload = { header: { kid: 'kid' } };
      const config = mockSsoConfig;
      config.jwksUri = 'test_url';

      jest.spyOn(service, 'getSsoConfig').mockResolvedValue(config);
      jest.spyOn(axios, 'post').mockResolvedValue(tokenResponse);
      jest
        .spyOn(service['jwtService'], 'decode')
        .mockImplementation(() => decodedPayload);
      jest.spyOn(axios, 'get').mockResolvedValue(axiosGetResponse);
      jest.spyOn(mockUserRepository, 'findOneBy').mockResolvedValue(mockUser);
      jest.spyOn(mockUserRepository, 'save').mockResolvedValue(user);
      jest
        .spyOn(service['jwtService'], 'verifyAsync')
        .mockResolvedValue(new Promise((res) => res(user)));
      jest
        .spyOn(service['jwtService'], 'signAsync')
        .mockResolvedValue('signed_token');

      expect(await service.ssoLogin(name, code)).toEqual({
        access_token: 'signed_token',
      });
    });

    it('should throw inactive user error', async () => {
      const name = 'test';
      const code = 'test_code';
      const tokenResponse = { data: { access_token: 'test_token' } };
      const userInfoResponse = {
        data: { email: 'test@example.com', firewall_role: 'admin' },
      };
      const user = {
        id: 1,
        username: 'test',
        userEmail: 'test@example.com',
        role: 'admin',
        active: false,
      };
      const config = mockSsoConfig;
      config.jwksUri = null;

      jest.spyOn(service, 'getSsoConfig').mockResolvedValue(config);
      jest.spyOn(axios, 'post').mockResolvedValue(tokenResponse);
      jest.spyOn(axios, 'get').mockResolvedValue(userInfoResponse);
      jest.spyOn(mockUserRepository, 'findOneBy').mockResolvedValue(mockUser);
      jest.spyOn(mockUserRepository, 'save').mockResolvedValue(user);
      jest
        .spyOn(service['jwtService'], 'signAsync')
        .mockResolvedValue('signed_token');

      await expect(service.ssoLogin(name, code)).rejects.toThrow(
        'Cant login in active user, contact admin'
      );
    });
  });
});
