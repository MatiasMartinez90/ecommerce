-- migrate:up

ALTER TABLE products ADD COLUMN IF NOT EXISTS video_url text;

-- migrate:down

ALTER TABLE products DROP COLUMN IF EXISTS video_url;
