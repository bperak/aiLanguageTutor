## Research: CanDo-driven lesson orchestration

Context
- Primary sources: graph (Neo4j) with CanDoDescriptor/Word/GrammarPattern/Level/Topic; compiled example `resources/canDoDescriptorExample.txt`.
- Clarified policies: graph-first precedence (feature-flag), completion-gated phases by default, hybrid storage (Postgres JSONB + graph links), hybrid illustrations, personalization via JSON Patch overlays.

Key references in repo
- resources/canDoDescriptorExample.txt: LessonPlan, Exercises, SampleDialog, StagedExercises, PragmaticPatterns, Illustration prompts.
- scripts/generate_lesson_illustrations.py, scripts/wire_lesson_media.py: image placeholder + wiring flow.

Risks & mitigations
- Sparse graph links: propose candidates; do not block activation.
- Image generation latency: pre-generate core, on-demand variants with cache.
- Personalization drift: base version pin + auto-rebase; conflict log.

Open interoperability notes
- Contracts: LessonPlan JSON, Exercises JSON, PragmaticPatterns JSON, Manifest JSON.
- Localization: UI meta in `ui_lang`; exercises target L2.


