/* ============================================================
   Migration Auth Security (SQL Server)
   - users.token_version
   - revoked_tokens.token_type
   - revoked_tokens.username
   - Index utiles
   ============================================================ */

SET NOCOUNT ON;
BEGIN TRY
    BEGIN TRANSACTION;

    /* ------------------------------------------------------------
       1) users.token_version
       ------------------------------------------------------------ */
    IF OBJECT_ID(N'dbo.users', N'U') IS NULL
    BEGIN
        RAISERROR('Table dbo.users introuvable.', 16, 1);
    END

    IF COL_LENGTH('dbo.users', 'token_version') IS NULL
    BEGIN
        ALTER TABLE dbo.users
        ADD token_version INT NOT NULL
            CONSTRAINT DF_users_token_version DEFAULT (0);
    END

    -- Sécurise les anciennes lignes si colonne déjà là et nullable
    IF COL_LENGTH('dbo.users', 'token_version') IS NOT NULL
    BEGIN
        EXEC sp_executesql N'
            UPDATE dbo.users
            SET token_version = 0
            WHERE token_version IS NULL;
        ';
    END

    /* ------------------------------------------------------------
       2) revoked_tokens: créer table si absente
       ------------------------------------------------------------ */
    IF OBJECT_ID(N'dbo.revoked_tokens', N'U') IS NULL
    BEGIN
        CREATE TABLE dbo.revoked_tokens
        (
            id INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
            jti VARCHAR(64) NOT NULL,
            token_type VARCHAR(20) NOT NULL
                CONSTRAINT DF_revoked_tokens_token_type DEFAULT ('access'),
            username VARCHAR(150) NULL,
            expires_at DATETIMEOFFSET NOT NULL,
            revoked_at DATETIMEOFFSET NOT NULL
                CONSTRAINT DF_revoked_tokens_revoked_at DEFAULT (SYSDATETIMEOFFSET())
        );
    END

    /* ------------------------------------------------------------
       3) revoked_tokens: ajouter colonnes manquantes
       ------------------------------------------------------------ */
    IF COL_LENGTH('dbo.revoked_tokens', 'token_type') IS NULL
    BEGIN
        ALTER TABLE dbo.revoked_tokens
        ADD token_type VARCHAR(20) NOT NULL
            CONSTRAINT DF_revoked_tokens_token_type DEFAULT ('access');
    END

    IF COL_LENGTH('dbo.revoked_tokens', 'username') IS NULL
    BEGIN
        ALTER TABLE dbo.revoked_tokens
        ADD username VARCHAR(150) NULL;
    END

    /* ------------------------------------------------------------
       4) Index / contraintes utiles
       ------------------------------------------------------------ */
    IF NOT EXISTS (
        SELECT 1
        FROM sys.indexes
        WHERE name = 'UX_revoked_tokens_jti'
          AND object_id = OBJECT_ID('dbo.revoked_tokens')
    )
    BEGIN
        CREATE UNIQUE INDEX UX_revoked_tokens_jti
            ON dbo.revoked_tokens (jti);
    END

    IF NOT EXISTS (
        SELECT 1
        FROM sys.indexes
        WHERE name = 'IX_revoked_tokens_expires_at'
          AND object_id = OBJECT_ID('dbo.revoked_tokens')
    )
    BEGIN
        CREATE INDEX IX_revoked_tokens_expires_at
            ON dbo.revoked_tokens (expires_at);
    END

    IF NOT EXISTS (
        SELECT 1
        FROM sys.indexes
        WHERE name = 'IX_revoked_tokens_username'
          AND object_id = OBJECT_ID('dbo.revoked_tokens')
    )
    BEGIN
        CREATE INDEX IX_revoked_tokens_username
            ON dbo.revoked_tokens (username);
    END

    COMMIT TRANSACTION;
    PRINT 'Migration auth security appliquée avec succès.';
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;

    DECLARE @ErrMsg NVARCHAR(4000) = ERROR_MESSAGE();
    DECLARE @ErrSev INT = ERROR_SEVERITY();
    DECLARE @ErrState INT = ERROR_STATE();

    RAISERROR('Migration échouée: %s', @ErrSev, @ErrState, @ErrMsg);
END CATCH;
GO
