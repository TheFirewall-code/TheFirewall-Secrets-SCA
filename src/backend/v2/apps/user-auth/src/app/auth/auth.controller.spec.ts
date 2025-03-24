import { Test, TestingModule } from '@nestjs/testing';
import { AuthController } from './auth.controller';
import { AuthService } from './auth.service';
import { LoginDto } from './dto/auth.dto';
import { ResetPasswordDto } from './dto/auth.dto';
import { UserIdParamsDto } from './dto/auth.dto';
import { Request } from 'express';
import { mockUser } from '../user/mock/user.mock';
import { getRepositoryToken } from '@nestjs/typeorm';
import { User } from '../user/entities/user.entity';
import { JwtService } from '@nestjs/jwt';
import { getLoggerToken } from 'nestjs-pino';

describe('AuthController', () => {
  const mockAuthService = {
    checkIfFirstLogin: jest.fn(),
    resetAdminPassword: jest.fn(),
    authenticateUser: jest.fn(),
    resetPassword: jest.fn(),
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

  let controller: AuthController;
  let service: AuthService;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      controllers: [AuthController],
      providers: [
        {
          provide: AuthService,
          useValue: mockAuthService,
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
            decode: jest.fn(),
            signAsync: jest.fn(),
          },
        },
        {
          provide: getLoggerToken(AuthController.name),
          useValue: mockLogger,
        },
      ],
    }).compile();

    controller = module.get<AuthController>(AuthController);
    service = module.get<AuthService>(AuthService);
  });

  it('should be defined', () => {
    expect(controller).toBeDefined();
  });

  describe('checkFirstLogin', () => {
    it('should check if it is the first login', async () => {
      const result = true;
      jest.spyOn(service, 'checkIfFirstLogin').mockResolvedValue(result);

      expect(await controller.checkFirstLogin()).toEqual(result);
      expect(service.checkIfFirstLogin).toHaveBeenCalled();
    });
  });

  describe('resetAdminPassword', () => {
    it('should reset the admin password', async () => {
      const resetPasswordDto: ResetPasswordDto = {
        newPassword: 'new_password',
      };
      jest.spyOn(service, 'resetAdminPassword').mockResolvedValue(mockUser);

      expect(await controller.resetAdminPassword(resetPasswordDto)).toEqual(
        mockUser
      );
      expect(service.resetAdminPassword).toHaveBeenCalledWith(resetPasswordDto);
    });
  });

  describe('login', () => {
    it('should authenticate the user', async () => {
      const loginDto: LoginDto = {
        username: 'test-user',
        password: 'password',
      };
      const result = { access_token: 'token' };
      jest.spyOn(service, 'authenticateUser').mockResolvedValue(result);

      expect(await controller.login(loginDto)).toEqual(result);
      expect(service.authenticateUser).toHaveBeenCalledWith(loginDto);
    });
  });

  describe('resetPassword', () => {
    it('should reset the user password', async () => {
      const resetPasswordDto: ResetPasswordDto = {
        newPassword: 'new_password',
      };
      const req = { user: { user_id: 1 } } as Request;
      jest.spyOn(service, 'resetPassword').mockResolvedValue(mockUser);

      expect(await controller.resetPassword(resetPasswordDto, req)).toEqual(
        mockUser
      );
      expect(service.resetPassword).toHaveBeenCalledWith(
        req.user.user_id,
        resetPasswordDto,
        req.user.user_id
      );
    });
  });

  describe('resetPasswordById', () => {
    it('should reset the password for a specific user', async () => {
      const params: UserIdParamsDto = { user_id: 1 };
      const resetPasswordDto: ResetPasswordDto = {
        newPassword: 'new_password',
      };
      const req = { user: { user_id: 1 } } as Request;
      jest.spyOn(service, 'resetPassword').mockResolvedValue(mockUser);

      expect(
        await controller.resetPasswordById(params, resetPasswordDto, req)
      ).toEqual(mockUser);
      expect(service.resetPassword).toHaveBeenCalledWith(
        params.user_id,
        resetPasswordDto,
        req.user.user_id
      );
    });
  });
});
