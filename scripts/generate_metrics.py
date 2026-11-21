import json
import os
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

USERNAME = os.environ.get("GITHUB_USERNAME", "juandiegoceron-ux")
TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()

LANG_COLORS = {
    "Python": "#3572A5",
    "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6",
    "CSS": "#663399",
    "HTML": "#e34c26",
    "C++": "#f34b7d",
    "Dart": "#00B4AB",
    "Shell": "#89e051",
    "Verilog": "#b2b7f8",
    "PLpgSQL": "#336790",
    "SQL": "#e38c00",
    "CMake": "#DA3434",
}

def gh_get(url):
    headers = {"User-Agent": "juandiegoceron-metrics-bot", "Accept": "application/vnd.github+json"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as res:
        return json.loads(res.read().decode("utf-8"))

def fetch_total_contributions():
    # Uses GitHub's public contributions SVG/HTML or GraphQL when token is present
    if TOKEN:
        try:
            query = {
                "query": f'query {{ user(login: "{USERNAME}") {{ contributionsCollection {{ contributionCalendar {{ totalContributions }} }} }} }}'
            }
            req = urllib.request.Request(
                "https://api.github.com/graphql",
                data=json.dumps(query).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {TOKEN}",
                    "User-Agent": "juandiegoceron-metrics-bot",
                    "Content-Type": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=15) as res:
                data = json.loads(res.read().decode("utf-8"))
                return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]
        except Exception:
            pass
    try:
        req = urllib.request.Request(
            f"https://github.com/users/{USERNAME}/contributions",
            headers={"User-Agent": "Mozilla/5.0"},
        )
        with urllib.request.urlopen(req, timeout=15) as res:
            html = res.read().decode("utf-8", errors="ignore")
            m = re.search(r"([\d,]+)\s+contributions\s+in\s+the\s+last\s+year", html)
            if m:
                return int(m.group(1).replace(",", ""))
    except Exception:
        pass
    return None

def escape_xml(text):
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )

def build_stats_svg(user, stars, forks, contributions):
    public_repos = user.get("public_repos", 0)
    followers = user.get("followers", 0)
    contrib_label = str(contributions) if contributions is not None else f"{public_repos}+"
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    return f"""<svg width="440" height="175" viewBox="0 0 440 175" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="accentGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#00D9FF"/>
      <stop offset="100%" stop-color="#10B981"/>
    </linearGradient>
    <linearGradient id="ringGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#00D9FF"/>
      <stop offset="100%" stop-color="#10B981"/>
    </linearGradient>
  </defs>
  <rect x="0.5" y="0.5" width="439" height="174" rx="10" fill="#0D1117" stroke="#21262D"/>
  <rect x="0.5" y="0.5" width="439" height="3" rx="1.5" fill="url(#accentGrad)"/>

  <text x="24" y="34" fill="#00D9FF" font-family="'Segoe UI', Ubuntu, Helvetica, Arial, sans-serif" font-size="16" font-weight="700">GitHub Stats · {escape_xml(USERNAME)}</text>

  <g font-family="'Segoe UI', Ubuntu, Helvetica, Arial, sans-serif" font-size="13">
    <text x="24" y="66" fill="#8B949E">Contribuciones (último año):</text>
    <text x="255" y="66" fill="#FFFFFF" font-weight="700" text-anchor="end">{escape_xml(contrib_label)}</text>

    <text x="24" y="92" fill="#8B949E">Repositorios públicos:</text>
    <text x="255" y="92" fill="#FFFFFF" font-weight="700" text-anchor="end">{public_repos}</text>

    <text x="24" y="118" fill="#8B949E">Estrellas recibidas:</text>
    <text x="255" y="118" fill="#FFFFFF" font-weight="700" text-anchor="end">{stars}</text>

    <text x="24" y="144" fill="#8B949E">Seguidores / Forks:</text>
    <text x="255" y="144" fill="#FFFFFF" font-weight="700" text-anchor="end">{followers} / {forks}</text>
  </g>

  <g transform="translate(352, 94)">
    <circle cx="0" cy="0" r="38" stroke="#21262D" stroke-width="6" fill="none"/>
    <circle cx="0" cy="0" r="38" stroke="url(#ringGrad)" stroke-width="6" stroke-linecap="round" stroke-dasharray="195 240" transform="rotate(-90)" fill="none"/>
    <text x="0" y="-2" fill="#FFFFFF" font-family="'Segoe UI', Ubuntu, sans-serif" font-size="20" font-weight="800" text-anchor="middle" dominant-baseline="middle">LIVE</text>
    <text x="0" y="16" fill="#10B981" font-family="'Segoe UI', Ubuntu, sans-serif" font-size="9.5" font-weight="600" text-anchor="middle">GITHUB API</text>
  </g>

  <text x="416" y="162" fill="#484F58" font-family="'Segoe UI', Ubuntu, sans-serif" font-size="9" text-anchor="end">Sync {updated}</text>
</svg>
"""

