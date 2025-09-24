import re
from datetime import datetime
from typing import Dict, List, Optional
import hashlib

def normalize_firm_name(name: str) -> str:
    """Normalize firm names for consistent comparison"""
    if not name:
        return ""
    name = name.upper()
    name = re.sub(r'\s+(LLC|LTD|LIMITED|INC|INCORPORATED|CORP|CORPORATION|PLC)\.?$', '', name)
    name = re.sub(r'[^\w\s]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def normalize_date(date_str: Optional[str]) -> Optional[str]:
    """Convert various date formats to ISO format (YYYY-MM-DD)"""
    if not date_str:
        return None

    date_formats = [
        '%Y-%m-%d',
        '%d/%m/%Y',
        '%m/%d/%Y',
        '%d-%m-%Y',
        '%Y/%m/%d',
        '%d %B %Y',
        '%B %d, %Y',
        '%Y%m%d'
    ]

    for fmt in date_formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            continue
    return date_str

def generate_client_id(firm_name: str, client_name: str) -> str:
    """Generate consistent ID for firm-client pairs"""
    combined = f"{normalize_firm_name(firm_name)}:{normalize_firm_name(client_name)}"
    return hashlib.md5(combined.encode()).hexdigest()[:12]

def merge_client_records(records: List[Dict]) -> List[Dict]:
    """Merge duplicate client records from different sources"""
    merged = {}

    for record in records:
        key = generate_client_id(record.get('firm_name', ''), record.get('client_name', ''))

        if key not in merged:
            merged[key] = record
        else:
            # Merge dates - take earliest start and latest end
            existing = merged[key]

            start1 = normalize_date(existing.get('start_date'))
            start2 = normalize_date(record.get('start_date'))
            if start1 and start2:
                existing['start_date'] = min(start1, start2)
            elif start2:
                existing['start_date'] = start2

            end1 = normalize_date(existing.get('end_date'))
            end2 = normalize_date(record.get('end_date'))
            if end1 and end2:
                existing['end_date'] = max(end1, end2)
            elif end2:
                existing['end_date'] = end2

            # Merge IDs
            for id_field in ['client_id', 'client_registration_number', 'firm_registration_number']:
                if not existing.get(id_field) and record.get(id_field):
                    existing[id_field] = record[id_field]

    return list(merged.values())

def validate_record(record: Dict) -> bool:
    """Validate that a record has minimum required fields"""
    required = ['firm_name', 'client_name']
    return all(record.get(field) for field in required)