#!/usr/bin/env python3
"""Convert Pandoc Grid Tables to Pipe Tables in .qmd files.

Usage:
    python3.9 scripts/convert_grid_tables.py output/book/contents/core/hw_acceleration/hw_acceleration.qmd
    python3.9 scripts/convert_grid_tables.py --all   # Process all .qmd in output/book/contents/core/
    python3.9 scripts/convert_grid_tables.py --dry-run FILE  # Preview without writing
"""

import re
import sys
import os
import argparse
from pathlib import Path


def is_separator_line(line):
    """Check if line is a Grid Table separator (e.g., +---+---+ or +===+===+)."""
    stripped = line.strip()
    # Must start and end with +, only contain +, -, =, :
    if not stripped.startswith('+') or not stripped.endswith('+'):
        return False
    inner = stripped[1:-1]
    # Inner should only contain +, -, =, :
    if not re.match(r'^[+\-=:]+$', inner):
        return False
    # Must have at least one - or =
    if '-' not in stripped and '=' not in stripped:
        return False
    return True


def is_data_line(line):
    """Check if line is a Grid Table data line (starts and ends with |)."""
    stripped = line.strip()
    return stripped.startswith('|') and stripped.endswith('|')


def is_separator_type(line):
    """Return 'header' if === separator, 'normal' if --- separator, None otherwise."""
    stripped = line.strip()
    if not is_separator_line(stripped):
        return None
    if '=' in stripped:
        return 'header'
    if '-' in stripped:
        return 'normal'
    return None


def parse_cell_alignments(sep_line):
    """Parse alignment from separator line like +:===+:===+.

    Rules:
    - : before content = left-aligned (or just :)
    - : after content = right-aligned
    - : on both sides = center-aligned
    - no : = default (left)
    """
    stripped = sep_line.strip()
    # Remove outer +
    inner = stripped[1:-1]
    # Split by +
    cells = inner.split('+')

    alignments = []
    for cell in cells:
        cell = cell.strip()
        if not cell:
            # Empty separator cell
            alignments.append('---')
            continue

        left_colon = cell.startswith(':')
        right_colon = cell.endswith(':')

        if left_colon and right_colon:
            align = ':---:'
        elif right_colon:
            align = '---:'
        elif left_colon:
            align = ':---'
        else:
            align = '---'
        alignments.append(align)

    return alignments


def parse_cell_contents(data_line):
    """Parse cell contents from a data line like | cell1 | cell2 |."""
    stripped = data_line.strip()
    # Remove outer | characters
    if stripped.startswith('|'):
        stripped = stripped[1:]
    if stripped.endswith('|'):
        stripped = stripped[:-1]

    # Split by | to get cells
    cells = stripped.split('|')
    return [c.strip() for c in cells]


def find_grid_tables(lines):
    """Find all Grid Tables in the file and return their line ranges.

    Returns list of (start_idx, end_idx) tuples (inclusive, 0-based).
    """
    tables = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]
        stripped = line.strip()

        # Look for start of a grid table: separator line
        if is_separator_line(stripped):
            # Check if next line is a data line (table header)
            if i + 1 < n and is_data_line(lines[i + 1].strip()):
                table_start = i
                j = i + 1

                # Scan forward: expect alternating data/separator lines
                while j < n:
                    j_stripped = lines[j].strip()
                    if is_data_line(j_stripped):
                        j += 1
                    elif is_separator_line(j_stripped):
                        j += 1
                    else:
                        break

                # j is now past the last table line
                # Find the actual end (last separator line)
                table_end = j - 1

                # Verify this looks like a real table (at least 3 lines: sep, data, sep)
                if table_end - table_start >= 2:
                    tables.append((table_start, table_end))
                    i = j
                    continue
        i += 1

    return tables


