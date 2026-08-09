-- Cardio Vita Clinic Supabase full setup
-- Run this whole file in Supabase SQL Editor.
--
-- It creates tables, indexes, doctors, and login users.
-- It is safe to run more than once.
--
-- Temporary password for seeded users:
--   ChangeMe2026!
--
-- IMPORTANT:
-- Change passwords before using real patient data.

CREATE TABLE IF NOT EXISTS users (
  id BIGSERIAL PRIMARY KEY,
  username TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('admin', 'staff', 'doctor')),
  branch TEXT,
  doctor_name TEXT,
  active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL
);

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

-- Main full-system admin.
INSERT INTO users (username, password_hash, role, branch, doctor_name, active, created_at) VALUES
  ('admin', 'T+Gyb8aLCp2+S30+3yoH0v+D59qmErCpJht7ONTRHAlKuiGr5nBr+fPC4LahlsHQ', 'admin', NULL, NULL, 1, NOW()::text)
ON CONFLICT (username) DO UPDATE SET
  password_hash = EXCLUDED.password_hash,
  role = EXCLUDED.role,
  branch = EXCLUDED.branch,
  doctor_name = EXCLUDED.doctor_name,
  active = EXCLUDED.active;

-- Branch staff users.
INSERT INTO users (username, password_hash, role, branch, doctor_name, active, created_at) VALUES
  ('mane.barseghyan', 'jTFlRfSjB95CdPESvHsooriSiLkYz3URvLKpw5mraSj0h+u7QMdOv1NmjdxRpNdi', 'staff', 'Նարեկացի', NULL, 1, NOW()::text),
  ('milena.ashabeyan', 'IsIyTe7L+ayq4oI8P4xfvkXD2shUm+yowKpkzruN4ptbK5vB6XASE0Q1NgWhuIXy', 'staff', 'Նարեկացի', NULL, 1, NOW()::text),
  ('lusine.teryan', '+r/dHsCmUkofr+j3cnfuENu+ZmODVq2NG9GBlJaq2Kw1qA8ahloby25NAE8y5BYa', 'staff', 'Տերյան', NULL, 1, NOW()::text),
  ('siranush.teryan', '9M0CjLvjVhvoQbQT6rL3iHAmP83JVxn/Ot6JFw9wK/T2FjGBGM3cx41fMyAGw5od', 'staff', 'Տերյան', NULL, 1, NOW()::text),
  ('gohar.teryan', '4z9Vh3VO6LiYLDMY0XVfTt9j0A955Sw1rJ9SC5y/KJpKzcghuFmwMYYesPUQ3X7/', 'staff', 'Տերյան', NULL, 1, NOW()::text)
ON CONFLICT (username) DO UPDATE SET
  password_hash = EXCLUDED.password_hash,
  role = EXCLUDED.role,
  branch = EXCLUDED.branch,
  doctor_name = EXCLUDED.doctor_name,
  active = EXCLUDED.active;

-- Doctors.
INSERT INTO doctors (name, specialty, active) VALUES
  ('Ազնիվ Գևորգյան', 'Սրտաբան', 1),
  ('Ալլա Աբովյան', 'Սրտաբան', 1),
  ('Սիրանուշ Գրիգորյան', 'Սրտաբան', 1),
  ('Սոֆյա Խաչատրյան', 'Սոնոգրաֆիստ', 1),
  ('Մելինա Խաչատրյան', 'Նյարդաբան', 1),
  ('Լյուբա Արզումանյան', 'Ճառագայթային ախտորոշման մասնագետ', 1),
  ('Բակուր Վարդանյան', 'Սրտաբան', 1),
  ('Արմեն Շահբազյան', 'Սրտաբան', 1),
  ('Մակարյան Գայանե', 'Ռևմատոլոգ', 1),
  ('Ասլիկյան Աննա', 'Բժիշկ-լաբորանտ', 1)
ON CONFLICT (name) DO UPDATE SET
  specialty = EXCLUDED.specialty,
  active = EXCLUDED.active;

-- Doctor login users.
INSERT INTO users (username, password_hash, role, branch, doctor_name, active, created_at) VALUES
  ('azniv.gevorgyan', 'PR5MoHAqAlWVYH5BUFoMMV3Wxn02p9ltjV5gGctcOe0gNcvqgd7cN7cROB2/ASlB', 'doctor', NULL, 'Ազնիվ Գևորգյան', 1, NOW()::text),
  ('alla.abovyan', 'XxfclYb4ITH7PGc4qd2A/Xc2XGs9Oeh2///TOiDdtxqmTLomKRD28d1YeUri/Qj4', 'doctor', NULL, 'Ալլա Աբովյան', 1, NOW()::text),
  ('siranush.grigoryan', '3W2NCUdR9ExI6MpxB0vpsszBcWF8hXp0FjlAU74+ji5TR1oqQ16ZPwvzk9kx4NYP', 'doctor', NULL, 'Սիրանուշ Գրիգորյան', 1, NOW()::text),
  ('sofya.khachatryan', 'A42zAu4Ik4hVwrFcx1zQHITwu+f6NWc/ytkidSn8ZMzLqxGOhoeELiPfkDEACkkU', 'doctor', NULL, 'Սոֆյա Խաչատրյան', 1, NOW()::text),
  ('melina.khachatryan', 'h6VNT1JYd92T5w9Ir/L3IfKSsfw3LWqHd1IBueW3oySRCTED6JaLVy8+SnVpZKYj', 'doctor', NULL, 'Մելինա Խաչատրյան', 1, NOW()::text),
  ('lyuba.arzumanyan', 'qVnRqAah8zBucQ2AHs0EBwjjn+scofR5iHXnrI8q4Q0S2+MOWbkE9tbQsdDtWVsJ', 'doctor', NULL, 'Լյուբա Արզումանյան', 1, NOW()::text),
  ('bakur.vardanyan', '7J7kDhMN/a4xKAr+GZXL7YriGYGSemUQSe5Jj7jjJcEJrDknK6KyvEs8jJXoWyqF', 'doctor', NULL, 'Բակուր Վարդանյան', 1, NOW()::text),
  ('armen.shahbazyan', 'qKKj3j7lDRlFxT1m3KOUG1rv5flkm45ryYaYR3d0EPfA6qsjnzaCbi5v9SXXZuG/', 'doctor', NULL, 'Արմեն Շահբազյան', 1, NOW()::text),
  ('gayane.makaryan', 'divAQqQOZi8f/+LB/cRfw5PEF9koFqtXGyFY1DWBvsX2jPXLffRwIStvKsY3BfLK', 'doctor', NULL, 'Մակարյան Գայանե', 1, NOW()::text),
  ('anna.aslikyan', 'xpsnrKjdGz0Q17mGzUjJ7pf0HHCkOhiXZmJkjRQgQ7U072MQcGJMEaN69f0AsynF', 'doctor', NULL, 'Ասլիկյան Աննա', 1, NOW()::text)
ON CONFLICT (username) DO UPDATE SET
  password_hash = EXCLUDED.password_hash,
  role = EXCLUDED.role,
  branch = EXCLUDED.branch,
  doctor_name = EXCLUDED.doctor_name,
  active = EXCLUDED.active;
