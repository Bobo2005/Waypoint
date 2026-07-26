from pathlib import Path
from backend.agent.tools import read_file, write_file, run_bash, git_commit, ToolError

root = Path(".").resolve()

# read_file
content = read_file(root, "demo-repo/weather_client.py")
assert "httpx" in content and "import requests" not in content
print("read_file: OK (weather_client.py already migrated, as expected)")

# write_file (round-trip on a throwaway file, not a real source file)
write_file(root, "demo-repo/_tmp_test.py", "# scratch\n")
assert (root / "demo-repo/_tmp_test.py").read_text() == "# scratch\n"
print("write_file: OK")

# run_bash (only ever runs pytest)
result = run_bash(root, "demo-repo/tests/test_weather_client.py")
assert result["passed"] is True
print("run_bash: OK ->", result["exit_code"])

# path escape is rejected
try:
    read_file(root, "../outside.py")
    print("read_file escape check: FAILED (should have raised)")
except ToolError:
    print("read_file escape check: OK (correctly rejected)")

(root / "demo-repo/_tmp_test.py").unlink()  # cleanup
print("ALL TOOL CHECKS PASSED")