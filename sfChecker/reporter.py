"""
SF Intelligence - Report Generator
=====================================
Converts an AnalysisReport into rich, shareable outputs:
  - JSON  : machine-readable full report (for Apex ingestion)
  - HTML  : standalone visual report for stakeholders
  - TXT   : plain text summary for quick sharing

Usage:
    from python.core.reporter import ReportGenerator
    gen = ReportGenerator(report)
    gen.save_html("output/report.html")
    gen.save_json("output/report.json")
    gen.print_summary()
"""

import json
import logging
import os
from dataclasses import asdict
from datetime import datetime

logger = logging.getLogger(__name__)

STATUS_COLOR = {
    "used":    "#00C4A1",
    "partial": "#FFD23F",
    "unused":  "#FF6B35",
}
STATUS_ICON = {
    "used":    "✅",
    "partial": "⚠️",
    "unused":  "🔴",
}


class ReportGenerator:

    def __init__(self, report):
        self.report = report

    # ─────────────────────────────────────────
    # JSON Output
    # ─────────────────────────────────────────
    def to_json(self) -> str:
        """Serialize the full report to JSON (Apex-consumable format)."""
        def serialize(obj):
            if hasattr(obj, "__dataclass_fields__"):
                return asdict(obj)
            return str(obj)

        return json.dumps(
            {
                "schemaVersion":     "1.0",
                "product":           "SF Cloud Intelligence",
                "org_id":            self.report.org_id,
                "instance_url":      self.report.instance_url,
                "analyzed_at":       self.report.analyzed_at,
                "summary": {
                    "total_features":       self.report.total_features,
                    "used_count":           self.report.used_count,
                    "partial_count":        self.report.partial_count,
                    "unused_count":         self.report.unused_count,
                    "overall_adoption_pct": self.report.overall_adoption_pct,
                    "overall_score":        self.report.overall_score,
                },
                "categories":  [asdict(c) for c in self.report.categories],
                "features":    [asdict(f) for f in self.report.all_features],
                "top_gaps":    [asdict(f) for f in self.report.top_gaps],
                "quick_wins":  [asdict(f) for f in self.report.quick_wins],
                "roadmap":     self._serialize_roadmap(),
            },
            indent=2, default=serialize
        )

    def save_json(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(self.to_json())
        logger.info(f"📄 JSON report saved: {path}")

    def _serialize_roadmap(self):
        result = []
        for phase in self.report.roadmap:
            result.append({
                "phase":    phase["phase"],
                "title":    phase["title"],
                "subtitle": phase["subtitle"],
                "timeline": phase["timeline"],
                "effort":   phase["effort"],
                "features": [asdict(f) for f in phase["features"]],
            })
        return result

    # ─────────────────────────────────────────
    # Plain Text Summary
    # ─────────────────────────────────────────
    def print_summary(self):
        r = self.report
        sep = "=" * 65

        print(f"\n{sep}")
        print(f"  SF SERVICE CLOUD FEATURE INTELLIGENCE REPORT")
        print(f"{sep}")
        print(f"  Org:       {r.org_id}")
        print(f"  Analyzed:  {r.analyzed_at[:19].replace('T', ' ')} UTC")
        print(f"  Score:     {r.overall_score}% (weighted adoption)")
        print(f"{sep}")
        print(f"  Total Features : {r.total_features}")
        print(f"  ✅ Used         : {r.used_count}")
        print(f"  ⚠️  Partial      : {r.partial_count}")
        print(f"  🔴 Unused       : {r.unused_count}")
        print(f"{sep}")
        print(f"\n  📊 CATEGORY BREAKDOWN")
        print(f"  {'Category':<30} {'Adoption':>8} {'Used':>5} {'Partial':>8} {'Unused':>7}")
        print(f"  {'-'*60}")
        for cat in r.categories:
            bar = self._text_bar(cat.adoption_pct)
            print(f"  {cat.name:<30} {cat.adoption_pct:>6.1f}%  {cat.used_count:>3}    {cat.partial_count:>4}    {cat.unused_count:>4}")

        print(f"\n  🔴 TOP GAPS (by impact score)")
        for i, feat in enumerate(r.top_gaps[:8], 1):
            print(f"  {i:>2}. [{feat.impact_score:>3}] {feat.name} ({feat.status.upper()})")
            print(f"      → {feat.recommendation[:75]}...")

        print(f"\n  ⚡ QUICK WINS (implement immediately)")
        for feat in r.quick_wins:
            print(f"  • {feat.name} — {feat.roi_metric}")

        print(f"\n  🗺️  ROADMAP")
        for phase in r.roadmap:
            if phase["features"]:
                print(f"\n  Phase {phase['phase']}: {phase['title']} [{phase['timeline']}]")
                for feat in phase["features"][:4]:
                    print(f"    • {feat.name}")

        print(f"\n{sep}\n")

    def _text_bar(self, pct: float, width: int = 15) -> str:
        filled = int(pct / 100 * width)
        return "█" * filled + "░" * (width - filled)

    # ─────────────────────────────────────────
    # HTML Report
    # ─────────────────────────────────────────
    def to_html(self) -> str:
        r = self.report
        feature_rows = "".join(self._feature_row(f) for f in r.all_features)
        category_cards = "".join(self._category_card(c) for c in r.categories)
        roadmap_html = self._roadmap_html()
        quick_win_html = "".join(self._quick_win_card(f) for f in r.quick_wins)
        date_str = r.analyzed_at[:10]

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>SF Service Cloud Intelligence Report — {date_str}</title>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet"/>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0;}}
body{{font-family:'DM Mono',monospace;background:#060d1f;color:#e8e6e0;line-height:1.6;}}
a{{color:#00A1E0;text-decoration:none;}}
a:hover{{text-decoration:underline;}}
.container{{max-width:1100px;margin:0 auto;padding:32px 24px;}}
header{{background:linear-gradient(135deg,#032D60,#0B1F46);border-bottom:1px solid rgba(0,161,224,0.2);padding:28px 40px;display:flex;align-items:center;justify-content:space-between;}}
.logo{{font-family:'Syne',sans-serif;font-weight:800;font-size:1.3rem;color:white;}}
.logo span{{color:#00A1E0;}}
.meta{{font-size:0.72rem;color:rgba(255,255,255,0.45);text-align:right;}}
/* Stats */
.stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin:32px 0;}}
.stat-card{{background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:14px;padding:20px;text-align:center;border-bottom:3px solid;}}
.stat-card.blue{{border-bottom-color:#00A1E0;}} .stat-card.green{{border-bottom-color:#00C4A1;}}
.stat-card.orange{{border-bottom-color:#FF6B35;}} .stat-card.yellow{{border-bottom-color:#FFD23F;}}
.stat-val{{font-family:'Syne',sans-serif;font-size:2.2rem;font-weight:800;}}
.stat-card.blue .stat-val{{color:#00A1E0;}} .stat-card.green .stat-val{{color:#00C4A1;}}
.stat-card.orange .stat-val{{color:#FF6B35;}} .stat-card.yellow .stat-val{{color:#FFD23F;}}
.stat-lbl{{font-size:0.65rem;letter-spacing:0.12em;text-transform:uppercase;color:rgba(255,255,255,0.4);margin-bottom:8px;}}
/* Score Banner */
.score-banner{{background:rgba(0,161,224,0.07);border:1px solid rgba(0,161,224,0.2);border-radius:16px;padding:28px 32px;margin-bottom:28px;display:flex;align-items:center;gap:32px;}}
.score-ring{{text-align:center;flex-shrink:0;}}
.score-num{{font-family:'Syne',sans-serif;font-size:3rem;font-weight:800;color:#00A1E0;line-height:1;}}
.score-sub{{font-size:0.65rem;color:rgba(255,255,255,0.4);letter-spacing:0.1em;text-transform:uppercase;}}
.score-text h2{{font-family:'Syne',sans-serif;font-size:1.2rem;margin-bottom:8px;}}
.score-text p{{font-size:0.8rem;color:rgba(255,255,255,0.55);}}
/* Sections */
.section{{margin-bottom:36px;}}
.section-title{{font-family:'Syne',sans-serif;font-size:1rem;font-weight:700;margin-bottom:16px;padding-bottom:8px;border-bottom:1px solid rgba(255,255,255,0.07);}}
/* Category Cards */
.cat-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;}}
.cat-card{{background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.07);border-radius:12px;padding:16px;}}
.cat-name{{font-family:'Syne',sans-serif;font-size:0.82rem;font-weight:700;margin-bottom:10px;}}
.pbar-track{{height:5px;background:rgba(255,255,255,0.07);border-radius:10px;margin-bottom:8px;overflow:hidden;}}
.pbar-fill{{height:100%;border-radius:10px;}}
.cat-pct{{font-size:0.7rem;color:rgba(255,255,255,0.4);}}
/* Feature Table */
table{{width:100%;border-collapse:collapse;font-size:0.78rem;}}
th{{text-align:left;padding:10px 14px;font-size:0.63rem;letter-spacing:0.1em;text-transform:uppercase;color:rgba(255,255,255,0.35);border-bottom:1px solid rgba(255,255,255,0.07);}}
td{{padding:11px 14px;border-bottom:1px solid rgba(255,255,255,0.04);vertical-align:top;}}
tr:hover td{{background:rgba(255,255,255,0.02);}}
.status-badge{{display:inline-block;padding:2px 9px;border-radius:10px;font-size:0.62rem;letter-spacing:0.05em;font-weight:500;}}
.status-used{{background:rgba(0,196,161,0.15);color:#00C4A1;}}
.status-partial{{background:rgba(255,210,63,0.15);color:#FFD23F;}}
.status-unused{{background:rgba(255,107,53,0.15);color:#FF6B35;}}
.impact-bar{{display:inline-block;height:4px;background:rgba(0,161,224,0.4);border-radius:4px;vertical-align:middle;}}
/* Quick Wins */
.qw-grid{{display:grid;grid-template-columns:1fr 1fr;gap:12px;}}
.qw-card{{background:rgba(0,196,161,0.06);border:1px solid rgba(0,196,161,0.15);border-radius:12px;padding:16px;}}
.qw-name{{font-family:'Syne',sans-serif;font-size:0.85rem;font-weight:700;color:#00C4A1;margin-bottom:4px;}}
.qw-roi{{font-size:0.73rem;color:rgba(255,255,255,0.5);margin-bottom:8px;}}
.qw-rec{{font-size:0.72rem;color:rgba(255,255,255,0.65);}}
/* Roadmap */
.phase{{display:flex;gap:16px;margin-bottom:12px;}}
.phase-dot{{min-width:36px;height:36px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-family:'Syne',sans-serif;font-weight:800;font-size:0.8rem;flex-shrink:0;border:2px solid;margin-top:4px;}}
.p1{{background:rgba(0,161,224,0.12);border-color:#00A1E0;color:#00A1E0;}}
.p2{{background:rgba(0,196,161,0.12);border-color:#00C4A1;color:#00C4A1;}}
.p3{{background:rgba(255,107,53,0.12);border-color:#FF6B35;color:#FF6B35;}}
.phase-body{{flex:1;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:12px;padding:16px;}}
.phase-header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;}}
.phase-title{{font-family:'Syne',sans-serif;font-size:0.9rem;font-weight:700;}}
.phase-tag{{font-size:0.62rem;background:rgba(255,255,255,0.05);padding:3px 10px;border-radius:10px;color:rgba(255,255,255,0.4);}}
.phase-items li{{font-size:0.75rem;color:rgba(255,255,255,0.6);margin-left:16px;margin-bottom:4px;}}
footer{{text-align:center;padding:32px;font-size:0.7rem;color:rgba(255,255,255,0.2);border-top:1px solid rgba(255,255,255,0.05);margin-top:40px;}}
</style>
</head>
<body>
<header>
  <div class="logo">☁️ <span>SF</span> Cloud Intelligence</div>
  <div class="meta">Org: {r.org_id}<br/>Generated: {date_str}</div>
</header>
<div class="container">

  <!-- Stats -->
  <div class="stats">
    <div class="stat-card blue"><div class="stat-lbl">Total Features</div><div class="stat-val">{r.total_features}</div></div>
    <div class="stat-card green"><div class="stat-lbl">Features Used</div><div class="stat-val">{r.used_count}</div></div>
    <div class="stat-card orange"><div class="stat-lbl">Unused Gaps</div><div class="stat-val">{r.unused_count}</div></div>
    <div class="stat-card yellow"><div class="stat-lbl">Adoption Score</div><div class="stat-val">{r.overall_score:.0f}%</div></div>
  </div>

  <!-- Score Banner -->
  <div class="score-banner">
    <div class="score-ring">
      <div class="score-num">{r.overall_score:.0f}%</div>
      <div class="score-sub">Weighted Score</div>
    </div>
    <div class="score-text">
      <h2>Service Cloud Feature Adoption Analysis</h2>
      <p>Your org is using {r.used_count} of {r.total_features} available features.
         {r.unused_count} capabilities are unused and {r.partial_count} are only partially configured.
         The roadmap below provides a phased path to full adoption.</p>
    </div>
  </div>

  <!-- Category Breakdown -->
  <div class="section">
    <div class="section-title">📊 Category Breakdown</div>
    <div class="cat-grid">{category_cards}</div>
  </div>

  <!-- Quick Wins -->
  <div class="section">
    <div class="section-title">⚡ Quick Wins — Implement This Week</div>
    <div class="qw-grid">{quick_win_html}</div>
  </div>

  <!-- Feature Map -->
  <div class="section">
    <div class="section-title">🗺️ Complete Feature Intelligence Map</div>
    <table>
      <thead><tr>
        <th>Feature</th><th>Category</th><th>Status</th>
        <th>Impact</th><th>License</th><th>Recommendation</th>
      </tr></thead>
      <tbody>{feature_rows}</tbody>
    </table>
  </div>

  <!-- Roadmap -->
  <div class="section">
    <div class="section-title">🗺️ Recommended Adoption Roadmap</div>
    {roadmap_html}
  </div>

</div>
<footer>Generated by SF Cloud Intelligence Platform &nbsp;|&nbsp; {date_str} &nbsp;|&nbsp; <a href="https://help.salesforce.com">help.salesforce.com</a></footer>
</body>
</html>"""

    def _feature_row(self, f) -> str:
        color = STATUS_COLOR.get(f.status, "#888")
        impact_w = int(f.impact_score * 0.7)
        return f"""<tr>
          <td><strong>{f.name}</strong></td>
          <td style="color:rgba(255,255,255,0.45);font-size:0.7rem">{f.category}</td>
          <td><span class="status-badge status-{f.status}">{STATUS_ICON[f.status]} {f.status.title()}</span></td>
          <td><span class="impact-bar" style="width:{impact_w}px;background:{color}"></span> {f.impact_score}</td>
          <td style="font-size:0.68rem;color:rgba(255,255,255,0.4)">{f.license_requirement}</td>
          <td style="font-size:0.72rem;color:rgba(255,255,255,0.55)">{f.recommendation[:90]}... <a href="{f.doc_url}" target="_blank">→ Docs</a></td>
        </tr>"""

    def _category_card(self, c) -> str:
        pct = c.adoption_pct
        color = "#00C4A1" if pct >= 70 else "#FFD23F" if pct >= 40 else "#FF6B35"
        w = int(pct)
        return f"""<div class="cat-card">
          <div class="cat-name">{c.name}</div>
          <div class="pbar-track"><div class="pbar-fill" style="width:{w}%;background:{color}"></div></div>
          <div class="cat-pct">{pct:.0f}% — {c.used_count} used, {c.partial_count} partial, {c.unused_count} unused</div>
        </div>"""

    def _quick_win_card(self, f) -> str:
        return f"""<div class="qw-card">
          <div class="qw-name">{f.name}</div>
          <div class="qw-roi">💰 {f.roi_metric}</div>
          <div class="qw-rec">{f.recommendation}</div>
          <div style="margin-top:8px"><a href="{f.doc_url}" target="_blank" style="font-size:0.7rem">→ Salesforce Docs</a></div>
        </div>"""

    def _roadmap_html(self) -> str:
        html = ""
        phase_class = ["p1", "p2", "p3"]
        for phase in self.report.roadmap:
            if not phase["features"]:
                continue
            items = "".join(f"<li>{f.name} — {f.roi_metric}</li>" for f in phase["features"])
            cls = phase_class[phase["phase"] - 1]
            html += f"""<div class="phase">
              <div class="phase-dot {cls}">{phase['phase']}</div>
              <div class="phase-body">
                <div class="phase-header">
                  <div class="phase-title">{phase['title']} — {phase['subtitle']}</div>
                  <div class="phase-tag">{phase['timeline']} · {phase['effort']} Effort</div>
                </div>
                <ul class="phase-items">{items}</ul>
              </div>
            </div>"""
        return html

    def save_html(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(self.to_html())
        logger.info(f"📊 HTML report saved: {path}")
