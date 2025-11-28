-- Lessons core schema (PostgreSQL)

CREATE TABLE IF NOT EXISTS lessons (
    id BIGSERIAL PRIMARY KEY,
    can_do_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_lessons_can_do_id ON lessons (can_do_id);

CREATE TABLE IF NOT EXISTS lesson_versions (
    id BIGSERIAL PRIMARY KEY,
    lesson_id BIGINT NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    lesson_plan JSONB NOT NULL,
    exercises JSONB,
    manifest JSONB,
    dialogs JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (lesson_id, version)
);

CREATE INDEX IF NOT EXISTS idx_lesson_versions_lesson_id ON lesson_versions (lesson_id);
CREATE INDEX IF NOT EXISTS idx_lesson_versions_version ON lesson_versions (version);

CREATE TABLE IF NOT EXISTS user_lesson_overlays (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    lesson_id BIGINT NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
    base_version INTEGER NOT NULL,
    overlay_patch JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_overlays_user_lesson ON user_lesson_overlays (user_id, lesson_id);
CREATE INDEX IF NOT EXISTS idx_user_overlays_base_version ON user_lesson_overlays (base_version);


