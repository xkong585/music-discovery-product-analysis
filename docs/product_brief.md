# Music discovery and repeat listening

## Decision to support

A music product manager has limited capacity for the next discovery experience. Compare four options: more active exploration, easier access to familiar music, a recent-discovery retrieval entry point, or no feature investment until measurement improves. Do not assume repeat listening is always better.

## User need hypothesis

Some listeners may want to revisit a newly encountered artist but struggle to retrieve it; others may be satisfied with a single exploration. No interviews have been conducted. Public logs alone cannot distinguish those needs. The main deliverable is an evidence-calibrated decision memo, not a recommendation algorithm or an invented growth result.

## Measurement contract

- Unit: recorded user × artist first appearance, calculated using all available pre-cutoff history. This is not first-ever discovery.
- UTC calendar day d is excluded from cross-day repeat. Outcome window is [d+1, d+8).
- Main eligibility: first appearance ≥60 calendar days after the user's first record; observed activity in the prior 28 complete days; d+8 no later than exclusive 2009-05-05 administrative cutoff. No selection on future activity.
- A 90-day wash-in changes eligibility, not the outcome. The reliable-ID subset requires original IDs throughout that artist's retained records. The common 28-day cohort requires d+29 ≤ cutoff.
- Main estimand: average the repeat proportion within each user, then average users equally. Event-weighted proportion is a separate estimand.
- Exploration: newly observed distinct artists / all distinct artists in [d−28,d). Higher exploration ≥0.5. Higher activity ≥14 recorded active days in that same past window. Thresholds are transparent analysis choices, not optimized product settings.
- Bootstrap the per-user means 2,000 times with fixed seed. Each group has its own descriptive interval; overlapping users across states prevent interpreting groups as independent experimental arms.
- Future activity: observed active days in [d+1,d+29); complementary [d+8,d+29) reduces mechanical overlap with repeat. These are recording proxies, not verified continuous usage or subscription retention.

## Data quality and limitations

Use the original author/MTG-UPF Last.fm release on Zenodo, verify MD5, retain archive/TSV SHA-256. No generated listening records. Exclude profiles from analysis and publication. Preserve genuine repeated listens; identical tuple candidates are diagnostics, not automatically errors.

Artist identity: original MBID first; unique normalized-name-to-MBID mapping when missing; marked name-only fallback when no MBID exists; ambiguous missing-ID names excluded. Mapping uses the whole file for entity resolution; behavioral features and first appearances use pre-cutoff records. Possible merged homonyms and split variants remain limitations. A reliable-ID sensitivity is published.

The checksum-verified file contains post-description timestamps, including June 2009 and isolated 2010/2013 records. Use the conservative publisher-described May boundary and audit all excluded records. A shared administrative cutoff does not guarantee that each user continuously synchronized history. Daily activity zeros mean no recorded event, not proven non-use.

## Research and product gates

Recruit consenting participants only if available; record real recent discovery/retrieval episodes and counterexamples. No participant count or finding is claimed here. Prototype recent discovery only when observed episodes support retrieval friction. Compare task success, errors and time using balanced task order; a small study cannot measure population retention lift.

An eventual product experiment would randomize eligible users, retain all randomized users in the denominator, and measure an observable user-level outcome plus exploration, negative feedback and reliability guardrails. The conditional repeat proportion among discovered artists cannot automatically become an experiment's primary causal metric because discovery itself may be affected by treatment.

## Stop conditions

Stop feature development if retrieval need is unsupported, if data definitions dominate the pattern, or if a simpler entry point solves the task. Ship a recommendation to improve measurement or conduct research when that is the strongest supported action.
