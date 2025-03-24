import {
  Controller,
  Get,
  Post,
  Body,
  Param,
  Delete,
  UseGuards,
  Req,
  Query,
  Put,
} from '@nestjs/common';
import { UserService } from './user.service';
import { CreateUserDto } from './dto/create-user.dto';
import { UpdateUserDto } from './dto/update-user.dto';
import { AuthGuard, RolesGuard } from '@firewall-backend/guards';
import { Roles } from '@firewall-backend/decorators';
import { UserRole } from '@firewall-backend/enums';
import { Request } from 'express';
import { GetUsersQueryDto } from './dto/get-user.dto';
import { UserIdParamsDto } from './dto/get-user.dto';
import { ApiBearerAuth, ApiTags } from '@nestjs/swagger';

@ApiBearerAuth()
@ApiTags('User')
@Controller('user')
@UseGuards(AuthGuard)
export class UserController {
  constructor(private readonly userService: UserService) {}

  @Post()
  @Roles(UserRole.Admin)
  @UseGuards(RolesGuard)
  createNewUser(@Body() createUserDto: CreateUserDto, @Req() req: Request) {
    return this.userService.createUser(createUserDto, req.user.user_id);
  }

  @Get()
  @Roles(UserRole.Admin, UserRole.User)
  @UseGuards(RolesGuard)
  getUsers(@Query() query: GetUsersQueryDto) {
    return this.userService.getAllUsers(query);
  }

  @Get('/self')
  getSelfUser(@Req() req: Request) {
    return this.userService.getUserById(req.user.user_id);
  }

  @Get(':user_id')
  @Roles(UserRole.Admin)
  @UseGuards(RolesGuard)
  readUser(@Param() params: UserIdParamsDto) {
    return this.userService.getUserById(params.user_id);
  }

  @Put(':user_id')
  @Roles(UserRole.Admin)
  @UseGuards(RolesGuard)
  updateExistingUser(
    @Param() params: UserIdParamsDto,
    @Body() updateUserDto: UpdateUserDto,
    @Req() req: Request
  ) {
    return this.userService.updateUser(
      params.user_id,
      updateUserDto,
      req.user.user_id
    );
  }

  @Delete(':user_id')
  @Roles(UserRole.Admin)
  @UseGuards(RolesGuard)
  softDeleteUser(@Param() params: UserIdParamsDto, @Req() req: Request) {
    return this.userService.deleteUser(params.user_id, req.user.user_id);
  }
}
