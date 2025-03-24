import { Test, TestingModule } from '@nestjs/testing';
import { AuthService } from './auth.service';
import { getRepositoryToken } from '@nestjs/typeorm';
import { User } from '../user/entities/user.entity';
import { Repository } from 'typeorm';
import { JwtService } from '@nestjs/jwt';
import { getLoggerToken } from 'nestjs-pino';
import { Bcrypt } from '@firewall-backend/utils';
import { ResetPasswordDto } from './dto/auth.dto';
import { LoginDto } from './dto/auth.dto';
import {
  BadRequestException,
  NotFoundException,
  UnauthorizedException,
} from '@nestjs/common';
import { mockUser } from '../user/mock/user.mock';

describe('AuthService', () => {
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

  let service: AuthService;
  let userRepository: Repository<User>;
  let jwtService: JwtService;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      providers: [
        AuthService,
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
          provide: getLoggerToken(AuthService.name),
          useValue: mockLogger,
        },
      ],
    }).compile();

    service = module.get<AuthService>(AuthService);
    userRepository = module.get<Repository<User>>(getRepositoryToken(User));
    jwtService = module.get<JwtService>(JwtService);
  });

  it('should be defined', () => {
    expect(service).toBeDefined();
  });

  describe('checkIfFirstLogin', () => {
    it('should return true if it is the first login', async () => {
      const user = { ...mockUser, username: 'admin' };
      jest.spyOn(userRepository, 'findOneBy').mockResolvedValue(user);
      jest.spyOn(Bcrypt.prototype, 'compare').mockResolvedValue(true);

      expect(await service.checkIfFirstLogin()).toBe(true);
      expect(userRepository.findOneBy).toHaveBeenCalledWith({
        username: 'admin',
      });
      expect(Bcrypt.prototype.compare).toHaveBeenCalledWith(
        'admin',
        user.hashedPassword
      );
    });

    it('should return false if it is not the first login', async () => {
      const user = { ...mockUser, username: 'admin' };
      jest.spyOn(userRepository, 'findOneBy').mockResolvedValue(user);
      jest.spyOn(Bcrypt.prototype, 'compare').mockResolvedValue(false);

      expect(await service.checkIfFirstLogin()).toBe(false);
      expect(userRepository.findOneBy).toHaveBeenCalledWith({
        username: 'admin',
      });
      expect(Bcrypt.prototype.compare).toHaveBeenCalledWith(
        'admin',
        user.hashedPassword
      );
    });

    it('should return false if admin user does not exist', async () => {
      jest.spyOn(userRepository, 'findOneBy').mockResolvedValue(null);

      expect(await service.checkIfFirstLogin()).toBe(false);
      expect(userRepository.findOneBy).toHaveBeenCalledWith({
        username: 'admin',
      });
    });
  });

  describe('updateUserPassword', () => {
    it('should update the user password', async () => {
      const userId = 1;
      const newPassword = 'new_password';
      const currentUserId = 1;
      const hashedPassword = 'new_hashed_password';
      const updatedUser = { ...mockUser, hashedPassword };

      jest.spyOn(userRepository, 'findOneBy').mockResolvedValue(mockUser);
      jest.spyOn(Bcrypt.prototype, 'hash').mockResolvedValue(hashedPassword);
      jest.spyOn(userRepository, 'save').mockResolvedValue(updatedUser);

      expect(
        await service.updateUserPassword(userId, newPassword, currentUserId)
      ).toEqual(updatedUser);
      expect(userRepository.findOneBy).toHaveBeenCalledWith({ id: userId });
      expect(Bcrypt.prototype.hash).toHaveBeenCalledWith(newPassword);
      expect(userRepository.save).toHaveBeenCalledWith({
        ...mockUser,
        hashedPassword,
        updatedByUid: currentUserId,
      });
    });

    it('should throw NotFoundException if user not found', async () => {
      const userId = 1;
      const newPassword = 'new_password';
      const currentUserId = 1;

      jest.spyOn(userRepository, 'findOneBy').mockResolvedValue(null);

      await expect(
        service.updateUserPassword(userId, newPassword, currentUserId)
      ).rejects.toThrow(NotFoundException);
      expect(userRepository.findOneBy).toHaveBeenCalledWith({ id: userId });
    });
  });

  describe('resetAdminPassword', () => {
    it('should reset the admin password', async () => {
      const resetPasswordDto: ResetPasswordDto = {
        newPassword: 'new_password',
      };
      const updatedUser = {
        ...mockUser,
        hashedPassword: 'new_hashed_password',
      };

      jest.spyOn(service, 'checkIfFirstLogin').mockResolvedValue(true);
      jest.spyOn(userRepository, 'findOneBy').mockResolvedValue(mockUser);
      jest.spyOn(service, 'updateUserPassword').mockResolvedValue(updatedUser);

      expect(await service.resetAdminPassword(resetPasswordDto)).toEqual(
        updatedUser
      );
      expect(service.checkIfFirstLogin).toHaveBeenCalled();
      expect(userRepository.findOneBy).toHaveBeenCalledWith({
        username: 'admin',
      });
      expect(service.updateUserPassword).toHaveBeenCalledWith(
        mockUser.id,
        resetPasswordDto.newPassword,
        new User().id
      );
    });

    it('should throw BadRequestException if admin password already updated', async () => {
      const resetPasswordDto: ResetPasswordDto = {
        newPassword: 'new_password',
      };

      jest.spyOn(service, 'checkIfFirstLogin').mockResolvedValue(false);

      await expect(
        service.resetAdminPassword(resetPasswordDto)
      ).rejects.toThrow(BadRequestException);
      expect(service.checkIfFirstLogin).toHaveBeenCalled();
    });

    it('should throw NotFoundException if admin user not found', async () => {
      const resetPasswordDto: ResetPasswordDto = {
        newPassword: 'new_password',
      };

      jest.spyOn(service, 'checkIfFirstLogin').mockResolvedValue(true);
      jest.spyOn(userRepository, 'findOneBy').mockResolvedValue(null);

      await expect(
        service.resetAdminPassword(resetPasswordDto)
      ).rejects.toThrow(NotFoundException);
      expect(service.checkIfFirstLogin).toHaveBeenCalled();
      expect(userRepository.findOneBy).toHaveBeenCalledWith({
        username: 'admin',
      });
    });
  });

  describe('authenticateUser', () => {
    it('should authenticate the user', async () => {
      const loginDto: LoginDto = {
        username: 'test-user',
        password: 'password',
      };
      const accessToken = 'access_token';

      jest.spyOn(userRepository, 'findOneBy').mockResolvedValue(mockUser);
      jest.spyOn(Bcrypt.prototype, 'compare').mockResolvedValue(true);
      jest.spyOn(jwtService, 'signAsync').mockResolvedValue(accessToken);

      expect(await service.authenticateUser(loginDto)).toEqual({
        access_token: accessToken,
      });
      expect(userRepository.findOneBy).toHaveBeenCalledWith({
        username: loginDto.username,
      });
      expect(Bcrypt.prototype.compare).toHaveBeenCalledWith(
        loginDto.password,
        mockUser.hashedPassword
      );
      expect(jwtService.signAsync).toHaveBeenCalledWith({
        user_id: mockUser.id,
        username: mockUser.username,
        role: mockUser.role,
      });
    });

    it('should throw NotFoundException if user not found', async () => {
      const loginDto: LoginDto = {
        username: 'test-user',
        password: 'password',
      };

      jest.spyOn(userRepository, 'findOneBy').mockResolvedValue(null);

      await expect(service.authenticateUser(loginDto)).rejects.toThrow(
        NotFoundException
      );
      expect(userRepository.findOneBy).toHaveBeenCalledWith({
        username: loginDto.username,
      });
    });

    it('should throw UnauthorizedException if password is incorrect', async () => {
      const loginDto: LoginDto = {
        username: 'test-user',
        password: 'password',
      };

      jest.spyOn(userRepository, 'findOneBy').mockResolvedValue(mockUser);
      jest.spyOn(Bcrypt.prototype, 'compare').mockResolvedValue(false);

      await expect(service.authenticateUser(loginDto)).rejects.toThrow(
        UnauthorizedException
      );
      expect(userRepository.findOneBy).toHaveBeenCalledWith({
        username: loginDto.username,
      });
      expect(Bcrypt.prototype.compare).toHaveBeenCalledWith(
        loginDto.password,
        mockUser.hashedPassword
      );
    });

    it('should throw BadRequestException if user is not active', async () => {
      const loginDto: LoginDto = {
        username: 'test-user',
        password: 'password',
      };
      const user = { ...mockUser, active: false };

      jest.spyOn(userRepository, 'findOneBy').mockResolvedValue(user);
      jest.spyOn(Bcrypt.prototype, 'compare').mockResolvedValue(true);

      await expect(service.authenticateUser(loginDto)).rejects.toThrow(
        BadRequestException
      );
      expect(userRepository.findOneBy).toHaveBeenCalledWith({
        username: loginDto.username,
      });
      expect(Bcrypt.prototype.compare).toHaveBeenCalledWith(
        loginDto.password,
        user.hashedPassword
      );
    });
  });

  describe('resetPassword', () => {
    it('should reset the user password', async () => {
      const userId = 1;
      const resetPasswordDto: ResetPasswordDto = {
        newPassword: 'new_password',
      };
      const currentUserId = 1;
      const updatedUser = {
        ...mockUser,
        hashedPassword: 'new_hashed_password',
      };

      jest.spyOn(userRepository, 'findOneBy').mockResolvedValue(mockUser);
      jest.spyOn(service, 'updateUserPassword').mockResolvedValue(updatedUser);

      expect(
        await service.resetPassword(userId, resetPasswordDto, currentUserId)
      ).toEqual(updatedUser);
      expect(userRepository.findOneBy).toHaveBeenCalledWith({ id: userId });
      expect(service.updateUserPassword).toHaveBeenCalledWith(
        mockUser.id,
        resetPasswordDto.newPassword,
        currentUserId
      );
    });

    it('should throw NotFoundException if user not found', async () => {
      const userId = 1;
      const resetPasswordDto: ResetPasswordDto = {
        newPassword: 'new_password',
      };
      const currentUserId = 1;

      jest.spyOn(userRepository, 'findOneBy').mockResolvedValue(null);

      await expect(
        service.resetPassword(userId, resetPasswordDto, currentUserId)
      ).rejects.toThrow(NotFoundException);
      expect(userRepository.findOneBy).toHaveBeenCalledWith({ id: userId });
    });
  });
});
