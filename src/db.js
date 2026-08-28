import Database from "better-sqlite3";
import { mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";

const dataDir = fileURLToPath(new URL("../data", import.meta.url));
mkdirSync(dataDir, { recursive: true });
export const db = new Database(fileURLToPath(new URL("../data/jee.db", import.meta.url)));

db.pragma("journal_mode = WAL");

db.exec(`
  CREATE TABLE IF NOT EXISTS concepts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    subject TEXT NOT NULL,
    created_at INTEGER NOT NULL
  );

  CREATE TABLE IF NOT EXISTS attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    concept_id INTEGER NOT NULL REFERENCES concepts(id),
    result TEXT NOT NULL CHECK (result IN ('correct', 'wrong', 'unattempted')),
    time_seconds INTEGER,
    created_at INTEGER NOT NULL
  );

  CREATE TABLE IF NOT EXISTS error_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT
  );

  CREATE TABLE IF NOT EXISTS attempt_errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    attempt_id INTEGER NOT NULL REFERENCES attempts(id),
    error_type_id INTEGER NOT NULL REFERENCES error_types(id),
    notes TEXT
  );
`);

const seedErrorType = db.prepare(
  `INSERT OR IGNORE INTO error_types (name) VALUES (?)`
);
for (const name of [
  "concept_gap",
  "calculation",
  "misread",
  "time_pressure",
  "unattempted",
  "unknown",
]) {
  seedErrorType.run(name);
}

function normalize(name) {
  return name.toLowerCase().replace(/[^a-z0-9]/g, "");
}

export function findOrCreateConcept(name, subject) {
  const target = normalize(name);
  const existing = db
    .prepare(`SELECT id, name FROM concepts WHERE subject = ?`)
    .all(subject)
    .find((c) => normalize(c.name) === target);

  if (existing) return existing.id;

  return db
    .prepare(
      `INSERT INTO concepts (name, subject, created_at) VALUES (?, ?, ?)`
    )
    .run(name, subject, Date.now()).lastInsertRowid;
}

export function listConcepts(subject) {
  return db
    .prepare(`SELECT id, name FROM concepts WHERE subject = ? ORDER BY name`)
    .all(subject);
}
