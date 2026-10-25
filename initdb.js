// Run once with: npm run initdb
require('dotenv').config();
const fs = require('fs');
const path = require('path');
const mysql = require('mysql2/promise');

async function main() {
  const connection = await mysql.createConnection({
    host: process.env.DB_HOST || 'localhost',
    port: process.env.DB_PORT || 3306,
    user: process.env.DB_USER || 'root',
    password: process.env.DB_PASSWORD || '',
    multipleStatements: true,
  });

  const sql = fs.readFileSync(path.join(__dirname, 'schema.sql'), 'utf8');
  await connection.query(sql);
  console.log('Database, tables and the 8 subjects are ready.');
  await connection.end();
}

main().catch((err) => {
  console.error('Failed to initialize database:', err.message);
  process.exit(1);
});
