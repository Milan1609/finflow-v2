ALTER TABLE "user"
ADD COLUMN IF NOT EXISTS google_subject VARCHAR(255);

CREATE UNIQUE INDEX IF NOT EXISTS uq_user_google_subject
ON "user"(google_subject)
WHERE google_subject IS NOT NULL;
