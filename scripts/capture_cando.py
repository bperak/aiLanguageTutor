import os
import sys
import json
import time
import pathlib
import httpx


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/capture_cando.py <CAN_DO_ID>")
        return 2

    can_do_id = sys.argv[1]
    base = os.environ.get("TARGET_BACKEND", "http://localhost:8000")
    api = base.rstrip("/") + "/api/v1"
    out_dir = pathlib.Path("backend/tests/artifacts")
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = str(int(time.time()))

    timeout_s = float(os.environ.get("CAPTURE_TIMEOUT_SEC", "480"))

    print(f"Capturing for {can_do_id} -> {out_dir}")
    with httpx.Client(timeout=timeout_s) as client:
        # Start lesson
        try:
            r = client.post(
                f"{api}/cando/lessons/start",
                params={
                    "can_do_id": can_do_id,
                    "phase": "lexicon_and_patterns",
                    "level": 3,
                    # pass extended timeout where supported
                    "timeout": int(min(timeout_s, 300)),
                },
            )
            start_path = out_dir / f"{can_do_id}.{ts}.start.json"
            start_path.write_text(json.dumps(r.json(), ensure_ascii=False, indent=2), encoding="utf-8")
            print("start ->", start_path)
        except Exception as e:
            print("start_failed:", e)

        # Compile dry_run
        try:
            r2 = client.post(
                f"{api}/cando/lessons/compile",
                params={
                    "can_do_id": can_do_id,
                    "version": 1,
                    "provider": "openai",
                    "fast": False,
                    "dry_run": True,
                },
            )
            compile_path = out_dir / f"{can_do_id}.{ts}.compile.dry_run.json"
            compile_path.write_text(json.dumps(r2.json(), ensure_ascii=False, indent=2), encoding="utf-8")
            print("compile ->", compile_path)
        except Exception as e:
            print("compile_failed:", e)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


