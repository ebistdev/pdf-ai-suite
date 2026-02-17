"""
Document Comparison Service.

Compare two documents and highlight differences:
- Text differences (added, removed, changed)
- Structural changes
- Table differences
"""

import difflib
from dataclasses import dataclass
from typing import Optional
from enum import Enum


class ChangeType(str, Enum):
    ADDED = "added"
    REMOVED = "removed"
    CHANGED = "changed"
    UNCHANGED = "unchanged"


@dataclass
class TextDiff:
    """A single difference in text."""
    type: ChangeType
    line_number: int
    content: str
    old_content: Optional[str] = None  # For changed lines


@dataclass
class ComparisonResult:
    """Result of comparing two documents."""
    doc1_name: str
    doc2_name: str
    similarity_percent: float
    total_lines_doc1: int
    total_lines_doc2: int
    added_lines: int
    removed_lines: int
    changed_lines: int
    diffs: list[TextDiff]
    summary: str


def compare_documents(
    text1: str,
    text2: str,
    doc1_name: str = "Document 1",
    doc2_name: str = "Document 2",
    context_lines: int = 3
) -> ComparisonResult:
    """
    Compare two documents and return differences.
    
    Args:
        text1: First document text
        text2: Second document text
        doc1_name: Name of first document
        doc2_name: Name of second document
        context_lines: Number of context lines around changes
        
    Returns:
        ComparisonResult with all differences
    """
    lines1 = text1.splitlines()
    lines2 = text2.splitlines()
    
    # Calculate similarity
    matcher = difflib.SequenceMatcher(None, text1, text2)
    similarity = matcher.ratio() * 100
    
    # Get detailed diffs
    differ = difflib.unified_diff(
        lines1, lines2,
        fromfile=doc1_name,
        tofile=doc2_name,
        lineterm='',
        n=context_lines
    )
    
    diffs = []
    added = 0
    removed = 0
    changed = 0
    line_num = 0
    
    for line in differ:
        if line.startswith('@@'):
            # Parse line numbers from unified diff header
            # Format: @@ -start,count +start,count @@
            try:
                parts = line.split(' ')
                line_num = int(parts[2].split(',')[0].replace('+', ''))
            except:
                pass
            continue
        elif line.startswith('---') or line.startswith('+++'):
            continue
        elif line.startswith('-'):
            diffs.append(TextDiff(
                type=ChangeType.REMOVED,
                line_number=line_num,
                content=line[1:]
            ))
            removed += 1
        elif line.startswith('+'):
            diffs.append(TextDiff(
                type=ChangeType.ADDED,
                line_number=line_num,
                content=line[1:]
            ))
            added += 1
            line_num += 1
        else:
            line_num += 1
    
    # Generate summary
    if similarity > 95:
        summary = "Documents are nearly identical."
    elif similarity > 80:
        summary = "Documents are similar with minor differences."
    elif similarity > 50:
        summary = "Documents have moderate differences."
    else:
        summary = "Documents are substantially different."
    
    summary += f" {added} lines added, {removed} lines removed."
    
    return ComparisonResult(
        doc1_name=doc1_name,
        doc2_name=doc2_name,
        similarity_percent=round(similarity, 2),
        total_lines_doc1=len(lines1),
        total_lines_doc2=len(lines2),
        added_lines=added,
        removed_lines=removed,
        changed_lines=changed,
        diffs=diffs,
        summary=summary
    )


def generate_html_diff(
    text1: str,
    text2: str,
    doc1_name: str = "Document 1",
    doc2_name: str = "Document 2"
) -> str:
    """
    Generate an HTML side-by-side diff view.
    """
    differ = difflib.HtmlDiff(wrapcolumn=80)
    html = differ.make_file(
        text1.splitlines(),
        text2.splitlines(),
        fromdesc=doc1_name,
        todesc=doc2_name,
        context=True,
        numlines=3
    )
    return html


def get_word_level_diff(text1: str, text2: str) -> list[dict]:
    """
    Get word-level differences for more granular comparison.
    """
    words1 = text1.split()
    words2 = text2.split()
    
    matcher = difflib.SequenceMatcher(None, words1, words2)
    
    changes = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            continue
        elif tag == 'replace':
            changes.append({
                "type": "changed",
                "old": ' '.join(words1[i1:i2]),
                "new": ' '.join(words2[j1:j2]),
                "position": i1
            })
        elif tag == 'delete':
            changes.append({
                "type": "removed",
                "content": ' '.join(words1[i1:i2]),
                "position": i1
            })
        elif tag == 'insert':
            changes.append({
                "type": "added",
                "content": ' '.join(words2[j1:j2]),
                "position": j1
            })
    
    return changes
