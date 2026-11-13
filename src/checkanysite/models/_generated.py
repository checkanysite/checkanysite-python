"""Generated from openapi.json by scripts/generate_models.py: do not edit by hand.
Regenerate with `pnpm sdk:python:models` from the repository root (ADR 0102)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Optional

from pydantic import Field

from checkanysite.models._base import Model, ResponseModel


class AiReadiness(Model):
    """
    How easily AI tools can find, read and use the site: a score out of 100 from checks, each with its evidence, and what to fix first. What the site lets AI crawlers do is listed apart and never scored: keeping AI out is the site’s choice.
    """

    answer: str
    """
    The answer in a sentence ("Ready for AI: it scores 82 of 100.").
    """
    note: str
    """
    What it lets AI crawlers do, in a sentence: the site’s choice, never scored.
    """
    score: Optional[int]
    """
    Out of 100; null when too little could be checked to say.
    """
    version: str
    """
    The readiness formula’s version (/changelog).
    """
    checked_at: Annotated[datetime, Field(alias="checkedAt")]
    """
    When AI access was checked: the scan’s own date, or for a result made before we checked AI access, the newer check that answers in its place.
    """
    level: Optional[AiReadinessLevel]
    """
    The highest level it reaches; null when it reaches none.
    """
    levels: list[AiReadinessLevelState]
    """
    Every level, lowest first; one counts once its checks and every level before it are met.
    """
    next: Optional[AiReadinessNext]
    """
    The first level not reached and what it needs; null once every level is.
    """
    comparison: Optional[str]
    """
    Where the score stands among the most visited sites we read, in a sentence; null without a score.
    """
    partial: bool
    """
    True when some checks couldn’t be made or are still checking; the rest is scaled to 100.
    """
    checks: list[AiReadinessCheck]
    """
    Each check that counts, as the score reads it.
    """
    fix_prompt: Annotated[Optional[str], Field(alias="fixPrompt")]
    """
    The fixes that aren’t optional, most points first, as one prompt for an AI coding assistant that ends with where to check again; the optional ones once only they are left. Null when there is nothing to fix.
    """
    crawlers: list[AiReadinessCrawler]
    """
    Every AI crawler we know, as the site’s robots.txt treats it; never scored.
    """


class AiReadinessCheck(Model):
    key: str
    """
    A stable key: `text`, `listing`, `facts`, `structured`, `sitemap`, `robots`, `agents` (every file for AI agents at once: one found is enough), `llms`, `links` or `markdown`; new keys may appear.
    """
    group: str
    """
    `find` (can AI find its pages?), `read` (can AI read it?) or `agents` (can agents use it?).
    """
    label: str
    """
    The check’s name ("Structured data").
    """
    state: str
    """
    `found`, `partial`, `none`, `info` or `unknown` (we couldn’t check it).
    """
    value: str
    """
    What we found, in words.
    """
    evidence: list[Evidence]
    """
    Where it was seen, with the exact line.
    """
    points: int
    """
    The points it earns.
    """
    max: int
    """
    The most it can earn.
    """
    met: bool
    """
    True when it earns its full points.
    """
    unchecked: bool
    """
    True when we couldn’t check it, or it is still checking: it is left out of the score.
    """
    optional: bool
    """
    True for what few sites have yet; it is worth few points.
    """
    fix: Optional[AiReadinessCheckFix]
    """
    What to do about it; null when it is met or couldn’t be checked.
    """


class AiReadinessCheckFix(Model):
    """
    What to do about it; null when it is met or couldn’t be checked.
    """

    gain: int
    """
    The points fixing it would add to the score.
    """
    why: str
    """
    Why it matters.
    """
    todo: str
    """
    What to do, in a line.
    """
    prompt: str
    """
    A prompt for an AI coding assistant to fix it, with the site’s address and what we found.
    """


class AiReadinessCrawler(Model):
    name: str
    """
    The crawler, as its maker writes it ("GPTBot").
    """
    company: Optional[str]
    """
    The AI company it belongs to, for those we follow.
    """
    role: str
    """
    What it fetches pages for: `training` models, or `answers` (AI assistants and AI search).
    """
    access: str
    """
    `out` of the whole site, kept from `some` paths, or let `in`.
    """
    line: Optional[int]
    """
    The robots.txt line of the group that decides it; null when no group names it.
    """


class AiReadinessLevel(Model):
    """
    The highest level it reaches; null when it reaches none.
    """

    id: str
    """
    The level’s id ("readable").
    """
    name: str
    """
    Its name ("Readable").
    """
    meaning: str
    """
    What reaching it means, in a sentence.
    """


class AiReadinessLevelState(Model):
    id: str
    """
    `findable`, `readable`, `ai-friendly` or `agent-ready`; new levels may appear.
    """
    name: str
    """
    The level’s name.
    """
    reached: bool
    """
    True when the site reaches it.
    """


class AiReadinessNext(Model):
    """
    The first level not reached and what it needs; null once every level is.
    """

    id: str
    """
    The level’s id.
    """
    name: str
    """
    Its name.
    """
    needs: list[str]
    """
    The keys of the checks it still needs, as `checks` lists them.
    """


class AiTraces(Model):
    """
    Traces of the AI website builders and patterns we found. Evidence, never a verdict about who made the site.
    """

    level: str
    """
    `high`: an AI builder’s own trace; `medium`: a combination of its weaker traces only; `none`: no traces found.
    """
    builders: list[AiTracesBuilder]
    """
    Each builder whose traces we found; empty when none.
    """
    patterns: list[AiTracesPattern]
    """
    Design patterns common on AI-built pages; they never set the level on their own.
    """


class AiTracesBuilder(Model):
    id: str
    """
    Our id for the builder ("lovable").
    """
    name: str
    """
    The builder’s name ("Lovable").
    """
    kind: str
    """
    `ai` for AI builders, `general` for other site builders.
    """
    url: str
    """
    The builder’s own site.
    """
    strength: str
    """
    `signature`: one trace of its own; `combination`: weaker traces that count only together.
    """
    combination: Optional[str]
    """
    For a combination, what its traces mean together.
    """
    evidence: list[Evidence]
    """
    Where each trace was seen, with the exact line.
    """


class AiTracesPattern(Model):
    id: str
    """
    Our id for the pattern.
    """
    name: str
    """
    The pattern’s name.
    """
    note: str
    """
    Why it is weak evidence on its own.
    """
    evidence: list[Evidence]
    """
    Where it was seen.
    """


class DnsRecords(Model):
    """
    The domain’s DNS records as the scan read them, over DNS over HTTPS, and the network announcing its address.
    """

    read: bool
    """
    False when the lookup failed: then there are no records to give.
    """
    records: list[DnsRecordsRecord]
    """
    Each record we read.
    """
    dnssec: Optional[bool]
    """
    Whether the resolver validated the answer with DNSSEC; null when that didn’t answer.
    """
    incomplete: list[str]
    """
    The questions ("example.com TXT") that didn’t answer whole: a record missing from one of them may still exist.
    """
    source: Optional[str]
    """
    The resolver that answered.
    """
    checked_at: Annotated[Optional[datetime], Field(alias="checkedAt")]
    """
    When we asked.
    """
    network: Optional[DnsRecordsNetwork]
    """
    The network announcing the site’s address, never a place.
    """


class DnsRecordsNetwork(Model):
    """
    The network announcing the site’s address, never a place.
    """

    asn: int
    """
    The autonomous system number, such as 13335.
    """
    name: str
    """
    The organisation announcing the address ("Cloudflare, Inc.").
    """
    prefix: Optional[str]
    """
    The routed block holding the address ("104.16.16.0/20").
    """
    source: str
    """
    Who answered.
    """
    checked_at: Annotated[datetime, Field(alias="checkedAt")]
    """
    When we asked.
    """


class DnsRecordsRecord(Model):
    name: str
    """
    The name asked about: the domain, its www host, or a policy entry such as `_dmarc`.
    """
    type: str
    """
    The record type. SVCB and HTTPS come only from `_agents`, where a site names its AI agents.
    """
    value: str
    """
    The record’s value, as the resolver gave it.
    """


class DomainHistory(Model):
    """
    The domain’s history from public records: its registration, its first certificate and the web archive.
    """

    registration: Optional[DomainHistoryRegistration]
    """
    The domain registry’s record; null when it couldn’t be read.
    """
    first_certificate: Annotated[
        Optional[DomainHistoryFirstCertificate], Field(alias="firstCertificate")
    ]
    """
    Certificate Transparency: when a certificate for the domain was first issued.
    """
    archive: Optional[DomainHistoryArchive]
    """
    The Internet Archive’s record of the site.
    """


class DomainHistoryArchive(Model):
    """
    The Internet Archive’s record of the site.
    """

    first_capture: Annotated[Optional[datetime], Field(alias="firstCapture")]
    """
    The web archive’s first capture of the site.
    """
    first_capture_url: Annotated[Optional[str], Field(alias="firstCaptureUrl")]
    """
    A link to that capture, to look at.
    """
    capture_years: Annotated[list[int], Field(alias="captureYears")]
    """
    The years with at least one capture, oldest first.
    """
    source: str
    """
    The archive that answered.
    """
    checked_at: Annotated[datetime, Field(alias="checkedAt")]
    """
    When we asked.
    """


class DomainHistoryFirstCertificate(Model):
    """
    Certificate Transparency: when a certificate for the domain was first issued.
    """

    first_seen: Annotated[Optional[datetime], Field(alias="firstSeen")]
    """
    The earliest certificate’s start date; null when there were too many to read.
    """
    count: Optional[int]
    """
    How many certificates the logs list, when read in full.
    """
    source: str
    """
    The log search that answered.
    """
    checked_at: Annotated[datetime, Field(alias="checkedAt")]
    """
    When we asked.
    """


class DomainHistoryRegistration(Model):
    """
    The domain registry’s record; null when it couldn’t be read.
    """

    registered_at: Annotated[Optional[datetime], Field(alias="registeredAt")]
    """
    When the domain was registered; null when the registry doesn’t say.
    """
    last_changed_at: Annotated[Optional[datetime], Field(alias="lastChangedAt")]
    """
    When the record last changed.
    """
    registrar: Optional[str]
    """
    The registrar, as the registry names it.
    """
    record_for: Annotated[Optional[str], Field(alias="recordFor")]
    """
    The registered name, when the record is for a parent name.
    """
    source: str
    """
    The registry server that answered (RDAP or WHOIS).
    """
    checked_at: Annotated[datetime, Field(alias="checkedAt")]
    """
    When we asked.
    """


class Evidence(Model):
    """
    Where a finding was seen, with the exact text: the reason it is reported.
    """

    where: str
    """
    Where we saw it: "index.html, line 14", "response header", "address".
    """
    snippet: str
    """
    The element, header or excerpt as it appears.
    """
    match: str
    """
    The part of the snippet that matched.
    """
    masked: bool
    """
    True when email addresses and phone numbers in the snippet are masked.
    """


class Popularity(Model):
    """
    How popular the site is, from public ranked lists: a band and each list’s rank, never a visit count.
    """

    band: str
    """
    The best band any list gives the site ("Top 100K"), or "Outside top 1M".
    """
    best_rank: Annotated[Optional[int], Field(alias="bestRank")]
    """
    The best rank behind the band; null when no list ranks the site.
    """
    ranks: list[PopularityRank]
    """
    Each list we read, with the site’s rank on it.
    """


class PopularityRank(Model):
    list: str
    """
    The list’s name ("Chrome UX Report").
    """
    rank: Optional[int]
    """
    The rank, or null when the list doesn’t rank the site.
    """
    is_bucket: Annotated[bool, Field(alias="isBucket")]
    """
    True when the rank is the edge of a bucket, not an exact position.
    """
    ranked_as: Annotated[Optional[str], Field(alias="rankedAs")]
    """
    The parent name the list ranks, when not the site itself.
    """
    as_of: Annotated[str, Field(alias="asOf")]
    """
    When the list was produced, as it states it.
    """
    measures: str
    """
    What the list counts.
    """
    url: str
    """
    Where the list is published.
    """
    license: Optional[PopularityRankLicense]
    """
    The list’s license, when its terms ask for attribution: keep it when you republish.
    """


class PopularityRankLicense(Model):
    """
    The list’s license, when its terms ask for attribution: keep it when you republish.
    """

    name: str
    """
    The license’s name ("CC BY 3.0").
    """
    url: str
    """
    The license’s text.
    """


class Scan(ResponseModel):
    """
    A scan: queued, running, completed or failed. Poll it until `complete` is true.
    """

    id: str
    """
    The scan’s id.
    """
    domain: str
    """
    The domain scanned.
    """
    checks: list[str]
    """
    The checks its result holds: those asked that the scan answers.
    """
    status: str
    """
    Where it is: `queued`, `running`, `completed` or `failed`.
    """
    created_at: Annotated[datetime, Field(alias="createdAt")]
    """
    When it was asked for.
    """
    finished_at: Annotated[Optional[datetime], Field(alias="finishedAt")]
    """
    When it finished; null while it runs.
    """
    complete: bool
    """
    True once the scan failed, or completed with every slow source in.
    """
    failure: Optional[ScanFailure]
    """
    Why the scan couldn’t finish; null unless `status` is `failed`.
    """
    result: Optional[SiteResult]
    """
    The result once `status` is `completed`.
    """
    links: ScanLinks
    """
    Where to poll the scan, and where its result is shown.
    """


class ScanFailure(Model):
    """
    Why the scan couldn’t finish; null unless `status` is `failed`.
    """

    code: str
    """
    Why, as a stable code.
    """
    message: str
    """
    Why, in plain words.
    """


class ScanLinks(Model):
    """
    Where to poll the scan, and where its result is shown.
    """

    self: str
    """
    This scan, to poll: the address names the checks asked, so polling answers the same.
    """
    result: str
    """
    Its result page on our site.
    """


class Score(Model):
    """
    A score out of 100 for how established the site looks, from its parts; it says nothing about intent.
    """

    total: Optional[int]
    """
    Out of 100; null when too little could be read to score fairly.
    """
    band: str
    """
    The band the total falls in.
    """
    withheld: bool
    """
    True when too little could be read; `total` is null then.
    """
    version: str
    """
    The score formula’s version (/changelog).
    """
    parts: list[ScorePart]
    """
    The parts the total is made of, each with its points.
    """
    missing: list[str]
    """
    Inputs we couldn’t check; the rest is scaled to 100.
    """


class ScorePart(Model):
    key: str
    """
    The part, such as `transparency`, `trackRecord`, `popularity`, `security` or `consistency`.
    """
    label: str
    """
    The part’s name.
    """
    points: float
    """
    The points it earned.
    """
    max: float
    """
    The most it could earn from what we could check.
    """
    reasons: list[str]
    """
    Why points were given or withheld, one short phrase each.
    """
    checked: bool
    """
    False when none of its inputs could be checked.
    """


class SiteResult(ResponseModel):
    """
    One scan’s result for a site, holding the checks asked. A field is null when its check wasn’t asked, or the scan didn’t run it.
    """

    domain: str
    """
    The site’s domain, as we read it ("example.com").
    """
    checks: list[str]
    """
    The checks this result holds: those asked that the scan answered.
    """
    scan_id: Annotated[str, Field(alias="scanId")]
    """
    The scan that made this result.
    """
    scanned_at: Annotated[datetime, Field(alias="scannedAt")]
    """
    When the scan read the site.
    """
    complete: bool
    """
    False while slow sources (`pending`) are still being read.
    """
    pending: list[str]
    """
    The slow sources still being read, if any.
    """
    limited: Optional[SiteResultLimited]
    """
    Set when the page itself couldn’t be read; the result then comes from outside records.
    """
    final_url: Annotated[str, Field(alias="finalUrl")]
    """
    The address the scan ended at, after redirects.
    """
    result_url: Annotated[str, Field(alias="resultUrl")]
    """
    The result on our site, with every section and its evidence.
    """
    versions: SiteResultVersions
    """
    The signature list and score formula the result was made with (/changelog).
    """
    ai: Optional[AiTraces]
    """
    AI website builder traces (check `ai`).
    """
    readiness: Optional[AiReadiness]
    """
    How ready it is for AI tools, out of 100 (check `readiness`). A result made before we checked AI access takes it from a newer check when there is one (its `checkedAt` says when), and is null otherwise.
    """
    popularity: Optional[Popularity]
    """
    Popularity from public ranked lists (check `popularity`).
    """
    tech: Optional[Technology]
    """
    The technology it runs on (check `tech`).
    """
    dns: Optional[DnsRecords]
    """
    Its DNS records (check `dns`).
    """
    trust: Optional[TrustSignals]
    """
    Trust signals (check `trust`).
    """
    score: Optional[Score]
    """
    How established it looks, out of 100 (check `trust`, with the signals).
    """
    summary: Optional[SiteSummary]
    """
    What it is and who is behind it (check `summary`).
    """
    history: Optional[DomainHistory]
    """
    Its domain’s history (check `history`).
    """
    notes: list[str]
    """
    Limits of this scan, in plain words.
    """


class SiteResultLimited(Model):
    """
    Set when the page itself couldn’t be read; the result then comes from outside records.
    """

    reason: str
    """
    `blocked` (bot protection turned us away), `robots` (robots.txt keeps us out) or `private` (the site asks visitors to sign in).
    """
    message: str
    """
    What that means, in plain words.
    """


class SiteResultVersions(Model):
    """
    The signature list and score formula the result was made with (/changelog).
    """

    signatures: str
    """
    The signature list’s version.
    """
    score: str
    """
    The score formula’s version.
    """


class SiteSummary(Model):
    """
    What the site is: its own words, its kind, an automatic summary, who is behind it and its profiles.
    """

    title: Optional[str]
    """
    The page’s own title.
    """
    description: Optional[str]
    """
    The page’s own description.
    """
    site_name: Annotated[Optional[str], Field(alias="siteName")]
    """
    The name the site gives itself.
    """
    language: Optional[str]
    """
    The page’s language code ("en").
    """
    kind: Optional[SiteSummaryKind]
    """
    The kind of site we read it as (a shop, a blog, an app…); null when unclear.
    """
    summary: Optional[SiteSummarySummary]
    """
    An automatic summary whose quotes we checked against the page; null when there is none.
    """
    identity: Optional[SiteSummaryIdentity]
    """
    Who is behind the site, by independent sources.
    """
    wikidata: list[SiteSummaryWikidataItem]
    """
    The Wikidata items that name the domain as their official website.
    """
    social: list[SiteSummarySocialProfile]
    """
    The profiles the home page links.
    """
    ai_policy: Annotated[Optional[SiteSummaryAiPolicy], Field(alias="aiPolicy")]
    """
    What the site says about AI crawlers using its content.
    """
    llms_txt: Annotated[Optional[SiteSummaryLlmsTxt], Field(alias="llmsTxt")]
    """
    The site’s llms.txt (llmstxt.org), when it has one.
    """
    icon_url: Annotated[Optional[str], Field(alias="iconUrl")]
    """
    Our copy of the site’s icon.
    """


class SiteSummaryAiPolicy(Model):
    """
    What the site says about AI crawlers using its content.
    """

    training_blocked: Annotated[list[str], Field(alias="trainingBlocked")]
    """
    AI training crawlers robots.txt keeps out of the whole site.
    """
    training_partly: Annotated[list[str], Field(alias="trainingPartly")]
    """
    Training crawlers it gives rules for some paths only.
    """
    assistants_blocked: Annotated[list[str], Field(alias="assistantsBlocked")]
    """
    AI assistants (fetching pages for a person) it keeps out of the whole site.
    """
    everyone_blocked: Annotated[bool, Field(alias="everyoneBlocked")]
    """
    True when every crawler is kept out, AI ones included.
    """
    content_signal: Annotated[Optional[str], Field(alias="contentSignal")]
    """
    Its Content Signals line, as written ("search=yes, ai-train=no").
    """
    noai: bool
    """
    True when a `noai` robots tag or header is set.
    """


class SiteSummaryIdentity(Model):
    """
    Who is behind the site, by independent sources.
    """

    names: list[SiteSummaryIdentityName]
    """
    Each name a source gives for who is behind the site.
    """
    agreeing: list[str]
    """
    The sources whose names agree, when at least two do.
    """


class SiteSummaryIdentityName(Model):
    name: str
    """
    The name as the source gives it.
    """
    source: str
    """
    Where it comes from: `structured data`, `copyright line`, `Wikidata` or `certificate`.
    """


class SiteSummaryKind(Model):
    """
    The kind of site we read it as (a shop, a blog, an app…); null when unclear.
    """

    id: str
    """
    Our id for the kind ("shop").
    """
    label: str
    """
    Its name.
    """
    confidence: str
    """
    How sure the reading is.
    """


class SiteSummaryLlmsTxt(Model):
    """
    The site’s llms.txt (llmstxt.org), when it has one.
    """

    url: str
    """
    Where it is.
    """
    title: str
    """
    Its title.
    """
    summary: Optional[str]
    """
    The summary it writes for AI assistants.
    """


class SiteSummarySocialProfile(Model):
    network: str
    """
    The network ("github", "linkedin").
    """
    handle: str
    """
    The account as its address names it ("acme", "company/acme").
    """
    url: str
    """
    The profile’s address.
    """


class SiteSummarySummary(Model):
    """
    An automatic summary whose quotes we checked against the page; null when there is none.
    """

    text: str
    """
    Two or three sentences: what the site is and offers, as the page presents it.
    """
    category: str
    """
    What kind of site the model read it as.
    """
    offerings: list[str]
    """
    What it offers, in short phrases.
    """
    audience: Optional[str]
    """
    Who it is for, when the page says.
    """
    model: str
    """
    The model that wrote it.
    """
    written_at: Annotated[datetime, Field(alias="writtenAt")]
    """
    When it was written.
    """


class SiteSummaryWikidataItem(Model):
    id: str
    """
    The item’s id ("Q52").
    """
    label: str
    """
    Its label.
    """
    description: Optional[str]
    """
    Its short description.
    """
    types: list[str]
    """
    What it is an instance of, in English ("search engine").
    """
    inception_year: Annotated[Optional[int], Field(alias="inceptionYear")]
    """
    The year it was founded or launched.
    """
    url: str
    """
    Its page on Wikidata.
    """


class Technology(Model):
    """
    The technologies the site shows, each with its evidence, and the network announcing its address.
    """

    technologies: list[TechnologyItem]
    """
    Each technology the site shows, with its evidence.
    """
    network: Optional[TechnologyNetwork]
    """
    A network, never a place: many networks answer from everywhere.
    """


class TechnologyItem(Model):
    id: str
    """
    Our id for the technology.
    """
    name: str
    """
    Its name ("Next.js").
    """
    category: str
    """
    Such as "framework", "cms", "analytics", "hosting".
    """
    evidence: list[Evidence]
    """
    Where it was seen, with the exact line.
    """


class TechnologyNetwork(Model):
    """
    A network, never a place: many networks answer from everywhere.
    """

    asn: int
    """
    The autonomous system number, such as 13335.
    """
    name: str
    """
    The organisation announcing the address ("Cloudflare, Inc.").
    """
    prefix: Optional[str]
    """
    The routed block holding the address ("104.16.16.0/20").
    """
    source: str
    """
    Who answered.
    """
    checked_at: Annotated[datetime, Field(alias="checkedAt")]
    """
    When we asked.
    """


class TrustSignals(Model):
    """
    Signals about how established and reachable the site is. Signals, never a verdict.
    """

    checks: list[TrustSignalsCheck]
    """
    Each signal we looked for, found or not.
    """


class TrustSignalsCheck(Model):
    key: str
    """
    A stable key such as `privacyPolicy` or `domainAge`; new keys may appear.
    """
    label: str
    """
    The signal’s name ("Privacy policy").
    """
    state: str
    """
    `found`, `partial`, `none` (not found; absence is never an accusation), `info` (a fact) or `unknown` (couldn’t check).
    """
    value: str
    """
    What we found, in words.
    """
    kind: str
    """
    `measured` by us, `sourced` from a named source, or `interpreted` from what we read.
    """
    source: str
    """
    Where it came from: our scan or a named source.
    """
    evidence: list[Evidence]
    """
    Where it was seen, when the page or a record shows it.
    """
    pending: bool
    """
    True while a slow source is still being read.
    """


class Usage(ResponseModel):
    """
    The calling key’s account: its credits this month, and the key’s own.
    """

    period: UsagePeriod
    """
    The calendar month (UTC) the credits count in.
    """
    allowance: int
    """
    The account’s credits this month.
    """
    used: int
    """
    The credits the account used this month, all keys together.
    """
    remaining: int
    """
    The account’s credits left this month.
    """
    key: UsageKey
    """
    The key that made this call.
    """
    prices: UsagePrices
    """
    What a call costs, in credits: each check it asks, never more than every check at once.
    """
    rate_limit: Annotated[UsageRateLimit, Field(alias="rateLimit")]
    """
    How fast a key may call.
    """


class UsageKey(Model):
    """
    The key that made this call.
    """

    id: str
    """
    The key’s id.
    """
    name: str
    """
    The name you gave it.
    """
    monthly_credit_limit: Annotated[Optional[int], Field(alias="monthlyCreditLimit")]
    """
    Its own monthly limit; null when it has none.
    """
    used: int
    """
    The credits it used this month.
    """
    remaining: Optional[int]
    """
    What its own limit leaves; null without one.
    """


class UsagePeriod(Model):
    """
    The calendar month (UTC) the credits count in.
    """

    start: datetime
    """
    When the month began.
    """
    end: datetime
    """
    When it ends and the credits start again.
    """


class UsagePrices(Model):
    """
    What a call costs, in credits: each check it asks, never more than every check at once.
    """

    checks: dict[str, UsagePricesCheck]
    """
    What each check costs.
    """
    all_checks: Annotated[UsagePricesAllChecks, Field(alias="allChecks")]
    """
    The most a call costs: every check at once, asked when `checks` is left out.
    """


class UsagePricesAllChecks(Model):
    """
    The most a call costs: every check at once, asked when `checks` is left out.
    """

    stored: int
    """
    Every check from a stored result.
    """
    scan: int
    """
    Every check with a new scan.
    """


class UsagePricesCheck(Model):
    stored: int
    """
    From a stored result, or a scan already running.
    """
    scan: int
    """
    With a new scan.
    """


class UsageRateLimit(Model):
    """
    How fast a key may call.
    """

    requests: int
    """
    Calls a key may make in a period.
    """
    period_seconds: Annotated[int, Field(alias="periodSeconds")]
    """
    The period, in seconds.
    """


__all__ = [
    "AiReadiness",
    "AiReadinessCheck",
    "AiReadinessCheckFix",
    "AiReadinessCrawler",
    "AiReadinessLevel",
    "AiReadinessLevelState",
    "AiReadinessNext",
    "AiTraces",
    "AiTracesBuilder",
    "AiTracesPattern",
    "DnsRecords",
    "DnsRecordsNetwork",
    "DnsRecordsRecord",
    "DomainHistory",
    "DomainHistoryArchive",
    "DomainHistoryFirstCertificate",
    "DomainHistoryRegistration",
    "Evidence",
    "Popularity",
    "PopularityRank",
    "PopularityRankLicense",
    "Scan",
    "ScanFailure",
    "ScanLinks",
    "Score",
    "ScorePart",
    "SiteResult",
    "SiteResultLimited",
    "SiteResultVersions",
    "SiteSummary",
    "SiteSummaryAiPolicy",
    "SiteSummaryIdentity",
    "SiteSummaryIdentityName",
    "SiteSummaryKind",
    "SiteSummaryLlmsTxt",
    "SiteSummarySocialProfile",
    "SiteSummarySummary",
    "SiteSummaryWikidataItem",
    "Technology",
    "TechnologyItem",
    "TechnologyNetwork",
    "TrustSignals",
    "TrustSignalsCheck",
    "Usage",
    "UsageKey",
    "UsagePeriod",
    "UsagePrices",
    "UsagePricesAllChecks",
    "UsagePricesCheck",
    "UsageRateLimit",
]
