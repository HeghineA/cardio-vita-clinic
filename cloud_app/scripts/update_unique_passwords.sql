-- Update Cardio Vita users to separate temporary passwords.
-- This file stores hashes only. Keep the plain password list separately.

UPDATE users SET password_hash = '6hilODVD6daxzPc1VqJNYxOuEoKxrfbDvW/aCyn2nhyzlCcGcWCCvjtJXxY/8dJq' WHERE username = 'admin';
UPDATE users SET password_hash = 'gR7orS5WCfLXkdrYo6qklbslUHudrAZO4Fp9b+WVyIZp0v7XZ/A6dkHAtU0Fp5vb' WHERE username = 'mane.barseghyan';
UPDATE users SET password_hash = 'Mp4XlqWTBTh5NW378ptkz81bnq7Z/g3X3vBWIJeiTn4FnJ77Q1hglyGGpbomfWL3' WHERE username = 'milena.ashabeyan';
UPDATE users SET password_hash = 's57a2Rz2CVkqvHAOqmHAyqNzkr8ht91k5pkYjeL8pQxZoCH2YhH6TbZwkEHGBFJb' WHERE username = 'lusine.teryan';
UPDATE users SET password_hash = 'KYucFN/b8NBR99Nx0tp9vEcGcASe4ow20UJxXdlvY8PGB1fVbEHWw/mdfrm5pLNR' WHERE username = 'siranush.teryan';
UPDATE users SET password_hash = 'NtuFUhygVMJ2aijyORHDP1CG7yB5tFzlpyXkuO5+TqrWXQLe6EMghb7FsKmj0kW6' WHERE username = 'gohar.teryan';
UPDATE users SET password_hash = 'Td0gSh3+Yrv9g3n0qjImjJtYePiDph/XXKkIHckx2hWLdOcgmE0ti1wsJ2jlm6pw' WHERE username = 'azniv.gevorgyan';
UPDATE users SET password_hash = 'a7V6h5s2Tq52cTEvE9fUNwiR9Jywi/XZ1uo64+aGdStqAv/ypx5AuzWQ+0Q6jk3E' WHERE username = 'alla.abovyan';
UPDATE users SET password_hash = 'iTKu/MeHoP8TF5hiNF9ZnelZZ5xXmRNxzFssk+q2ishjzXTeUrYUCnn5KXGOf/ct' WHERE username = 'siranush.grigoryan';
UPDATE users SET password_hash = 'ZQ3H7Es2zpkJaU8dFNLxfaCak3lylmXl721jlODe1oLoxnDTisZL8dbQu3R6zTra' WHERE username = 'sofya.khachatryan';
UPDATE users SET password_hash = 'TOiyWQMhzmU929bQoa24WQOXLh2ccH8JxIiYO2rKpAXo/w3eIBWaZVyfCG6RDFd2' WHERE username = 'melina.khachatryan';
UPDATE users SET password_hash = 'tA31hBYpmwRdJKRfmJByV2l51Fpa5NrpsL5gyBuWHh7m5KSOJjZEt39K5/EsT8tO' WHERE username = 'lyuba.arzumanyan';
UPDATE users SET password_hash = 'SMHHOtSc0QvV0sbOxpGmpURRW1JPbKKwGXgu7xUrUR1W+yfh5UvAUywoZ0z6Ys1m' WHERE username = 'bakur.vardanyan';
UPDATE users SET password_hash = 'V1WFtotY94CA+vp4R8qBy9vUNt2z/D/0cTHY4IXw1dU9jFFd4AlJLdWC/wo5Djfk' WHERE username = 'armen.shahbazyan';
UPDATE users SET password_hash = 'ROBVRrN1tn+c0OrYNWvCErXrmnppruzenZCqzOEW0+CaGpij53xdJ7UuM97v6P9U' WHERE username = 'gayane.makaryan';
UPDATE users SET password_hash = 'P6UQVB3j9LoUFqTG7Ob3vngHIzxPxBPbVNAapAcxAhRnSkaPl5ybjrE4yC3p6o93' WHERE username = 'anna.aslikyan';

DELETE FROM sessions;
