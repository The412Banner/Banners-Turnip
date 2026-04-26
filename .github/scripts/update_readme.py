import re, json, os, subprocess
from datetime import datetime, timezone, timedelta

tag          = os.environ["BT_TAG"]
mesa_ver     = os.environ["BT_MESA_VERSION"]
build_date   = os.environ["BT_BUILD_DATE"]
githash      = os.environ["BT_GITHASH"]
githash_f    = os.environ["BT_GITHASH_FULL"]
c_date       = os.environ["BT_COMMIT_DATE"]
c_title      = os.environ["BT_COMMIT_TITLE"]
vulkan_ver   = os.environ["BT_VULKAN_VERSION"]
repo         = os.environ["BT_REPO"]

release_url = f"https://github.com/{repo}/releases/tag/{tag}"
mesa_url    = f"https://gitlab.freedesktop.org/mesa/mesa/-/commit/{githash_f}"

latest = (
    "| | |\n"
    "| :--- | :--- |\n"
    f"| **Mesa version** | {mesa_ver} |\n"
    f"| **Vulkan version** | {vulkan_ver} |\n"
    f"| **Commit** | [`{githash}`]({mesa_url}) |\n"
    f"| **Commit date** | {c_date} |\n"
    f"| **Commit title** | {c_title} |\n"
    f"| **Build date** | {build_date} |\n"
    f"| **Release** | [{tag}]({release_url}) |"
)

result = subprocess.run(
    ["gh", "release", "list", "--repo", repo, "--limit", "50",
     "--json", "tagName,name,publishedAt"],
    capture_output=True, text=True
)
releases = json.loads(result.stdout)
since = datetime.now(timezone.utc) - timedelta(hours=24)
recent_releases = [
    r for r in releases
    if datetime.fromisoformat(r["publishedAt"].replace("Z", "+00:00")) >= since
]

rows = []
for r in recent_releases:
    t = r["tagName"]
    pub_date = r["publishedAt"][:10]
    rel_url = f"https://github.com/{repo}/releases/tag/{t}"

    body_result = subprocess.run(
        ["gh", "release", "view", t, "--repo", repo, "--json", "body"],
        capture_output=True, text=True
    )
    body = json.loads(body_result.stdout).get("body", "")

    commit_cell  = ""
    title_cell   = ""
    vulkan_cell  = ""

    m = re.search(r"\*\*Commit\*\*\s*\|\s*(\[`[^`]+`\]\([^)]+\))", body)
    if m:
        commit_cell = m.group(1)

    m = re.search(r"\*\*Commit title\*\*\s*\|\s*(.+)", body)
    if m:
        title_cell = m.group(1).strip()

    m = re.search(r"\*\*Vulkan version\*\*\s*\|\s*(.+)", body)
    if m:
        vulkan_cell = m.group(1).strip()

    rows.append(f"| [{t}]({rel_url}) | {pub_date} | {commit_cell} | {title_cell} | {vulkan_cell} |")

if rows:
    header = (
        "| Tag | Date | Commit | Description | Vulkan |\n"
        "| :--- | :--- | :--- | :--- | :--- |"
    )
    recent = header + "\n" + "\n".join(rows)
else:
    recent = "_No builds in the last 24 hours._"

with open("README.md") as f:
    content = f.read()

content = re.sub(
    r"<!-- LATEST_BUILD_START -->.*?<!-- LATEST_BUILD_END -->",
    f"<!-- LATEST_BUILD_START -->\n{latest}\n<!-- LATEST_BUILD_END -->",
    content, flags=re.DOTALL
)
content = re.sub(
    r"<!-- RECENT_BUILDS_START -->.*?<!-- RECENT_BUILDS_END -->",
    f"<!-- RECENT_BUILDS_START -->\n{recent}\n<!-- RECENT_BUILDS_END -->",
    content, flags=re.DOTALL
)

with open("README.md", "w") as f:
    f.write(content)
print("README updated")
