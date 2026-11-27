ALTER TABLE rag.documents
    ADD COLUMN IF NOT EXISTS origin text NOT NULL DEFAULT 'corpus',
    ADD COLUMN IF NOT EXISTS publication text NOT NULL DEFAULT 'published',
    ADD COLUMN IF NOT EXISTS index_stage text,
    ADD COLUMN IF NOT EXISTS queued_from_ui boolean NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS chunks_total integer,
    ADD COLUMN IF NOT EXISTS chunks_done integer,
    ADD COLUMN IF NOT EXISTS replaces_id bigint REFERENCES rag.documents(id),
    ADD COLUMN IF NOT EXISTS published_at timestamptz,
    ADD COLUMN IF NOT EXISTS effective_on date;
