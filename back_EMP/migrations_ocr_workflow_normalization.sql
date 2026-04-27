/*
Migration SQL Server - Normalisation workflow OCR
- Ajoute documents.uploaded_by_user_id
- Cree ocr_results, extracted_fields, validation_sessions, correction_history
- Conserve taxes, articles, document_upload_traces existants
*/

SET NOCOUNT ON;

/* 1) documents.uploaded_by_user_id */
IF COL_LENGTH('documents', 'uploaded_by_user_id') IS NULL
BEGIN
    ALTER TABLE documents ADD uploaded_by_user_id INT NULL;
END;

IF NOT EXISTS (
    SELECT 1
    FROM sys.foreign_keys
    WHERE name = 'FK_documents_uploaded_by_user'
)
BEGIN
    ALTER TABLE documents
        ADD CONSTRAINT FK_documents_uploaded_by_user
        FOREIGN KEY (uploaded_by_user_id) REFERENCES users(id);
END;

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_documents_uploaded_by_user_id'
      AND object_id = OBJECT_ID('documents')
)
BEGIN
    CREATE INDEX IX_documents_uploaded_by_user_id ON documents(uploaded_by_user_id);
END;

/* 2) ocr_results (1 document -> 1 resultat OCR) */
IF OBJECT_ID('ocr_results', 'U') IS NULL
BEGIN
    CREATE TABLE ocr_results (
        id INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        document_id INT NOT NULL,
        raw_result_json NVARCHAR(MAX) NULL,
        global_confidence FLOAT NULL,
        engine_name NVARCHAR(100) NULL,
        created_at DATETIME2 NOT NULL CONSTRAINT DF_ocr_results_created_at DEFAULT SYSUTCDATETIME(),
        CONSTRAINT UQ_ocr_results_document_id UNIQUE (document_id),
        CONSTRAINT FK_ocr_results_document FOREIGN KEY (document_id) REFERENCES documents(id)
    );
END;

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_ocr_results_document_id'
      AND object_id = OBJECT_ID('ocr_results')
)
BEGIN
    CREATE INDEX IX_ocr_results_document_id ON ocr_results(document_id);
END;

/* 3) extracted_fields (1 OCRResult -> N champs) */
IF OBJECT_ID('extracted_fields', 'U') IS NULL
BEGIN
    CREATE TABLE extracted_fields (
        id INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        ocr_result_id INT NOT NULL,
        field_key NVARCHAR(120) NOT NULL,
        value NVARCHAR(MAX) NULL,
        confidence FLOAT NULL,
        manually_added BIT NOT NULL CONSTRAINT DF_extracted_fields_manually_added DEFAULT 0,
        page_number INT NULL,
        bbox_json NVARCHAR(MAX) NULL,
        created_at DATETIME2 NOT NULL CONSTRAINT DF_extracted_fields_created_at DEFAULT SYSUTCDATETIME(),
        updated_at DATETIME2 NULL,
        CONSTRAINT FK_extracted_fields_ocr_result FOREIGN KEY (ocr_result_id) REFERENCES ocr_results(id)
    );
END;

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_extracted_fields_ocr_result_id'
      AND object_id = OBJECT_ID('extracted_fields')
)
BEGIN
    CREATE INDEX IX_extracted_fields_ocr_result_id ON extracted_fields(ocr_result_id);
END;

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_extracted_fields_field_key'
      AND object_id = OBJECT_ID('extracted_fields')
)
BEGIN
    CREATE INDEX IX_extracted_fields_field_key ON extracted_fields(field_key);
END;

/* 4) validation_sessions (document + validateur) */
IF OBJECT_ID('validation_sessions', 'U') IS NULL
BEGIN
    CREATE TABLE validation_sessions (
        id INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        document_id INT NOT NULL,
        validator_user_id INT NULL,
        status NVARCHAR(30) NOT NULL CONSTRAINT DF_validation_sessions_status DEFAULT 'in_progress',
        started_at DATETIME2 NOT NULL CONSTRAINT DF_validation_sessions_started_at DEFAULT SYSUTCDATETIME(),
        ended_at DATETIME2 NULL,
        comment NVARCHAR(MAX) NULL,
        CONSTRAINT FK_validation_sessions_document FOREIGN KEY (document_id) REFERENCES documents(id),
        CONSTRAINT FK_validation_sessions_validator FOREIGN KEY (validator_user_id) REFERENCES users(id)
    );
END;

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_validation_sessions_document_id'
      AND object_id = OBJECT_ID('validation_sessions')
)
BEGIN
    CREATE INDEX IX_validation_sessions_document_id ON validation_sessions(document_id);
END;

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_validation_sessions_validator_user_id'
      AND object_id = OBJECT_ID('validation_sessions')
)
BEGIN
    CREATE INDEX IX_validation_sessions_validator_user_id ON validation_sessions(validator_user_id);
END;

/* 5) correction_history (historique des corrections) */
IF OBJECT_ID('correction_history', 'U') IS NULL
BEGIN
    CREATE TABLE correction_history (
        id INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        validation_session_id INT NOT NULL,
        extracted_field_id INT NULL,
        changed_by_user_id INT NULL,
        old_value NVARCHAR(MAX) NULL,
        new_value NVARCHAR(MAX) NULL,
        action_type NVARCHAR(20) NOT NULL CONSTRAINT DF_correction_history_action_type DEFAULT 'update',
        changed_at DATETIME2 NOT NULL CONSTRAINT DF_correction_history_changed_at DEFAULT SYSUTCDATETIME(),
        CONSTRAINT FK_correction_history_validation_session FOREIGN KEY (validation_session_id) REFERENCES validation_sessions(id),
        CONSTRAINT FK_correction_history_extracted_field FOREIGN KEY (extracted_field_id) REFERENCES extracted_fields(id),
        CONSTRAINT FK_correction_history_changed_by_user FOREIGN KEY (changed_by_user_id) REFERENCES users(id)
    );
END;

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_correction_history_validation_session_id'
      AND object_id = OBJECT_ID('correction_history')
)
BEGIN
    CREATE INDEX IX_correction_history_validation_session_id ON correction_history(validation_session_id);
END;

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_correction_history_extracted_field_id'
      AND object_id = OBJECT_ID('correction_history')
)
BEGIN
    CREATE INDEX IX_correction_history_extracted_field_id ON correction_history(extracted_field_id);
END;

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_correction_history_changed_by_user_id'
      AND object_id = OBJECT_ID('correction_history')
)
BEGIN
    CREATE INDEX IX_correction_history_changed_by_user_id ON correction_history(changed_by_user_id);
END;

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_correction_history_changed_at'
      AND object_id = OBJECT_ID('correction_history')
)
BEGIN
    CREATE INDEX IX_correction_history_changed_at ON correction_history(changed_at);
END;
