"""Parse acebidx.com HTML pages to extract tender data."""

import re
import logging
from dataclasses import dataclass, field, asdict

from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

# Fields we want to extract from detail pages
DETAIL_FIELDS = [
    "機關代碼", "機關名稱", "單位名稱", "機關地址",
    "標案案號", "標案名稱", "標的分類",
    "採購金額級距", "預算金額", "預算金額是否公開",
    "招標方式", "決標方式",
    "公告日", "截止投標", "開標時間",
    "履約地點", "履約期限",
    "是否須繳納押標金", "是否須繳納履約保證金",
]


@dataclass
class TenderSummary:
    tender_id: str
    title: str
    org_name: str
    announce_date: str
    url: str


@dataclass
class TenderDetail:
    tender_id: str = ""
    org_code: str = ""
    org_name: str = ""
    unit_name: str = ""
    org_address: str = ""
    case_number: str = ""
    tender_name: str = ""
    category: str = ""
    budget_level: str = ""
    budget: int | None = None
    budget_public: str = ""
    bid_method: str = ""
    award_method: str = ""
    announce_date: str = ""
    deadline: str = ""
    open_time: str = ""
    location: str = ""
    duration: str = ""
    deposit_required: str = ""
    bond_required: str = ""
    url: str = ""
    crawled_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def parse_listing_page(html: str) -> tuple[list[TenderSummary], str | None]:
    """Parse a keyword listing page using BeautifulSoup.

    Returns:
        (list of TenderSummary, next_page_path or None)
    """
    soup = BeautifulSoup(html, 'html.parser')
    tenders = []
    seen_ids = set()

    # Find all <li> elements with tender links
    for li in soup.find_all('li', attrs={'value': True}):
        link = li.find('a', href=re.compile(r'/docs/tender/id/'))
        if not link:
            continue

        href = link.get('href', '')
        # Extract UUID from href
        id_match = re.search(r'/docs/tender/id/([a-f0-9-]+)', href)
        if not id_match:
            continue

        tender_id = id_match.group(1)
        if tender_id in seen_ids:
            continue
        seen_ids.add(tender_id)

        # Title is in <span class="text-xl ...">
        title_span = link.find('span', class_=re.compile(r'text-xl'))
        title = title_span.get_text(strip=True) if title_span else "(unknown)"

        # Org and date are in the <div> spans
        org_name = ""
        announce_date = ""
        info_div = link.find('div', class_=re.compile(r'flex'))
        if info_div:
            spans = info_div.find_all('span')
            # Typically: [title_span_already_captured, org_span, date_span]
            # Filter for base-sized text spans
            text_spans = [s for s in spans if s.get_text(strip=True) and 'text-xl' not in (s.get('class') or [])]
            for s in text_spans:
                text = s.get_text(strip=True)
                if re.match(r'\d+月\d+日', text) or '公告' in text:
                    announce_date = text
                elif len(text) > 2 and not text[0].isdigit():
                    org_name = text

        tenders.append(TenderSummary(
            tender_id=tender_id,
            title=title,
            org_name=org_name,
            announce_date=announce_date,
            url=href,
        ))

    # Find next page link
    next_page = None
    for a in soup.find_all('a', href=True):
        if '下一頁' in a.get_text():
            next_page = a['href']
            break

    log.info(f"列表頁解析: {len(tenders)} 筆標案, 下一頁: {next_page is not None}")
    return tenders, next_page


