"""
SF Intelligence - Feature Analyzer
====================================
Compares fetched Salesforce org metadata against the Service Cloud
feature registry (config/service_cloud_features.json) and produces
a scored adoption report with gap analysis.

Outputs:
  - Feature status per record  (used / partial / unused)
  - Category-level adoption %
  - Overall adoption score
  - Prioritized gap list
"""

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

STATUS_USED    = "used"
STATUS_PARTIAL = "partial"
STATUS_UNUSED  = "unused"


# ──────────────────────────────────────────────
# Data Models
# ──────────────────────────────────────────────
@dataclass
class FeatureResult:
    id: str
    name: str
    category: str
    status: str                    # used | partial | unused
    impact_score: int              # 0-100
    adoption_signals: list         # what evidence was found
    gaps: list                     # what's missing
    recommendation: str
    roi_metric: str
    doc_url: str
    license_requirement: str
    confidence: float = 1.0        # 0.0-1.0 — how confident is the detection


@dataclass
class CategoryResult:
    id: str
    name: str
    total_features: int
    used_count: int
    partial_count: int
    unused_count: int
    adoption_pct: float
    features: list = field(default_factory=list)


@dataclass
class AnalysisReport:
    org_id: str
    instance_url: str
    analyzed_at: str
    total_features: int
    used_count: int
    partial_count: int
    unused_count: int
    overall_adoption_pct: float
    overall_score: float           # weighted by impact_score
    categories: list
    all_features: list
    top_gaps: list                 # top unused features sorted by impact
    quick_wins: list               # high-impact, low-effort unused features
    roadmap: list                  # phased adoption plan


