-- Cardio Vita seed users and doctors
-- Run this after scripts/postgres_schema.sql in Supabase SQL Editor.
--
-- Seeded users have separate temporary passwords.
-- Keep the password list outside the database and ask users to change them later.
--
-- IMPORTANT:
-- These password hashes are already salted/hashed by the app.
-- After first login, create stronger personal passwords.

-- Branch staff/admin users from the provided list.
-- They are created as role = 'staff' so each user sees only their own branch.
-- If someone must manage the whole system, change role to 'admin' and branch to NULL.
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

-- Doctors table from the provided doctors list.
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
  ('azniv.gevorgyan', 'Td0gSh3+Yrv9g3n0qjImjJtYePiDph/XXKkIHckx2hWLdOcgmE0ti1wsJ2jlm6pw', 'doctor', NULL, 'Ազնիվ Գևորգյան', 1, NOW()::text),
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
