import { MigrationInterface, QueryRunner } from 'typeorm';

export class Migration1737997572654 implements MigrationInterface {
  name = 'Migration1737997572654';

  public async up(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(`
            ALTER TABLE "sso_config"
            ALTER COLUMN "jwks_uri" DROP NOT NULL
        `);
  }

  public async down(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(`
            ALTER TABLE "sso_config"
            ALTER COLUMN "jwks_uri"
            SET NOT NULL
        `);
  }
}
