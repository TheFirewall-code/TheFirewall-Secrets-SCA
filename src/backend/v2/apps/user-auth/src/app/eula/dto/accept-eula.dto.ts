import { IsBoolean } from 'class-validator';

export class AcceptEulaDto {
  @IsBoolean()
  accepted: boolean;
}
