import csv
import io
from typing import Dict, Any, Tuple, Optional, List
from pyspark import RDD

def parse_csv_line(line: str) -> Optional[List[str]]:
    try:
        reader = csv.reader(io.StringIO(line))
        for row in reader:
            return [col.strip() for col in row]
    except Exception:
        return None
    return None

class RddDataCleaner:
    """
    Cleans raw RDD lines using distributed transformations:
    filter(), map(), distinct(), and validation checks.
    """
    @staticmethod
    def extract_header_and_data(lines_rdd: RDD) -> Tuple[List[str], RDD]:
        """
        Extracts the first line as CSV header and filters it out from the data RDD.
        """
        first_line = lines_rdd.first()
        header = [c.strip() for c in next(csv.reader([first_line]))]
        
        # Filter out header line and empty lines using filter()
        data_lines = lines_rdd.filter(lambda l: l.strip() != "" and l != first_line)
        return header, data_lines

    @staticmethod
    def clean_and_parse_csv(
        data_lines_rdd: RDD,
        header: List[str],
        expected_col_count: int
    ) -> Tuple[RDD, int, int]:
        """
        Parses rows, strips whitespace, removes duplicates via distinct(),
        and validates required column counts.
        """
        total_input_count = data_lines_rdd.count()

        # Step 1: Deduplicate identical lines using distinct()
        deduped_lines = data_lines_rdd.distinct()

        # Step 2: Parse into row lists using map()
        parsed_rows = deduped_lines.map(lambda l: next(csv.reader([l])) if l.strip() else None)

        # Step 3: Filter invalid rows using filter()
        valid_rows = parsed_rows.filter(
            lambda r: r is not None and len(r) == expected_col_count and all(c != "" for c in r[:3])
        )

        valid_count = valid_rows.count()
        rejected_count = total_input_count - valid_count

        # Step 4: Map into dictionary records using map()
        records_rdd = valid_rows.map(lambda row: dict(zip(header, row)))

        return records_rdd, valid_count, rejected_count
