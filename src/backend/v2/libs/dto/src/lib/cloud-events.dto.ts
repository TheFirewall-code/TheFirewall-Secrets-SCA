import { AssetType, VulnerabilityProfiles } from '@firewall-backend/enums';
import { IsEnum, IsInt, IsOptional, IsString } from 'class-validator';

export class AssetEventData {
  @IsInt()
  assetId!: number;

  @IsString()
  assetName!: string;

  @IsEnum(AssetType)
  assetType!: AssetType;

  @IsOptional()
  @IsEnum(VulnerabilityProfiles, { each: true })
  profiles?: VulnerabilityProfiles[];

  @IsOptional()
  @IsInt()
  configurationId?: number = 1;
}
