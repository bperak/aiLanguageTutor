## Data Model

Graph (Neo4j)
- (:CanDoDescriptor {uid, level, topic, domain, type})
- (:Lesson {lesson_id, version, status})
- (:PragmaticPattern {id, pragmaticAct, register, socialDistance, locale, tags})
- Relationships:
  - (:Lesson)-[:COVERS]->(:CanDoDescriptor)
  - (:Lesson)-[:USES_PRAGMA]->(:PragmaticPattern)
  - (:CanDoDescriptor)-[:PREREQ]->(:CanDoDescriptor)
  - SAME_* edges already generated (level/topic/skillDomain/type)

Postgres (JSONB)
- lessons(id PK, can_do_id, version, status, created_at)
- lesson_versions(id PK, lesson_id FK, version, lesson_plan JSONB, exercises JSONB, manifest JSONB, dialogs JSONB)
- user_lesson_overlays(id PK, user_id, lesson_id, base_version, overlay_patch JSONB, created_at)

Filesystem/Object Storage
- images/lessons/cando/{can_do_id}/: *.png + manifest.json

Identity & Constraints
- CanDoDescriptor.uid is unique (enforced in Neo4j).
- lessons(can_do_id, version) unique.
- user_lesson_overlays base_version pin required; JSON Patch RFC 6902 format.


