-- Cardio Vita Clinic Supabase full setup
-- Run this whole file in Supabase SQL Editor.
--
-- It creates tables, indexes, doctors, and login users.
-- It is safe to run more than once.
--
-- Seeded users have separate temporary passwords.
-- Keep the password list outside the database and ask users to change them later.
--
-- IMPORTANT:
-- Change passwords before using real patient data.

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

-- Main full-system admin.
INSERT INTO users (username, password_hash, role, branch, doctor_name, active, created_at) VALUES
  ('admin', '6hilODVD6daxzPc1VqJNYxOuEoKxrfbDvW/aCyn2nhyzlCcGcWCCvjtJXxY/8dJq', 'admin', NULL, NULL, 1, NOW()::text)
ON CONFLICT (username) DO UPDATE SET
  password_hash = EXCLUDED.password_hash,
  role = EXCLUDED.role,
  branch = EXCLUDED.branch,
  doctor_name = EXCLUDED.doctor_name,
  active = EXCLUDED.active;

-- Branch staff users.
INSERT INTO users (username, password_hash, role, branch, doctor_name, active, created_at) VALUES
  ('mane.barseghyan', 'gR7orS5WCfLXkdrYo6qklbslUHudrAZO4Fp9b+WVyIZp0v7XZ/A6dkHAtU0Fp5vb', 'staff', 'Նարեկացի', NULL, 1, NOW()::text),
  ('milena.ashabeyan', 'Mp4XlqWTBTh5NW378ptkz81bnq7Z/g3X3vBWIJeiTn4FnJ77Q1hglyGGpbomfWL3', 'staff', 'Նարեկացի', NULL, 1, NOW()::text),
  ('lusine.teryan', 's57a2Rz2CVkqvHAOqmHAyqNzkr8ht91k5pkYjeL8pQxZoCH2YhH6TbZwkEHGBFJb', 'staff', 'Տերյան', NULL, 1, NOW()::text),
  ('siranush.teryan', 'KYucFN/b8NBR99Nx0tp9vEcGcASe4ow20UJxXdlvY8PGB1fVbEHWw/mdfrm5pLNR', 'staff', 'Տերյան', NULL, 1, NOW()::text),
  ('gohar.teryan', 'NtuFUhygVMJ2aijyORHDP1CG7yB5tFzlpyXkuO5+TqrWXQLe6EMghb7FsKmj0kW6', 'staff', 'Տերյան', NULL, 1, NOW()::text)
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
  ('azniv.gevorgyan', 'Td0gSh3+Yrv9g3n0qjImjJtYePiDph/XXKkIHckx2hWLdOcgmE0ti1wsJ2jlm6pw', 'manager', NULL, 'Ազնիվ Գևորգյան', 1, NOW()::text),
  ('alla.abovyan', 'a7V6h5s2Tq52cTEvE9fUNwiR9Jywi/XZ1uo64+aGdStqAv/ypx5AuzWQ+0Q6jk3E', 'doctor', NULL, 'Ալլա Աբովյան', 1, NOW()::text),
  ('siranush.grigoryan', 'iTKu/MeHoP8TF5hiNF9ZnelZZ5xXmRNxzFssk+q2ishjzXTeUrYUCnn5KXGOf/ct', 'doctor', NULL, 'Սիրանուշ Գրիգորյան', 1, NOW()::text),
  ('sofya.khachatryan', 'ZQ3H7Es2zpkJaU8dFNLxfaCak3lylmXl721jlODe1oLoxnDTisZL8dbQu3R6zTra', 'doctor', NULL, 'Սոֆյա Խաչատրյան', 1, NOW()::text),
  ('melina.khachatryan', 'TOiyWQMhzmU929bQoa24WQOXLh2ccH8JxIiYO2rKpAXo/w3eIBWaZVyfCG6RDFd2', 'doctor', NULL, 'Մելինա Խաչատրյան', 1, NOW()::text),
  ('lyuba.arzumanyan', 'tA31hBYpmwRdJKRfmJByV2l51Fpa5NrpsL5gyBuWHh7m5KSOJjZEt39K5/EsT8tO', 'doctor', NULL, 'Լյուբա Արզումանյան', 1, NOW()::text),
  ('bakur.vardanyan', 'SMHHOtSc0QvV0sbOxpGmpURRW1JPbKKwGXgu7xUrUR1W+yfh5UvAUywoZ0z6Ys1m', 'doctor', NULL, 'Բակուր Վարդանյան', 1, NOW()::text),
  ('armen.shahbazyan', 'V1WFtotY94CA+vp4R8qBy9vUNt2z/D/0cTHY4IXw1dU9jFFd4AlJLdWC/wo5Djfk', 'doctor', NULL, 'Արմեն Շահբազյան', 1, NOW()::text),
  ('gayane.makaryan', 'ROBVRrN1tn+c0OrYNWvCErXrmnppruzenZCqzOEW0+CaGpij53xdJ7UuM97v6P9U', 'doctor', NULL, 'Մակարյան Գայանե', 1, NOW()::text),
  ('anna.aslikyan', 'P6UQVB3j9LoUFqTG7Ob3vngHIzxPxBPbVNAapAcxAhRnSkaPl5ybjrE4yC3p6o93', 'doctor', NULL, 'Ասլիկյան Աննա', 1, NOW()::text)
ON CONFLICT (username) DO UPDATE SET
  password_hash = EXCLUDED.password_hash,
  role = EXCLUDED.role,
  branch = EXCLUDED.branch,
  doctor_name = EXCLUDED.doctor_name,
  active = EXCLUDED.active;
