import { MigrationInterface, QueryRunner } from 'typeorm';

export class Migration1738820433484 implements MigrationInterface {
  public async up(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(`
            ALTER TABLE users
            ALTER COLUMN user_email DROP NOT NULL;
        `);
  }

  public async down(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(`
            ALTER TABLE users
            ALTER COLUMN user_email SET NOT NULL;
        `);
  }
}
