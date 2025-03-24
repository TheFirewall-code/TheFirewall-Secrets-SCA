import { AddSsoConfigDto } from '../dto/add-sso-config.dto';
import { SsoConfig } from '../entities/sso-config.entity';
import { SsoConfigType } from '../enums/sso-config-type.enum';

export const mockSsoConfig: SsoConfig = {
  authorizationUrl: 'test',
  callbackUrl: 'test',
  clientId: 'test',
  clientSecret: 'test',
  issuer: 'test',
  tokenUrl: 'test',
  type: SsoConfigType.Okta,
  userInfoUrl: 'test',
  jwksUri: 'test',
  id: 1,
  name: 'test_name',
  createdAt: new Date(),
  updatedAt: new Date(),
  addedByUid: 1,
  updatedByUid: 1,
};

export const mockAddSsoConfigDto: AddSsoConfigDto = {
  authorizationUrl: 'test',
  callbackUrl: 'test',
  clientId: 'test',
  clientSecret: 'test',
  issuer: 'test',
  tokenUrl: 'test',
  type: SsoConfigType.Okta,
  userInfoUrl: 'test',
  jwksUri: 'test',
};