def parse_detail_page(html: str, tender_id: str) -> TenderDetail:
    """Parse a tender detail page from RSC flight data.

    The page uses Next.js RSC format with MUI Grid components.
    Labels are in __html attributes, values in children.
    """
    detail = TenderDetail(tender_id=tender_id)

    # Extract all label-value pairs from MUI Grid structure
    fields = _extract_rsc_fields(html)

    # Map to TenderDetail fields
    detail.org_code = fields.get("機關代碼", "")
    detail.org_name = fields.get("機關名稱", "") or fields.get("單位名稱", "")
    detail.unit_name = fields.get("單位名稱", "")
    detail.org_address = fields.get("機關地址", "")
    detail.case_number = fields.get("標案案號", "")
    detail.tender_name = fields.get("標案名稱", "")
    detail.category = fields.get("標的分類", "")
    detail.budget_level = fields.get("採購金額級距", "")
    detail.budget = _parse_budget(fields.get("預算金額", ""))
    detail.budget_public = fields.get("預算金額是否公開", "")
    detail.bid_method = fields.get("招標方式", "")
    detail.award_method = fields.get("決標方式", "")
    detail.announce_date = fields.get("公告日", "")
    detail.deadline = fields.get("截止投標", "")
    detail.open_time = fields.get("開標時間", "")
    detail.location = fields.get("履約地點", "")
    detail.duration = fields.get("履約期限", "")
    detail.deposit_required = fields.get("是否須繳納押標金", "")
    detail.bond_required = fields.get("是否須繳納履約保證金", "")

    # Fallback: try to get title from page title tag if not found in fields
    if not detail.tender_name:
        title_match = re.search(r'<title>(.*?)</title>', html)
        if title_match:
            raw_title = title_match.group(1)
            # Title format: "NAME 招標公告 | 案號：NUMBER | ..."
            parts = raw_title.split(" 招標公告")
            if parts:
                detail.tender_name = parts[0].strip()

    # Fallback for case number from title
    if not detail.case_number:
        case_match = re.search(r'案號：([A-Za-z0-9]+)', html)
        if case_match:
            detail.case_number = case_match.group(1)

    return detail


def _extract_rsc_fields(html: str) -> dict[str, str]:
    """Extract label-value pairs from Next.js RSC flight data."""
    fields = {}

    # Find all labels using __html pattern
    label_pattern = re.compile(r'\\"__html\\":\\"([^\\"]{2,30})\\"')
    label_matches = list(label_pattern.finditer(html))

    for match in label_matches:
        label = match.group(1)

        # Skip non-field content
        if label.startswith('{') or label.startswith('body') or label.startswith('http'):
            continue

        # Only extract fields we care about
        if label not in DETAIL_FIELDS:
            continue

        pos = match.start()
        region = html[pos:pos + 1500]

        # Find value in the xs:9 grid item
        xs9_idx = region.find('\\"xs\\":9')
        if xs9_idx < 0:
            continue

        after_xs9 = region[xs9_idx:xs9_idx + 800]

        # Try multiple value extraction patterns
        value = _extract_value_from_region(after_xs9)
        if value:
            fields[label] = value
        elif '會員專用' in after_xs9[:500]:
            fields[label] = "(會員專用)"

    return fields


def _extract_value_from_region(region: str) -> str | None:
    """Extract the text value from a RSC region after xs:9."""
    # Pattern 1: Array children with plain text
    # \"children\":[\"VALUE\" (not starting with $)
    m = re.search(r'\\"children\\":\[\\"([^$\\\\"][^\\"]*)\\"', region)
    if m:
        return m.group(1)

    # Pattern 2: String children (not array)
    # \"children\":\"VALUE\"
    m = re.search(r'\\"children\\":\\"([^$\\\\"][^\\"]{2,})\\"', region)
    if m:
        val = m.group(1)
        if not val.startswith('{') and not val.startswith('$'):
            return val

    # Pattern 3: Nested span with style + children string
    # \"style\":{...},\"children\":\"VALUE\"
    m = re.search(r'\\"style\\":\{[^}]*\},\\"children\\":\\"([^\\"]+)\\"', region)
    if m:
        return m.group(1)

    # Pattern 4: Nested span children as string
    # \"children\":[\"$\",\"span\",null,{...\"children\":\"VALUE\"
    m = re.search(r'span.*?\\"children\\":\\"([^\\"\$][^\\"]{2,})\\"', region)
    if m:
        return m.group(1)

    # Pattern 5: Deep nested - \"children\":\"$\",\"span\"...\"children\":\"VALUE\"
    # For date fields with color styling
    vals = re.findall(r'\\"children\\":\\"([^\\"\$][^\\"]+)\\"', region)
    for v in vals:
        # Return first non-trivial value
        if len(v) > 1 and not v.startswith('{') and not v.startswith('$') and v not in ('null', 'true', 'false'):
            return v

    return None


def _parse_budget(budget_str: str) -> int | None:
    """Parse budget string to integer. Returns None if unparseable."""
    if not budget_str or budget_str == "(會員專用)":
        return None

    # Remove common suffixes and prefixes
    cleaned = budget_str.strip()
    cleaned = cleaned.replace("底價分析", "")
    cleaned = cleaned.replace("NT$", "")
    cleaned = cleaned.replace("元", "")
    cleaned = cleaned.replace(",", "")
    cleaned = cleaned.replace(" ", "")

    try:
        return int(cleaned)
    except ValueError:
        log.debug(f"無法解析預算金額: {budget_str}")
        return None
