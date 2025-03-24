import { MigrationInterface, QueryRunner } from 'typeorm';

export class Migration1738604071838 implements MigrationInterface {
  public async up(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(`
      CREATE TABLE eula (
        id SERIAL PRIMARY KEY,
        accepted BOOLEAN DEFAULT FALSE NOT NULL,
        accepted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
      );
    `);

    await queryRunner.query(`
      INSERT INTO eula (id, accepted, accepted_at, created_at)
      VALUES (1, false, NULL, CURRENT_TIMESTAMP);
    `);
  }

  public async down(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(`DROP TABLE eula;`);
  }
}
