"""PDF bank statement parser — extracts candidate transactions via regex."""
import re
from datetime import datetime

try:
    import pdfplumber
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# Matches common date formats: 01/31, 01/31/24, 01/31/2024, 01-31-2024
_DATE_RE = re.compile(r'\b(\d{1,2}[/\-]\d{1,2}(?:[/\-]\d{2,4})?)\b')
# Matches dollar amounts with optional leading $ and commas
_AMOUNT_RE = re.compile(r'\$?\s*([\d]{1,3}(?:,\d{3})*\.\d{2})')


def _parse_amount(s: str) -> float:
    return float(s.replace(",", ""))


def extract_transactions(pdf_path: str) -> list[dict]:
    """Return a list of candidate transactions parsed from a PDF statement.

    Each entry has: raw_date, description, amount, raw_line.
    """
    if not PDF_AVAILABLE:
        return []

    results = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for line in text.splitlines():
                line = line.strip()
                if len(line) < 5:
                    continue

                date_m = _DATE_RE.search(line)
                if not date_m:
                    continue

                amounts = _AMOUNT_RE.findall(line)
                if not amounts:
                    continue

                # Use first amount (transaction amount, not running balance)
                try:
                    amount = _parse_amount(amounts[0])
                except ValueError:
                    continue

                if amount <= 0:
                    continue

                # Description = text between end of date and first amount
                first_amount_m = _AMOUNT_RE.search(line)
                desc_start = date_m.end()
                desc_end = first_amount_m.start() if first_amount_m else len(line)
                description = line[desc_start:desc_end].strip(" -")

                if not description:
                    description = line[: date_m.start()].strip() or "—"

                results.append({
                    "raw_date": date_m.group(1),
                    "description": description,
                    "amount": amount,
                    "raw_line": line,
                })

    return results


def normalize_date(raw: str) -> str:
    """Convert common statement date strings to YYYY-MM-DD, falling back to today."""
    today = datetime.today()
    for fmt in ("%m/%d/%Y", "%m-%d-%Y", "%m/%d/%y", "%m-%d-%y", "%m/%d", "%m-%d"):
        try:
            dt = datetime.strptime(raw, fmt)
            # Two-digit-year or no-year: fill in current year
            if dt.year == 1900 or fmt in ("%m/%d", "%m-%d"):
                dt = dt.replace(year=today.year)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return today.strftime("%Y-%m-%d")
