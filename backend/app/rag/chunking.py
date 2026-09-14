import re
from typing import List, Dict, Any


def chunk_markdown_document(content: str, filename: str, max_chunk_size: int = 500, overlap: int = 50) -> List[Dict[str, Any]]:
    """
    Split markdown text into semantic chunks based on sections (# and ##)
    and paragraph boundaries.
    """
    sections = re.split(r'\n(?=#{1,3}\s)', content)
    chunks = []
    chunk_index = 0

    for sec in sections:
        sec = sec.strip()
        if not sec:
            continue
        
        # Extract title if present
        header_match = re.match(r'^(#{1,3}\s[^\n]+)', sec)
        header = header_match.group(1) if header_match else "General"
        
        # If section is small enough, keep as single chunk
        if len(sec) <= max_chunk_size:
            chunk_index += 1
            chunks.append({
                "chunk_id": f"{filename}_{chunk_index}",
                "source": filename,
                "header": header,
                "content": sec
            })
        else:
            # Paragraph level split
            paragraphs = sec.split("\n\n")
            current_text = header + "\n"
            for p in paragraphs:
                p = p.strip()
                if not p:
                    continue
                if len(current_text) + len(p) <= max_chunk_size:
                    current_text += "\n" + p
                else:
                    if current_text.strip() != header:
                        chunk_index += 1
                        chunks.append({
                            "chunk_id": f"{filename}_{chunk_index}",
                            "source": filename,
                            "header": header,
                            "content": current_text.strip()
                        })
                    current_text = f"{header}\n{p}"
            if current_text.strip() != header:
                chunk_index += 1
                chunks.append({
                    "chunk_id": f"{filename}_{chunk_index}",
                    "source": filename,
                    "header": header,
                    "content": current_text.strip()
                })
                
    return chunks
