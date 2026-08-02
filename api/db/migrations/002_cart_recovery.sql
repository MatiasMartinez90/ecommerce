-- migrate:up

ALTER TABLE shopping_carts
    ADD COLUMN IF NOT EXISTS abandoned_at timestamptz,
    ADD COLUMN IF NOT EXISTS recovery_attempts int NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS last_recovery_at timestamptz;

CREATE INDEX IF NOT EXISTS shopping_carts_abandoned_idx
    ON shopping_carts (status, abandoned_at)
    WHERE status = 'abandoned';

-- migrate:down

DROP INDEX IF EXISTS shopping_carts_abandoned_idx;
ALTER TABLE shopping_carts
    DROP COLUMN IF EXISTS last_recovery_at,
    DROP COLUMN IF EXISTS recovery_attempts,
    DROP COLUMN IF EXISTS abandoned_at;
