-- Cardio Vita seed users and doctors
-- Run this after scripts/postgres_schema.sql in Supabase SQL Editor.
--
-- Temporary password for every user below:
--   ChangeMe2026!
--
-- IMPORTANT:
-- These password hashes are already salted/hashed by the app.
-- After first login, create stronger personal passwords.

-- Branch staff/admin users from the provided list.
-- They are created as role = 'staff' so each user sees only their own branch.
-- If someone must manage the whole system, change role to 'admin' and branch to NULL.
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

-- Doctors table from the provided doctors list.
INSERT INTO doctors (name, specialty, active) VALUES
  ('Ազնիվ Գևորգյան', 'Սրտաբան', 1),
  ('Ալլա Աբովյան', 'Սրտաբան', 1),
  ('Սիրանուշ Գրիգորյան', 'Սրտաբան', 1),
  ('Սոֆյա Խաչատրյան', 'Սոնոգրաֆիստ', 1),
  ('Մելինա Խաչատրյան', 'Նյարդաբան', 1),
  ('Լյուբա Արզումանյան', 'Ճառագայթային ախտորոշման մասնագետ', 1),
  ('Բակուր Վարդանյան', 'Սրտաբան', 1),
  ('Արմեն Շահբազյան', 'Սրտաբան', 1)
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
  ('armen.shahbazyan', 'qKKj3j7lDRlFxT1m3KOUG1rv5flkm45ryYaYR3d0EPfA6qsjnzaCbi5v9SXXZuG/', 'doctor', NULL, 'Արմեն Շահբազյան', 1, NOW()::text)
ON CONFLICT (username) DO UPDATE SET
  password_hash = EXCLUDED.password_hash,
  role = EXCLUDED.role,
  branch = EXCLUDED.branch,
  doctor_name = EXCLUDED.doctor_name,
  active = EXCLUDED.active;

