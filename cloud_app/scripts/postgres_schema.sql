-- Cardio Vita Clinic PostgreSQL schema
-- Run this in Supabase or Neon SQL editor.

CREATE TABLE IF NOT EXISTS users (
  id BIGSERIAL PRIMARY KEY,
  username TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('admin', 'manager', 'staff', 'doctor')),
  branch TEXT,
  doctor_name TEXT,
  active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL
);

ALTER TABLE users DROP CONSTRAINT IF EXISTS users_role_check;
ALTER TABLE users ADD CONSTRAINT users_role_check CHECK (role IN ('admin', 'manager', 'staff', 'doctor'));

CREATE TABLE IF NOT EXISTS sessions (
  token TEXT PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  expires_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS patients (
  id BIGSERIAL PRIMARY KEY,
  anketa_number TEXT NOT NULL UNIQUE,
  visit_date TEXT NOT NULL,
  branch TEXT NOT NULL,
  first_name TEXT NOT NULL,
  last_name TEXT NOT NULL,
  father_name TEXT,
  birth_date TEXT,
  passport TEXT,
  phone TEXT,
  email TEXT,
  status TEXT,
  payment TEXT,
  notes TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS appointments (
  id BIGSERIAL PRIMARY KEY,
  appointment_date TEXT NOT NULL,
  appointment_time TEXT NOT NULL,
  branch TEXT NOT NULL,
  doctor TEXT NOT NULL,
  anketa_number TEXT,
  patient_name TEXT,
  passport TEXT,
  phone TEXT,
  status TEXT NOT NULL,
  notes TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE (appointment_date, appointment_time, doctor)
);

CREATE TABLE IF NOT EXISTS holters (
  id BIGSERIAL PRIMARY KEY,
  anketa_number TEXT NOT NULL,
  patient_name TEXT,
  phone TEXT,
  branch TEXT,
  provided_date TEXT NOT NULL,
  provided_time TEXT NOT NULL,
  duration_hours INTEGER NOT NULL CHECK (duration_hours IN (24, 48, 72)),
  return_at TEXT NOT NULL,
  provided_status TEXT,
  return_status TEXT,
  actual_return TEXT,
  notes TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS service_orders (
  id BIGSERIAL PRIMARY KEY,
  anketa_number TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('general', 'lab')),
  branch TEXT,
  doctor TEXT,
  category TEXT,
  service_name TEXT NOT NULL,
  price INTEGER NOT NULL DEFAULT 0,
  status TEXT,
  notes TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS doctors (
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  specialty TEXT,
  active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS audit_log (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT,
  action TEXT NOT NULL,
  entity TEXT NOT NULL,
  entity_id TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS doctor_notes (
  id BIGSERIAL PRIMARY KEY,
  anketa_number TEXT NOT NULL,
  doctor TEXT NOT NULL,
  note_type TEXT NOT NULL DEFAULT 'Ախտորոշում',
  complaints TEXT,
  diagnosis TEXT,
  prescription TEXT,
  notes TEXT,
  created_by BIGINT REFERENCES users(id),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_patients_branch_visit ON patients(branch, visit_date);
CREATE INDEX IF NOT EXISTS idx_appointments_branch_date ON appointments(branch, appointment_date);
CREATE INDEX IF NOT EXISTS idx_appointments_doctor_date_time ON appointments(doctor, appointment_date, appointment_time);
CREATE INDEX IF NOT EXISTS idx_services_branch_kind ON service_orders(branch, kind);
CREATE INDEX IF NOT EXISTS idx_holters_branch_return_at ON holters(branch, return_at);
CREATE INDEX IF NOT EXISTS idx_holters_return_at ON holters(return_at);
CREATE INDEX IF NOT EXISTS idx_sessions_expiry ON sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_doctor_notes_anketa ON doctor_notes(anketa_number);
CREATE INDEX IF NOT EXISTS idx_doctor_notes_doctor_created ON doctor_notes(doctor, created_at);

INSERT INTO doctors (name, specialty) VALUES
  ('Ազնիվ Գևորգյան', 'Սրտաբան'),
  ('Սիրանուշ Գրիգորյան', 'Սրտաբան'),
  ('Բակուր Վարդանյան', 'Բժիշկ'),
  ('Արմեն Շահբազյան', 'Բժիշկ'),
  ('Ալլա Աբովյան', 'Սրտաբան'),
  ('Սոֆյա Խաչատրյան', 'Բժիշկ'),
  ('Մելինա Խաչատրյան', 'Բժիշկ'),
  ('Լյուբա Արզումանյան', 'Բժիշկ'),
  ('Արմինե Հովհաննիսյան', 'Բժիշկ'),
  ('Մակարյան Գայանե', 'Ռևմատոլոգ'),
  ('Ասլիկյան Աննա', 'Բժիշկ-լաբորանտ')
ON CONFLICT (name) DO NOTHING;
