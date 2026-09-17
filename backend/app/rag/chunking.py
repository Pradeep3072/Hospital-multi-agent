import re
from typing import List, Dict, Any


def chunk_document(content: str, filename: str, max_chunk_size: int = 650, overlap: int = 50) -> List[Dict[str, Any]]:
    """
    Split markdown, PDF, or text into semantic chunks based on:
    - Markdown section headers (#, ##, ###)
    - Numbered section titles (e.g. '1. Hospital Overview')
    - Paragraph and multi-line boundary splitting with preserved header context.
    """
    # Split on markdown headings or numbered sections
    split_pattern = r'\n(?=(?:#{1,4}\s+|\d{1,2}\.\s+[A-Z]))'
    sections = re.split(split_pattern, content)
    chunks = []
    chunk_index = 0

    for sec in sections:
        sec = sec.strip()
        if not sec:
            continue

        # Extract title if present
        header_match = re.match(r'^(?:#{1,4}\s+|\d{1,2}\.\s+)([^\n]+)', sec)
        first_line = sec.split('\n')[0].strip()
        header = header_match.group(0).strip() if header_match else first_line[:60]

        # Clean section lines: filter standalone markdown divider dashes
        clean_lines = [line.strip() for line in sec.split('\n') if line.strip() and line.strip() != '---']
        if not clean_lines:
            continue

        clean_text = '\n'.join(clean_lines)

        # If section is small enough, keep as single chunk
        if len(clean_text) <= max_chunk_size:
            chunk_index += 1
            chunks.append({
                "chunk_id": f"{filename}_{chunk_index}",
                "source": filename,
                "header": header,
                "content": clean_text
            })
        else:
            # Paragraph level split
            paragraphs = sec.split("\n\n")
            if len(paragraphs) <= 1:
                paragraphs = clean_lines

            current_lines = [header] if not clean_lines[0].startswith(header) else []
            current_len = sum(len(l) for l in current_lines)

            for p in paragraphs:
                p_str = p.strip()
                if not p_str or p_str == '---' or p_str == header:
                    continue

                if current_len + len(p_str) <= max_chunk_size:
                    current_lines.append(p_str)
                    current_len += len(p_str) + 1
                else:
                    if len(current_lines) > 1 or (len(current_lines) == 1 and current_lines[0] != header):
                        chunk_index += 1
                        chunks.append({
                            "chunk_id": f"{filename}_{chunk_index}",
                            "source": filename,
                            "header": header,
                            "content": "\n".join(current_lines)
                        })
                    current_lines = [header, p_str]
                    current_len = len(header) + len(p_str) + 1

            if len(current_lines) > 1 or (len(current_lines) == 1 and current_lines[0] != header):
                chunk_index += 1
                chunks.append({
                    "chunk_id": f"{filename}_{chunk_index}",
                    "source": filename,
                    "header": header,
                    "content": "\n".join(current_lines)
                })

    return chunks


def chunk_markdown_document(content: str, filename: str, max_chunk_size: int = 650, overlap: int = 50) -> List[Dict[str, Any]]:
    """
    Backwards-compatible alias for chunk_document.
    """
    return chunk_document(content, filename, max_chunk_size, overlap)
