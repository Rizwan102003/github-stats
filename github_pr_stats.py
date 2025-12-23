import argparse
import requests
import time
import random
from datetime import datetime
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.console import Console
from rich.progress import track

console = Console()

GITHUB_API = "https://api.github.com"

# ----------------------------
# Safe fetch with retry & sleep
# ----------------------------
def fetch(url, retries=3):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "github-pr-stats-script"
    }

    for attempt in range(retries):
        try:
            r = requests.get(url, headers=headers, timeout=15)

            if r.status_code == 200:
                # polite delay with jitter
                time.sleep(0.4 + random.uniform(0, 0.3))
                return r.json()

            if r.status_code in (403, 429):
                wait = 2 ** attempt
                console.print(f"[yellow]Rate limited. Sleeping {wait}s...[/yellow]")
                time.sleep(wait)
                continue

            if r.status_code >= 500:
                time.sleep(1)
                continue

            console.print(f"[red]Error fetching {url}: {r.status_code}[/red]")
            return None

        except requests.RequestException:
            time.sleep(1)

    return None


# ----------------------------
# Search PRs
# ----------------------------
def search_prs(username, start, end, label=None):
    prs = []
    page = 1

    query = f"author:{username}+type:pr+created:{start}..{end}"
    if label:
        query += f"+label:{label}"

    console.print(f"[bold blue]Fetching PRs for {username}...[/bold blue]")

    while True:
        url = f"{GITHUB_API}/search/issues?q={query}&per_page=100&page={page}"
        data = fetch(url)

        if not data or "items" not in data:
            break

        items = data["items"]
        prs.extend(items)

        if len(items) < 100:
            break

        page += 1

    return prs


# ----------------------------
# Fetch PR details
# ----------------------------
def fetch_pr_details(pr):
    pr_url = pr.get("pull_request", {}).get("url")
    if not pr_url:
        return None

    details = fetch(pr_url)
    if not details:
        return None

    return {
        "repo_name": details["base"]["repo"]["full_name"],
        "repo_link": details["base"]["repo"]["html_url"],
        "title": details["title"],
        "created_at": details["created_at"],
        "merged_at": details["merged_at"],
        "pr_link": details["html_url"],
    }


# ----------------------------
# Main
# ----------------------------
def main():
    parser = argparse.ArgumentParser(description="Fetch GitHub PR stats for any public user (No PAT required).")
    parser.add_argument("--user", required=True, help="GitHub username")
    parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--label", help="Optional PR label filter")
    args = parser.parse_args()

    start = f"{args.start}T00:00:00Z"
    end = f"{args.end}T23:59:59Z"

    prs = search_prs(args.user, start, end, args.label)
    if not prs:
        console.print("[yellow]No PRs found.[/yellow]")
        return

    console.print(f"[cyan]Fetching detailed PR info ({len(prs)} PRs)...[/cyan]")

    detailed_prs = []
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(fetch_pr_details, pr) for pr in prs]
        for f in track(as_completed(futures), total=len(futures), description="Processing PRs..."):
            data = f.result()
            if data:
                detailed_prs.append(data)

    grouped = defaultdict(list)
    for d in detailed_prs:
        grouped[d["repo_name"]].append(d)

    label_info = f" | Label: {args.label}" if args.label else ""
    console.print(f"\n📊 [bold green]GitHub PR Stats for user: {args.user}{label_info}[/bold green]")
    console.print("─" * 60)

    for repo, pr_list in grouped.items():
        repo_link = pr_list[0]["repo_link"]
        console.print(f"🧱 [bold cyan]Repository:[/bold cyan] {repo} ([link={repo_link}]{repo_link}[/link])")
        console.print(f"   Total PRs: [magenta]{len(pr_list)}[/magenta]")

        for i, pr in enumerate(sorted(pr_list, key=lambda x: x["created_at"]), start=1):
            created = datetime.strptime(pr["created_at"], "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d")
            merged = (
                datetime.strptime(pr["merged_at"], "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d")
                if pr["merged_at"]
                else "Not merged yet"
            )

            console.print(
                f"   {i}. {pr['title']}\n"
                f"      Raised: {created}\n"
                f"      Merged: {merged}\n"
                f"      PR: [link={pr['pr_link']}]{pr['pr_link']}[/link]"
            )

        console.print("─" * 60)


if __name__ == "__main__":
    main()
