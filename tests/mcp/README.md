Playwright MCP E2E Scenarios

Prereqs
- Backend running on http://localhost:8000
- Frontend (optional) on http://localhost:3000
- CanDo example imported; images/manifest generated for JFまるごと:13 (see quickstart).

Running
- Use a Playwright MCP runner that can consume scenario JSON files and invoke MCP browser ops.
- Suggested order:
  1) scenarios/activate_cando.json
  2) scenarios/generate_exercises.json
  3) scenarios/wire_media.json
  4) scenarios/perf_smoke.json

Notes
- Scenarios use backend endpoints directly via evaluate(fetch(...)).
- Adjust host/ports if different in your environment.