def convert_grid_table(table_lines):
    """Convert a Grid Table (list of lines) to Pipe Table format.

    Returns list of lines for the Pipe Table.
    """
    if not table_lines:
        return table_lines

    # Parse the table structure
    # Find all separator lines and their types
    sep_positions = []
    data_positions = []

    for idx, line in enumerate(table_lines):
        stripped = line.strip()
        stype = is_separator_type(stripped)
        if stype is not None:
            sep_positions.append((idx, stype))
        elif is_data_line(stripped):
            data_positions.append(idx)

    if not sep_positions or not data_positions:
        return table_lines  # Can't convert, return as-is

    # Get alignments from the first separator (or header separator)
    alignments = None
    header_sep_idx = None
    for idx, stype in sep_positions:
        if stype == 'header':
            alignments = parse_cell_alignments(table_lines[idx].strip())
            header_sep_idx = idx
            break

    if alignments is None:
        # Use first separator
        alignments = parse_cell_alignments(table_lines[sep_positions[0][0]].strip())

    # Group rows: each "row" is between consecutive separators
    # Structure: sep0, data_lines_0, sep1, data_lines_1, sep2, ...
    # Where sep0 is top border, sep1 is header separator, sep2+ are row separators

    rows = []  # List of lists of line indices (each row's data lines)
    current_row = []

    for idx, line in enumerate(table_lines):
        stripped = line.strip()
        stype = is_separator_type(stripped)

        if stype is not None:
            if current_row:
                rows.append(current_row)
                current_row = []
        elif is_data_line(stripped):
            current_row.append(idx)

    if current_row:
        rows.append(current_row)

    if not rows:
        return table_lines

    # Determine num columns from first data line
    first_data = parse_cell_contents(table_lines[rows[0][0]])
    num_cols = len(first_data)

    # Ensure alignments match column count
    while len(alignments) < num_cols:
        alignments.append(':---')
    alignments = alignments[:num_cols]

    # Process each row and merge multi-line cells
    processed_rows = []
    for row_indices in rows:
        # Merge cells across multiple lines
        merged_cells = [''] * num_cols

        for line_idx in row_indices:
            cells = parse_cell_contents(table_lines[line_idx])

            for col_idx in range(min(len(cells), num_cols)):
                cell_content = cells[col_idx]
                if cell_content:
                    if merged_cells[col_idx]:
                        merged_cells[col_idx] += '<br>' + cell_content
                    else:
                        merged_cells[col_idx] = cell_content

        processed_rows.append(merged_cells)

    # Build pipe table
    pipe_lines = []

    # Check if first row is header (was separated by ===)
    has_header = any(stype == 'header' for _, stype in sep_positions)

    if has_header and len(processed_rows) >= 1:
        # First row is header
        header = processed_rows[0]
        pipe_lines.append('| ' + ' | '.join(header) + ' |')
        pipe_lines.append('|' + '|'.join(alignments) + '|')

        # Remaining rows
        for row in processed_rows[1:]:
            pipe_lines.append('| ' + ' | '.join(row) + ' |')
    else:
        # No header separator, just data rows
        pipe_lines.append('|' + '|'.join(alignments) + '|')
        for row in processed_rows:
            pipe_lines.append('| ' + ' | '.join(row) + ' |')

    return pipe_lines


def process_file(filepath, dry_run=False):
    """Process a single .qmd file, converting all Grid Tables to Pipe Tables."""
    filepath = Path(filepath)

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Find all grid tables
    tables = find_grid_tables(lines)

    if not tables:
        print(f"  No Grid Tables found in {filepath.name}")
        return 0

    print(f"  Found {len(tables)} Grid Table(s) in {filepath.name}")

    # Process tables in reverse order to maintain line indices
    modified = False
    for start, end in reversed(tables):
        table_lines = [l.rstrip('\n') for l in lines[start:end + 1]]
        pipe_lines = convert_grid_table(table_lines)

        if pipe_lines != table_lines:
            print(f"    Table at lines {start + 1}-{end + 1}: {len(table_lines)} lines -> {len(pipe_lines)} lines")
            # Replace in file lines
            new_lines = [l + '\n' for l in pipe_lines]
            lines[start:end + 1] = new_lines
            modified = True

    if modified and not dry_run:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        print(f"  Wrote {filepath.name}")

    # Count remaining +--- lines
    remaining = sum(1 for l in lines if '+---' in l or '+===' in l)
    return remaining


def main():
    parser = argparse.ArgumentParser(description='Convert Grid Tables to Pipe Tables')
    parser.add_argument('files', nargs='*', help='Files to process')
    parser.add_argument('--all', action='store_true', help='Process all .qmd in core/')
    parser.add_argument('--dry-run', action='store_true', help='Preview without writing')
    args = parser.parse_args()

    if args.all:
        core_dir = Path('output/book/contents/core')
        files = sorted(core_dir.rglob('*.qmd'))
    elif args.files:
        files = [Path(f) for f in args.files]
    else:
        parser.print_help()
        return

    total_remaining = 0
    for filepath in files:
        print(f"\nProcessing: {filepath}")
        remaining = process_file(filepath, dry_run=args.dry_run)
        total_remaining += remaining

    print(f"\n{'=' * 50}")
    print(f"Total remaining +---/+= lines: {total_remaining}")


if __name__ == '__main__':
    main()
