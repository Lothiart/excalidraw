#!/usr/bin/env python3
"""Collecte les métriques DORA d'un dépôt GitHub.

Deux sources : l'API Deployments de GitHub pour les déploiements, un clone
local du dépôt pour les dates de commit.

Usage :
    python dora_metrics.py --repo owner/name --git ./clone --environment production

Le jeton d'accès est lu dans la variable d'environnement GITHUB_TOKEN.
Aucune dépendance externe : bibliothèque standard uniquement.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

API = "https://api.github.com"

# Force la sortie en UTF-8 : la console Windows utilise cp1252 par défaut
# et rendrait les accents illisibles.
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")


# --------------------------------------------------------------------- API

def api_get(path, token):
    """Appelle l'API GitHub et renvoie la réponse désérialisée."""
    req = urllib.request.Request(
        API + path,
        headers={
            "User-Agent": "dora-metrics",
            "Accept": "application/vnd.github+json",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as err:
        if err.code in (403, 429):
            reset = err.headers.get("x-ratelimit-reset")
            when = ""
            if reset:
                when = datetime.fromtimestamp(int(reset), timezone.utc).astimezone().strftime(" (réinitialisation à %H:%M)")
            sys.exit(f"Quota de l'API GitHub épuisé{when}. Définissez GITHUB_TOKEN.")
        sys.exit(f"GET {path} -> {err.code} {err.reason}")


def parse_date(value):
    """Convertit un horodatage ISO 8601 de l'API en datetime aware."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


# ------------------------------------------------------------ statistiques

def median(values):
    """Médiane d'une liste, None si la liste est vide."""
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def percentile_90(values):
    """P90 sans interpolation : valeur sous laquelle se situent 90 % des observations."""
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, -(-9 * len(ordered) // 10) - 1)
    return ordered[index]


def to_hours(delta):
    return delta.total_seconds() / 3600


def fmt_duration(hours):
    """Formate une durée en heures, ou en jours au-delà de 48 h."""
    if hours is None:
        return "n/a"
    if hours < 48:
        return f"{hours:.1f} h"
    return f"{hours / 24:.1f} j"


def fmt_ratio(value):
    return "n/a" if value is None else f"{value * 100:.1f} %"


# ------------------------------------------------------------ déploiements

def fetch_deployments(repo, environment, since, token):
    """Renvoie les déploiements réussis de l'environnement, dans la fenêtre.

    Chaque élément porte son sha, sa ref et l'horodatage du statut success.
    """
    collected = []
    for page in range(1, 11):
        query = urllib.parse.urlencode(
            {"environment": environment, "per_page": 100, "page": page}
        )
        batch = api_get(f"/repos/{repo}/deployments?{query}", token)
        if not batch:
            break
        collected.extend(batch)
        if parse_date(batch[-1]["created_at"]) < since or len(batch) < 100:
            break

    in_window = [d for d in collected if parse_date(d["created_at"]) >= since]

    successful = []
    for deployment in in_window:
        statuses = api_get(
            f"/repos/{repo}/deployments/{deployment['id']}/statuses?per_page=100", token
        )
        ok = [s for s in statuses if s["state"] == "success"]
        if not ok:
            continue
        first_success = min(ok, key=lambda s: parse_date(s["created_at"]))
        successful.append(
            {
                "id": deployment["id"],
                "sha": deployment["sha"],
                "ref": deployment.get("ref", ""),
                "deployed_at": parse_date(first_success["created_at"]),
            }
        )

    successful.sort(key=lambda d: d["deployed_at"])
    return successful


# ---------------------------------------------------------------- lead time

def git_output(git_dir, args):
    return subprocess.run(
        ["git", "-C", git_dir, *args],
        capture_output=True, text=True, check=True,
    ).stdout.strip()


def commit_exists(git_dir, sha):
    try:
        git_output(git_dir, ["cat-file", "-e", f"{sha}^{{commit}}"])
        return True
    except subprocess.CalledProcessError:
        return False


def lead_times(deployments, git_dir):
    """Lead time de chaque commit : écart entre son déploiement et sa committer date.

    Les commits d'un déploiement sont ceux présents dans son sha et absents
    du déploiement précédent.
    """
    durations = []
    batches = 0
    skipped = 0

    for previous, current in zip(deployments, deployments[1:]):
        if not commit_exists(git_dir, previous["sha"]) or not commit_exists(git_dir, current["sha"]):
            skipped += 1
            continue
        try:
            log = git_output(git_dir, ["log", "--format=%cI", f"{previous['sha']}..{current['sha']}"])
        except subprocess.CalledProcessError:
            skipped += 1
            continue
        if not log:
            continue
        batches += 1
        for line in log.splitlines():
            durations.append(to_hours(current["deployed_at"] - parse_date(line)))

    return durations, batches, skipped


# ----------------------------------------------------------------- incidents

def fetch_incidents(repo, label, since, token):
    """Renvoie les issues portant le label, avec leur date d'ouverture et de clôture."""
    incidents = []
    for page in range(1, 11):
        query = urllib.parse.urlencode(
            {
                "labels": label,
                "state": "all",
                "since": since.isoformat(),
                "per_page": 100,
                "page": page,
            }
        )
        batch = api_get(f"/repos/{repo}/issues?{query}", token)
        if not batch:
            break
        for issue in batch:
            if "pull_request" in issue:
                continue
            incidents.append(
                {
                    "number": issue["number"],
                    "opened_at": parse_date(issue["created_at"]),
                    "closed_at": parse_date(issue["closed_at"]) if issue.get("closed_at") else None,
                    "body": issue.get("body") or "",
                }
            )
        if len(batch) < 100:
            break
    return incidents


CAUSED_BY = re.compile(r"caused_by\s*:\s*(\d+)", re.IGNORECASE)


def link_incidents(incidents, deployments):
    """Associe chaque incident au déploiement dont l'identifiant figure dans son corps."""
    known_ids = {d["id"] for d in deployments}
    linked = []
    for incident in incidents:
        match = CAUSED_BY.search(incident["body"])
        if not match:
            continue
        deployment_id = int(match.group(1))
        if deployment_id in known_ids:
            linked.append({**incident, "deployment_id": deployment_id})
    return linked


# --------------------------------------------------------------------- main

def main():
    parser = argparse.ArgumentParser(description="Collecte les métriques DORA d'un dépôt GitHub.")
    parser.add_argument("--repo", required=True, help="dépôt au format owner/name")
    parser.add_argument("--git", required=True, help="chemin vers un clone local du dépôt")
    parser.add_argument("--environment", required=True, help="environnement de déploiement à retenir")
    parser.add_argument("--window", type=int, default=90, help="fenêtre glissante en jours (défaut : 90)")
    parser.add_argument("--incident-label", help="label des issues traitées comme incidents")
    parser.add_argument("--rework-prefix", help="préfixe de ref marquant un déploiement non planifié, ex. hotfix/")
    parser.add_argument("--json", action="store_true", help="sortie JSON")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    since = datetime.now(timezone.utc) - timedelta(days=args.window)

    if not args.json:
        print(f'Collecte des déploiements "{args.environment}"...', file=sys.stderr)

    deployments = fetch_deployments(args.repo, args.environment, since, token)
    durations, batches, skipped = lead_times(deployments, args.git)

    intervals = [
        to_hours(b["deployed_at"] - a["deployed_at"])
        for a, b in zip(deployments, deployments[1:])
    ]

    result = {
        "repo": args.repo,
        "environment": args.environment,
        "window_days": args.window,
        "since": since.date().isoformat(),
        "deployment_count": len(deployments),
        "deployment_frequency_per_day": len(deployments) / args.window,
        "median_interval_hours": median(intervals),
        "change_lead_time_p50_hours": median(durations),
        "change_lead_time_p90_hours": percentile_90(durations),
        "commits_analysed": len(durations),
        "batches_analysed": batches,
        "batches_skipped": skipped,
        "change_fail_rate": None,
        "failed_deployment_recovery_time_p50_hours": None,
        "deployment_rework_rate": None,
    }

    # Le taux d'échec et le temps de restauration exigent le rattachement
    # d'un incident au déploiement qui l'a causé.
    if args.incident_label and deployments:
        incidents = fetch_incidents(args.repo, args.incident_label, since, token)
        linked = link_incidents(incidents, deployments)
        result["incidents_found"] = len(incidents)
        result["incidents_linked"] = len(linked)
        if linked:
            failing = {i["deployment_id"] for i in linked}
            result["change_fail_rate"] = len(failing) / len(deployments)
            recoveries = [
                to_hours(i["closed_at"] - i["opened_at"]) for i in linked if i["closed_at"]
            ]
            result["failed_deployment_recovery_time_p50_hours"] = median(recoveries)

    # Le retravail se lit sur la ref du déploiement.
    if args.rework_prefix and deployments:
        rework = [d for d in deployments if d["ref"].startswith(args.rework_prefix)]
        result["deployment_rework_rate"] = len(rework) / len(deployments)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    def line(label, value):
        print(f"  {label:<36} {value}")

    print(f"\n=== DORA : {args.repo} ===")
    print(f"Fenêtre : {args.window} jours (depuis le {result['since']})")
    print(f'Environnement : "{args.environment}"\n')

    print("DÉBIT")
    line("Deployment frequency", f"{result['deployment_frequency_per_day']:.3f} /jour  ({result['deployment_count']} déploiements)")
    line("  délai médian entre deux", fmt_duration(result["median_interval_hours"]))
    line("Change lead time (P50)", fmt_duration(result["change_lead_time_p50_hours"]))
    line("Change lead time (P90)", fmt_duration(result["change_lead_time_p90_hours"]))
    line("  base de calcul", f"{result['commits_analysed']} commits / {result['batches_analysed']} lots")
    if skipped:
        line("  lots ignorés (sha absent)", str(skipped))
    line("Failed deployment recovery time", fmt_duration(result["failed_deployment_recovery_time_p50_hours"]))

    print("\nINSTABILITÉ")
    line("Change fail rate", fmt_ratio(result["change_fail_rate"]))
    line("Deployment rework rate", fmt_ratio(result["deployment_rework_rate"]))

    if args.incident_label:
        print("\nINCIDENTS")
        line(f'Issues "{args.incident_label}"', str(result.get("incidents_found", 0)))
        line("  rattachées à un déploiement", str(result.get("incidents_linked", 0)))
    print()


if __name__ == "__main__":
    main()
