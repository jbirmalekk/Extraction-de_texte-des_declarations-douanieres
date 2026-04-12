-- Migration SQL Server pour ajouter is_email_verified et is_approved

-- ⚠️ IMPORTANT: Exécutez ce script sur votre base de données SQL Server
-- Cela ajoutera les deux nouvelles colonnes au tableau users

ALTER TABLE users
ADD is_email_verified BIT DEFAULT 0 NOT NULL,
    is_approved BIT DEFAULT 0 NOT NULL;

-- Pour les utilisateurs existants, les marquer comme approuvés et vérifiés
-- Si vous ne voulez que certains utilisateurs soient approuvés, modifiez cette requête
-- UPDATE users SET is_email_verified = 1, is_approved = 1;

-- Vérifier que les colonnes ont été ajoutées
SELECT * FROM users;

-- Si vous avez besoin de annuler:
-- ALTER TABLE users DROP COLUMN is_email_verified, is_approved;
