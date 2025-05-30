import requests
import os
import re
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO = os.getenv("GITHUB_REPO")  # замените на свой репозиторий
LABEL = "requirement"
BRANCH = "main"

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}


def fetch_issues():
    url = f"https://api.github.com/repos/{REPO}/issues"
    params = {"state": "all", "labels": LABEL, "per_page": 100}
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    return response.json()


def fetch_repo_tree():
    url = f"https://api.github.com/repos/{REPO}/git/trees/{BRANCH}?recursive=1"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    tree = response.json()["tree"]
    return [item["path"] for item in tree if item["path"].endswith(".py")]


def fetch_file_content(path):
    url = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{path}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.text
    else:
        print(f"⚠️ Не удалось загрузить {path}")
        return ""


def find_implementations(issue_titles):
    implemented = {title: [] for title in issue_titles}
    code_files = fetch_repo_tree()

    for path in code_files:
        content = fetch_file_content(path)
        for lineno, line in enumerate(content.splitlines(), start=1):
            match = re.search(r'#\s*Implements:\s*(.+)', line)
            if match:
                title = match.group(1).strip()
                if title in implemented:
                    implemented[title].append(f"{path}:{lineno}")
    return implemented


def generate_documentation():
    issues = fetch_issues()
    issue_titles = [issue['title'] for issue in issues]
    implemented_map = find_implementations(issue_titles)

    os.makedirs("docs", exist_ok=True)

    with open("docs/requirements.md", "w", encoding="utf-8") as f:
        f.write("# Требования\n\n")
        for issue in issues:
            title = issue['title']
            f.write(f"## {title}\n")
            f.write(f"{issue['body']}\n\n")
            f.write(f"*Автор: @{issue['user']['login']} | Статус: {issue['state']}*\n\n")

            implemented = implemented_map.get(title, [])
            if implemented:
                f.write("**Реализовано в коде:**\n")
                for ref in implemented:
                    path, line = ref.split(":")
                    url = f"https://github.com/{REPO}/blob/{BRANCH}/{path}#L{line}"
                    f.write(f"- [`{ref}`]({url})\n")
                f.write("\n")
            else:
                f.write("_Пока не реализовано в коде._\n\n")

    print("✅ Документация обновлена в docs/requirements.md")


if __name__ == "__main__":
    generate_documentation()
