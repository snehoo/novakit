-- Per-IP request counters for the public form endpoints (track, subscribe,
-- feedback, free-skill). Keyed on a hash of the IP, never the raw address.
-- One row per key per minute; rows older than a day are pruned on write.
CREATE TABLE IF NOT EXISTS rate_limits (
  key     text        NOT NULL,
  bucket  timestamptz NOT NULL,
  n       integer     NOT NULL DEFAULT 1,
  PRIMARY KEY (key, bucket)
);
CREATE INDEX IF NOT EXISTS rate_limits_bucket_idx ON rate_limits (bucket);
