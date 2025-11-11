import argparse
import requests
from datetime import datetime
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.console import Console
from rich.table import Table
from rich.progress import track

console = Console()

GITHUB_API = "https://api.github.com"

def fetch(url):
    """Simple helper to fetch API data with error handling."""
    r = requests.get(url, headers={"Accept": "application/vnd.github+json"})
    if r.status_code == 200:
        return r.json()
    else:
        console.print(f"[red]Error fetching {url}: {r.status_code}[/red]")
        return None


def search_prs(username, start, end, label=None):
    """Fetch PRs made by the user within date range (optionally filtered by label)."""
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
        if "next" not in (r_link := requests.get(url).links):
            break
        if len(items) < 100:
            break
        page += 1

    return prs


def fetch_pr_details(pr):
    """Fetch full PR data (for merged_at, repo info, etc.)."""
    pr_url = pr.get("pull_request", {}).get("url")
    if not pr_url:
        return None
    details = fetch(pr_url)
    if not details:
        return None

    repo_name = details["base"]["repo"]["full_name"]
    repo_link = details["base"]["repo"]["html_url"]
    created = details["created_at"]
    merged = details["merged_at"]
    pr_title = details["title"]
    pr_html = details["html_url"]

    return {
        "repo_name": repo_name,
        "repo_link": repo_link,
        "title": pr_title,
        "created_at": created,
        "merged_at": merged,
        "pr_link": pr_html,
    }


def main():
    parser = argparse.ArgumentParser(description="Fetch GitHub PR stats for any public user.")
    parser.add_argument("--user", required=True, help="GitHub username to fetch PRs for")
    parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--label", help="Optional label to filter by (e.g., 'wocs')")
    args = parser.parse_args()

    start = f"{args.start}T00:00:00Z"
    end = f"{args.end}T23:59:59Z"

    # Fetch PRs
    prs = search_prs(args.user, start, end, args.label)
    if not prs:
        console.print("[yellow]No PRs found for the given user and filters.[/yellow]")
        return

    # Fetch full details in parallel
    detailed_prs = []
    console.print(f"[cyan]Fetching detailed PR info ({len(prs)} PRs)...[/cyan]")
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch_pr_details, pr) for pr in prs]
        for f in track(as_completed(futures), total=len(futures), description="Processing PRs..."):
            data = f.result()
            if data:
                detailed_prs.append(data)

    # Group by repository
    grouped = defaultdict(list)
    for d in detailed_prs:
        grouped[d["repo_name"]].append(d)

    # Display results
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
