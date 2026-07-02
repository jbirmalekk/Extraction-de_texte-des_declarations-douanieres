-- Initialisation base ERP_DB (serveur S2 — back_EMP_ERP)
-- Alternative au script Python : python scripts/init_db.py

IF NOT EXISTS (
    SELECT 1 FROM sys.tables WHERE name = 'X_Declaration_Facture' AND schema_id = SCHEMA_ID('dbo')
)
BEGIN
    CREATE TABLE dbo.X_Declaration_Facture (
        id INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        s1_export_id INT NOT NULL,
        kind NVARCHAR(20) NOT NULL,
        reference NVARCHAR(120) NULL,
        status NVARCHAR(32) NOT NULL CONSTRAINT DF_X_Declaration_Facture_status DEFAULT ('pending'),
        migration_message NVARCHAR(MAX) NULL,
        erp_reference NVARCHAR(120) NULL,
        payload_json NVARCHAR(MAX) NULL,
        created_at DATETIME2 NOT NULL CONSTRAINT DF_X_Declaration_Facture_created_at DEFAULT (SYSUTCDATETIME()),
        migrated_at DATETIME2 NULL
    );

    CREATE INDEX IX_X_Declaration_Facture_s1_export_id ON dbo.X_Declaration_Facture (s1_export_id);
END
GO
