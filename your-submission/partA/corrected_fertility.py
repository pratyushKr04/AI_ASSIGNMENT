#!/usr/bin/env python3
"""
corrected_fertility.py -- Corrected tokenizer fertility analysis

Uses:
  - Parallel corpus (4 languages)
  - Multiple tokenizers (gpt2 + Indic-aware)
  - Multiple denominators (words, chars, bytes, parallel-sentence)
  - Correct aggregation (ratio of totals, not mean of ratios)

Usage:
    python corrected_fertility.py

Author: Corrected version for the assignment
"""

import os
import sys
import unicodedata

# Fix Windows console encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

CORPUS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "corpus")


def read_lines(path):
    lines = []
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            line = unicodedata.normalize("NFC", line)
            lines.append(line)
    return lines


def load_tiktoken(spec="gpt2"):
    """Load a tiktoken tokenizer."""
    import tiktoken
    enc = tiktoken.get_encoding(spec)
    return enc.encode, f"tiktoken:{spec}"


def load_hf_tokenizer(repo_id):
    """Load a HuggingFace tokenizer."""
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(repo_id)
    return lambda s: tok.encode(s, add_special_tokens=False), f"hf:{repo_id}"


def analyze_corrected(lines, encode):
    """
    Corrected analysis: ratio of totals (not mean of ratios),
    proper whitespace splitting, multiple denominators.
    """
    total_tokens = 0
    total_words = 0
    total_chars = 0
    total_bytes = 0
    total_graphemes = 0

    for line in lines:
        tokens = encode(line)
        words = line.split()  # proper split
        total_tokens += len(tokens)
        total_words += len(words)
        total_chars += len(line)
        total_bytes += len(line.encode("utf-8"))
        # Count grapheme clusters (user-perceived characters)
        # Simple approximation: count non-combining characters
        total_graphemes += sum(1 for ch in line if unicodedata.category(ch) not in ('Mn', 'Mc', 'Me'))

    return {
        "total_tokens": total_tokens,
        "total_words": total_words,
        "total_chars": total_chars,
        "total_bytes": total_bytes,
        "total_graphemes": total_graphemes,
        "tok_per_word": total_tokens / total_words if total_words else 0,
        "tok_per_char": total_tokens / total_chars if total_chars else 0,
        "tok_per_byte": total_tokens / total_bytes if total_bytes else 0,
        "tok_per_grapheme": total_tokens / total_graphemes if total_graphemes else 0,
        "tok_per_sentence": total_tokens / len(lines) if lines else 0,
    }


