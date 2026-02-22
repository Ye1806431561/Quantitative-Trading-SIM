#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

if ! command -v varlock >/dev/null 2>&1; then
  echo "❌ 未安装 varlock，请先安装后再提交。"
  exit 1
fi

if ! varlock load >/dev/null 2>&1; then
  echo "❌ varlock 环境校验失败，请先修复 .env / 环境变量。"
  exit 1
fi

staged_files="$(git diff --cached --name-only --diff-filter=ACMR)"
if [[ -z "$staged_files" ]]; then
  exit 0
fi

blocked=0
for file in $staged_files; do
  if [[ "$file" == ".env.schema" ]]; then
    continue
  fi
  case "$file" in
    .env|.env.*|data/secure/*|data/database/*.db|data/database/*.sqlite|data/database/*.sqlite3)
      echo "❌ 禁止提交敏感或运行态文件: $file"
      blocked=1
      ;;
  esac
done

if [[ "$blocked" -eq 1 ]]; then
  exit 1
fi

python3 - <<'PY'
import re
import subprocess
import sys

diff = subprocess.check_output(
    ["git", "diff", "--cached", "--unified=0", "--no-color"],
    text=True,
    errors="ignore",
)

allow_literals = {
    "",
    "your_api_key_here",
    "your_api_secret_here",
    "replace_with_a_long_random_secret",
    "your_value_here",
}

patterns = {
    "aws_access_key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "github_token": re.compile(r"ghp_[A-Za-z0-9]{36}"),
    "slack_token": re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    "private_key": re.compile(r"BEGIN [A-Z ]*PRIVATE KEY"),
}

env_assignment = re.compile(
    r"^\+\s*(EXCHANGE_API_KEY|EXCHANGE_API_SECRET|CONFIG_MASTER_KEY)\s*=\s*(.*)\s*$"
)

findings: list[str] = []
for line in diff.splitlines():
    if not line.startswith("+") or line.startswith("+++"):
        continue
    payload = line[1:]

    for label, pattern in patterns.items():
        if pattern.search(payload):
            findings.append(f"{label}: {payload[:160]}")

    m = env_assignment.match(line)
    if m:
        value = m.group(2).strip().strip("'").strip('"')
        if value not in allow_literals and not value.startswith("${"):
            findings.append(f"env_secret_assignment: {payload[:160]}")

if findings:
    print("❌ 检测到疑似敏感信息，请先清理后再提交：")
    for item in findings:
        print(f"  - {item}")
    sys.exit(1)

print("✅ 提交前密钥检查通过")
PY
