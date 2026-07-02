-- Renommer l'ancienne table erp_migration_logs vers X_Declaration_Facture
-- A executer une seule fois si la base contient deja erp_migration_logs

USE ERP_DB;
GO

IF EXISTS (SELECT 1 FROM sys.tables WHERE name = 'erp_migration_logs' AND schema_id = SCHEMA_ID('dbo'))
   AND NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'X_Declaration_Facture' AND schema_id = SCHEMA_ID('dbo'))
BEGIN
    EXEC sp_rename 'dbo.erp_migration_logs', 'X_Declaration_Facture';
END
GO