# ──────────────────────────────────────────────
# Analyzer
# ──────────────────────────────────────────────
class FeatureAnalyzer:
    """
    Runs all feature detection rules against org metadata
    and produces a structured AnalysisReport.
    """

    def __init__(self, registry_path: Optional[str] = None):
        if registry_path is None:
            here = os.path.dirname(os.path.abspath(__file__))
            registry_path = os.path.join(here, "config", "service_cloud_features.json")


        with open(registry_path) as f:
            self.registry = json.load(f)

        logger.info(f"✅ Loaded feature registry: {self.registry['product']} v{self.registry['version']}")

    # ─────────────────────────────────────────
    # Main entry point
    # ─────────────────────────────────────────
    def analyze(self, metadata: dict) -> AnalysisReport:
        """
        Accepts the dict produced by fetcher.fetch_all() (or a file),
        runs all detection rules, and returns a full AnalysisReport.
        """
        import datetime
        logger.info("🔬 Running feature analysis...")

        category_results = []
        all_features     = []

        for cat in self.registry["feature_categories"]:
            feature_results = []
            for feat in cat["features"]:
                result = self._analyze_feature(feat, metadata)
                feature_results.append(result)
                all_features.append(result)
            cat_result = self._score_category(cat, feature_results)
            category_results.append(cat_result)

        # Global stats
        used_count    = sum(1 for f in all_features if f.status == STATUS_USED)
        partial_count = sum(1 for f in all_features if f.status == STATUS_PARTIAL)
        unused_count  = sum(1 for f in all_features if f.status == STATUS_UNUSED)
        total         = len(all_features)

        raw_pct   = round((used_count + partial_count * 0.5) / total * 100, 1) if total else 0
        # Weighted score (high-impact unused features hurt more)
        max_score = sum(f.impact_score for f in all_features)
        earned    = sum(
            f.impact_score if f.status == STATUS_USED else
            f.impact_score * 0.5 if f.status == STATUS_PARTIAL else 0
            for f in all_features
        )
        weighted_score = round(earned / max_score * 100, 1) if max_score else 0

        # Prioritize gaps
        unused_sorted = sorted(
            [f for f in all_features if f.status in (STATUS_UNUSED, STATUS_PARTIAL)],
            key=lambda x: x.impact_score, reverse=True
        )
        top_gaps  = unused_sorted[:10]
        quick_wins = [f for f in unused_sorted if f.impact_score >= 75][:5]

        roadmap   = self._build_roadmap(unused_sorted)

        report = AnalysisReport(
            org_id              = metadata.get("org_id", "unknown"),
            instance_url        = metadata.get("instance_url", ""),
            analyzed_at         = datetime.datetime.utcnow().isoformat(),
            total_features      = total,
            used_count          = used_count,
            partial_count       = partial_count,
            unused_count        = unused_count,
            overall_adoption_pct = raw_pct,
            overall_score       = weighted_score,
            categories          = category_results,
            all_features        = all_features,
            top_gaps            = top_gaps,
            quick_wins          = quick_wins,
            roadmap             = roadmap,
        )

        logger.info(
            f"✅ Analysis complete | Total: {total} | Used: {used_count} | "
            f"Unused: {unused_count} | Score: {weighted_score}%"
        )
        return report

    # ─────────────────────────────────────────
    # Feature detection logic
    # ─────────────────────────────────────────
    def _analyze_feature(self, feat: dict, metadata: dict) -> FeatureResult:
        """
        Runs all applicable detection rules for a single feature.
        Returns a FeatureResult with status and evidence.
        """
        det       = feat.get("detection", {})
        signals   = []
        gaps      = []

        # ── 1. Object record count check ──────
        obj_counts = metadata.get("object_record_counts", {})
        for obj in det.get("object_names", []):
            count = obj_counts.get(obj, -1)
            if count > 0:
                signals.append(f"Object '{obj}' has {count:,} records")
            elif count == 0:
                gaps.append(f"Object '{obj}' exists but has no records")
            else:
                gaps.append(f"Object '{obj}' not found or not accessible")

        # ── 2. SOQL-based counts ───────────────
        soql_obj = self._extract_soql_object(det.get("soql_check", ""))
        if soql_obj and soql_obj not in det.get("object_names", []):
            count = obj_counts.get(soql_obj, -1)
            if count > 0:
                signals.append(f"Detected activity on {soql_obj} ({count:,} records)")
            elif count == 0:
                gaps.append(f"No records found in {soql_obj}")

        # ── 3. Apex class detection ────────────
        org_classes = set(metadata.get("apex_classes", []))
        for cls in det.get("apex_classes", []):
            if any(cls.lower() in c.lower() for c in org_classes):
                signals.append(f"Custom Apex class '{cls}' detected")
            else:
                gaps.append(f"Expected Apex class '{cls}' not found")

        # ── 4. Flow detection ──────────────────
        flows = metadata.get("flows", {})
        if "Flow" in feat.get("id", "") or "flow" in feat.get("id", ""):
            if flows.get("total", 0) > 0:
                signals.append(f"Active Flows found: {flows['total']}")
                if flows.get("total", 0) < 5:
                    gaps.append("Very few flows configured — significant automation potential remains")
            else:
                gaps.append("No active Flows found")

        # ── 5. Special feature-specific checks ─
        signals, gaps = self._feature_specific_checks(feat["id"], metadata, signals, gaps)

        # ── 6. Score status ────────────────────
        status, confidence = self._determine_status(signals, gaps, feat)

        return FeatureResult(
            id                  = feat["id"],
            name                = feat["name"],
            category            = feat.get("category", ""),
            status              = status,
            impact_score        = feat.get("impact_score", 50),
            adoption_signals    = signals,
            gaps                = gaps,
            recommendation      = feat.get("recommendation", ""),
            roi_metric          = feat.get("roi_metric", ""),
            doc_url             = feat.get("doc_url", ""),
            license_requirement = feat.get("license_requirement", "Service Cloud"),
            confidence          = confidence,
        )

    def _feature_specific_checks(self, feat_id: str, metadata: dict,
                                  signals: list, gaps: list):
        """
        Custom detection logic for features that need more than record counts.
        """
        counts = metadata.get("object_record_counts", {})

        if feat_id == "omni_channel":
            channels = metadata.get("service_channels", [])
            if channels:
                signals.append(f"Omni-Channel: {len(channels)} service channel(s) configured")
            else:
                gaps.append("No Omni-Channel service channels configured")

        elif feat_id == "einstein_bots":
            bots = metadata.get("bots", [])
            if bots:
                active = [b for b in bots if b.get("Status") == "Active"]
                signals.append(f"Einstein Bots: {len(active)} active bot(s) found")
                if not active:
                    gaps.append("Bots exist but none are Active")
            else:
                gaps.append("No Einstein Bots configured")

        elif feat_id == "salesforce_knowledge":
            knowledge = metadata.get("knowledge", {})
            if knowledge.get("enabled"):
                signals.append(f"Knowledge enabled with {knowledge.get('article_count', 0):,} articles")
                if knowledge.get("article_count", 0) < 50:
                    gaps.append("Article library is small — insufficient for effective self-service")
            else:
                gaps.append("Salesforce Knowledge not enabled")

        elif feat_id == "entitlements_sla":
            ents = metadata.get("entitlements", {})
            if ents.get("entitlement_count", 0) > 0:
                signals.append(f"Entitlements configured: {ents['entitlement_count']:,} records")
            else:
                gaps.append("No Entitlement records found — SLAs not being tracked")

        elif feat_id == "experience_cloud_portal":
            networks = metadata.get("networks", [])
            if networks:
                active = [n for n in networks if n.get("Status") == "Live"]
                signals.append(f"Experience Cloud: {len(networks)} site(s), {len(active)} live")
            else:
                gaps.append("No Experience Cloud sites found")

        elif feat_id == "flow_automation":
            flows = metadata.get("flows", {})
            total_flows = flows.get("total", 0)
            if total_flows >= 10:
                signals.append(f"Good flow coverage: {total_flows} active flows")
            elif total_flows > 0:
                signals.append(f"Some flows active: {total_flows}")
                gaps.append(f"Only {total_flows} flows — consider expanding automation coverage")
            else:
                gaps.append("No active flows — missing major automation opportunity")

        elif feat_id == "csat_surveys":
            surveys = metadata.get("surveys", {})
            if surveys.get("count", 0) > 0:
                signals.append(f"Surveys configured: {surveys['count']}")
            else:
                gaps.append("No surveys configured — no systematic CSAT measurement")

        elif feat_id == "macros":
            macros = metadata.get("macros", {})
            if macros.get("macro_count", 0) > 0:
                signals.append(f"Macros: {macros['macro_count']} configured")
            else:
                gaps.append("No macros found — agents doing repetitive tasks manually")
            if macros.get("quick_text_count", 0) > 0:
                signals.append(f"Quick Text: {macros['quick_text_count']} entries")
            else:
                gaps.append("No Quick Text entries — missing response template library")

        elif feat_id == "service_analytics":
            reports = metadata.get("reports", {})
            if reports.get("service_reports", 0) >= 5:
                signals.append(f"Service reports found: {reports['service_reports']}")
            elif reports.get("service_reports", 0) > 0:
                signals.append(f"Some service reports: {reports['service_reports']}")
                gaps.append("Limited service reporting — consider expanding dashboards")
            else:
                gaps.append("No service-specific reports or dashboards found")

        elif feat_id == "live_chat":
            chat_count = counts.get("LiveChatTranscript", -1)
            if chat_count > 0:
                signals.append(f"Live chat transcripts: {chat_count:,}")
            else:
                gaps.append("No chat transcripts — Live Chat not in use")

        elif feat_id == "service_cloud_voice":
            voice_count = counts.get("VoiceCall", -1)
            if voice_count > 0:
                signals.append(f"Voice calls recorded: {voice_count:,}")
            else:
                gaps.append("No VoiceCall records — Service Cloud Voice not configured")

        return signals, gaps

    def _extract_soql_object(self, soql: str) -> Optional[str]:
        """Extract the object name from a SOQL COUNT query."""
        if not soql:
            return None
        parts = soql.upper().split("FROM")
        if len(parts) > 1:
            return parts[1].strip().split()[0].lower().replace("__kav", "")
        return None

    def _determine_status(self, signals: list, gaps: list, feat: dict):
        """
        Status decision tree:
          used    → clear evidence of active use, no critical gaps
          partial → some signals but also significant gaps
          unused  → no meaningful signals found
        """
        sig_count = len(signals)
        gap_count = len(gaps)

        if sig_count == 0:
            return STATUS_UNUSED, 0.9

        if sig_count > 0 and gap_count == 0:
            return STATUS_USED, 0.95

        if sig_count > 0 and gap_count > 0:
            # ratio-based decision
            ratio = sig_count / (sig_count + gap_count)
            if ratio >= 0.7:
                return STATUS_USED, 0.8
            elif ratio >= 0.35:
                return STATUS_PARTIAL, 0.75
            else:
                return STATUS_PARTIAL, 0.65

        return STATUS_UNUSED, 0.7

    def _score_category(self, cat: dict, feature_results: list) -> CategoryResult:
        """Aggregate feature results into a category-level summary."""
        used    = sum(1 for f in feature_results if f.status == STATUS_USED)
        partial = sum(1 for f in feature_results if f.status == STATUS_PARTIAL)
        unused  = sum(1 for f in feature_results if f.status == STATUS_UNUSED)
        total   = len(feature_results)
        pct     = round((used + partial * 0.5) / total * 100, 1) if total else 0

        return CategoryResult(
            id              = cat["id"],
            name            = cat["name"],
            total_features  = total,
            used_count      = used,
            partial_count   = partial,
            unused_count    = unused,
            adoption_pct    = pct,
            features        = feature_results,
        )

    # ─────────────────────────────────────────
    # Roadmap Builder
    # ─────────────────────────────────────────
    def _build_roadmap(self, unused_features: list) -> list:
        """
        Group unused/partial features into 3 adoption phases:
          Phase 1 (Quick Wins) : impact >= 80, standard license
          Phase 2 (Core Expand): impact 65-79 or add-on
          Phase 3 (Advanced)   : complex add-ons and AI
        """
        phases = [
            {
                "phase": 1,
                "title": "Quick Wins",
                "subtitle": "High-impact features on your existing license",
                "timeline": "Weeks 1–4",
                "features": [],
                "effort": "Low",
            },
            {
                "phase": 2,
                "title": "Core Expansion",
                "subtitle": "Extend key service capabilities",
                "timeline": "Months 2–3",
                "features": [],
                "effort": "Medium",
            },
            {
                "phase": 3,
                "title": "Advanced Transformation",
                "subtitle": "AI features and add-on products",
                "timeline": "Months 4–6",
                "features": [],
                "effort": "High",
            },
        ]

        add_on_keywords = ["Add-on", "Einstein", "Voice", "Field Service", "Workforce", "Digital Engagement"]

        for feat in unused_features:
            is_addon = any(kw in feat.license_requirement for kw in add_on_keywords)
            is_ai    = "Einstein" in feat.license_requirement

            if feat.impact_score >= 80 and not is_addon:
                phases[0]["features"].append(feat)
            elif is_ai:
                phases[2]["features"].append(feat)
            else:
                phases[1]["features"].append(feat)

        return phases