def main():
    # Load corpus
    langs = ["eng", "hin", "tam", "kan"]
    lang_names = {"eng": "English", "hin": "Hindi", "tam": "Tamil", "kan": "Kannada"}
    corpus = {}

    for lang in langs:
        path = os.path.join(CORPUS_DIR, f"{lang}.txt")
        if not os.path.exists(path):
            print(f"ERROR: Corpus file not found: {path}")
            print("Run build_corpus.py first.")
            sys.exit(1)
        corpus[lang] = read_lines(path)
        print(f"Loaded {lang}: {len(corpus[lang])} sentences")

    print()

    # Load tokenizers
    tokenizers = []

    # Tokenizer 1: GPT-2 (non-Indic-aware baseline)
    try:
        enc, name = load_tiktoken("gpt2")
        tokenizers.append((name, enc))
        print(f"Loaded tokenizer: {name}")
    except Exception as e:
        print(f"WARNING: Could not load gpt2: {e}")

    # Tokenizer 2: cl100k_base (GPT-4 tokenizer, somewhat better)
    try:
        enc, name = load_tiktoken("cl100k_base")
        tokenizers.append((name, enc))
        print(f"Loaded tokenizer: {name}")
    except Exception as e:
        print(f"WARNING: Could not load cl100k_base: {e}")

    # Tokenizer 3: Try an Indic-aware HF tokenizer
    hf_candidates = [
        "ai4bharat/IndicBERTv2-MLM-Sam-TLM",
        "google/gemma-2b",
        "meta-llama/Llama-2-7b-hf",
    ]
    for repo in hf_candidates:
        try:
            enc, name = load_hf_tokenizer(repo)
            tokenizers.append((name, enc))
            print(f"Loaded tokenizer: {name}")
            break
        except Exception as e:
            print(f"  Could not load {repo}: {e}")
            continue

    if not tokenizers:
        print("ERROR: No tokenizers available!")
        sys.exit(1)

    print()

    # === Analysis per tokenizer ===
    for tok_name, encode in tokenizers:
        print("=" * 80)
        print(f"TOKENIZER: {tok_name}")
        print("=" * 80)

        results = {}
        for lang in langs:
            results[lang] = analyze_corrected(corpus[lang], encode)

        # Table 1: Absolute metrics
        print(f"\n  {'lang':<6} {'total_tok':>10} {'tok/word':>10} {'tok/char':>10} "
              f"{'tok/byte':>10} {'tok/sent':>10} {'tok/graph':>10}")
        print("  " + "-" * 68)
        for lang in langs:
            r = results[lang]
            print(f"  {lang:<6} {r['total_tokens']:>10d} {r['tok_per_word']:>10.3f} "
                  f"{r['tok_per_char']:>10.4f} {r['tok_per_byte']:>10.4f} "
                  f"{r['tok_per_sentence']:>10.1f} {r['tok_per_grapheme']:>10.4f}")

        # Table 2: Ratios vs English
        print(f"\n  Ratios vs English:")
        print(f"  {'lang':<6} {'tok/word':>10} {'tok/char':>10} {'tok/byte':>10} "
              f"{'tok/sent':>10} {'tok/graph':>10}")
        print("  " + "-" * 56)
        base = results["eng"]
        for lang in langs:
            r = results[lang]
            rw = r['tok_per_word'] / base['tok_per_word'] if base['tok_per_word'] else 0
            rc = r['tok_per_char'] / base['tok_per_char'] if base['tok_per_char'] else 0
            rb = r['tok_per_byte'] / base['tok_per_byte'] if base['tok_per_byte'] else 0
            rs = r['tok_per_sentence'] / base['tok_per_sentence'] if base['tok_per_sentence'] else 0
            rg = r['tok_per_grapheme'] / base['tok_per_grapheme'] if base['tok_per_grapheme'] else 0
            print(f"  {lang:<6} {rw:>10.2f}x {rc:>10.2f}x {rb:>10.2f}x "
                  f"{rs:>10.2f}x {rg:>10.2f}x")

        print()

    # === Cost recommendation ===
    print("=" * 80)
    print("RECOMMENDATION: Best denominator for cost/routing decisions")
    print("=" * 80)
    print("""
  DENOMINATOR COMPARISON (using first tokenizer as reference):

  tok/word:     UNFAIR. Word boundaries differ across languages. Hindi has
                fewer but longer words than English. Dravidian languages
                have even longer agglutinative words. Grossly overstates
                the cost gap.

  tok/char:     BETTER but still unfair. Unicode characters have different
                byte-widths: English=1 byte/char, Hindi~2.7 bytes/char,
                Tamil~2.8 bytes/char. So tok/char overstates the gap
                because it treats a 3-byte character the same as a 1-byte one.

  tok/byte:     FAIREST for cost estimation. Bytes approximate the actual
                data volume being transmitted. A user sending N bytes of
                Hindi incurs tok/byte * N tokens, regardless of script.
                This is the right metric for API billing and capacity planning.

  tok/sentence: BEST for measuring "cost per user intent". If a user asks
                one question, how many tokens does the answer cost? This
                directly measures the serving cost per interaction.
                However, it requires parallel corpora.

  PRODUCTION RECOMMENDATION:
  - Use tok/byte for real-time cost monitoring (no parallel data needed).
  - Use tok/sentence on periodic benchmark sets for capacity planning.
  - Alert when tok/byte ratio exceeds a threshold (e.g., >4x for any language).
""")


if __name__ == "__main__":
    main()
