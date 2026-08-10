-- Add manager role support and make Azniv Gevorgyan a manager.

ALTER TABLE users DROP CONSTRAINT IF EXISTS users_role_check;
ALTER TABLE users ADD CONSTRAINT users_role_check CHECK (role IN ('admin', 'manager', 'staff', 'doctor'));

UPDATE users
SET role = 'manager',
    branch = NULL,
    doctor_name = 'Ազնիվ Գևորգյան'
WHERE username = 'azniv.gevorgyan';