def build_langs_svg(langs_dict):
    # Exclude noisy build-system metadata languages if real code languages exist
    filtered = {k: v for k, v in langs_dict.items() if k not in ("CMake", "Makefile")}
    if not filtered:
        filtered = langs_dict
    top = sorted(filtered.items(), key=lambda x: -x[1])[:6]
    total = sum(v for _, v in top) or 1

    bar_width = 392.0
    x_cursor = 0.0
    bar_rects = []
    for name, val in top:
        w = (val / total) * bar_width
        color = LANG_COLORS.get(name, "#00D9FF")
        bar_rects.append(
            f'    <rect x="{x_cursor:.2f}" y="0" width="{max(w, 1.5):.2f}" height="10" fill="{color}"/>'
        )
        x_cursor += w

    legend_items = []
    for idx, (name, val) in enumerate(top):
        col = idx % 2
        row = idx // 2
        lx = 24 + col * 200
        ly = 88 + row * 28
        pct = (val / total) * 100.0
        color = LANG_COLORS.get(name, "#00D9FF")
        legend_items.append(
            f'  <g transform="translate({lx}, {ly})">'
            f'<circle cx="5" cy="-4" r="5" fill="{color}"/>'
            f'<text x="17" y="0" fill="#E6EDF3" font-family="\'Segoe UI\', Ubuntu, sans-serif" font-size="12.5" font-weight="600">{escape_xml(name)}</text>'
            f'<text x="176" y="0" fill="#8B949E" font-family="\'Segoe UI\', Ubuntu, sans-serif" font-size="12" text-anchor="end">{pct:.1f}%</text>'
            f'</g>'
        )

    return f"""<svg width="440" height="175" viewBox="0 0 440 175" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="accentGradL" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#10B981"/>
      <stop offset="100%" stop-color="#00D9FF"/>
    </linearGradient>
    <clipPath id="barClip">
      <rect x="0" y="0" width="392" height="10" rx="5"/>
    </clipPath>
  </defs>
  <rect x="0.5" y="0.5" width="439" height="174" rx="10" fill="#0D1117" stroke="#21262D"/>
  <rect x="0.5" y="0.5" width="439" height="3" rx="1.5" fill="url(#accentGradL)"/>

  <text x="24" y="34" fill="#00D9FF" font-family="'Segoe UI', Ubuntu, Helvetica, Arial, sans-serif" font-size="16" font-weight="700">Lenguajes Más Usados</text>

  <g transform="translate(24, 48)" clip-path="url(#barClip)">
{chr(10).join(bar_rects)}
  </g>

{chr(10).join(legend_items)}
</svg>
"""

def main():
    user = gh_get(f"https://api.github.com/users/{USERNAME}")
    repos = gh_get(f"https://api.github.com/users/{USERNAME}/repos?per_page=100")

    stars = sum(r.get("stargazers_count", 0) for r in repos)
    forks = sum(r.get("forks_count", 0) for r in repos)
    contributions = fetch_total_contributions()

    langs = {}
    for r in repos:
        if r.get("fork"):
            continue
        lurl = r.get("languages_url")
        if lurl:
            try:
                ldata = gh_get(lurl)
                for k, v in ldata.items():
                    langs[k] = langs.get(k, 0) + v
            except Exception:
                pass

    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
    os.makedirs(out_dir, exist_ok=True)

    stats_svg = build_stats_svg(user, stars, forks, contributions)
    langs_svg = build_langs_svg(langs)

    # Validate XML strictly before saving
    ET.fromstring(stats_svg.encode("utf-8"))
    ET.fromstring(langs_svg.encode("utf-8"))

    with open(os.path.join(out_dir, "github-stats.svg"), "w", encoding="utf-8") as f:
        f.write(stats_svg)
    with open(os.path.join(out_dir, "top-langs.svg"), "w", encoding="utf-8") as f:
        f.write(langs_svg)

    print(f"Generated valid SVGs in {out_dir} (contributions={contributions}, stars={stars}, langs={len(langs)})")

if __name__ == "__main__":
    main()
