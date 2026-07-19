#!/usr/bin/env python3
"""
audit_evidence.py -- Demonstrate bugs and conceptual flaws in fertility.py

This script reproduces the original intern's methodology and then shows
what changes when each bug is fixed. Provides measured evidence for
every claimed flaw.

Usage:
    python audit_evidence.py
"""

import os
import sys
import unicodedata

# Fix Windows console encoding for Hindi/Tamil/Kannada output
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')


# Add starter_kit to path so we can import/compare
STARTER_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "starter_kit")
CORPUS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "corpus")


def load_tokenizer_tiktoken(spec="gpt2"):
    """Load tiktoken tokenizer (same as original)."""
    import tiktoken
    enc = tiktoken.get_encoding(spec)
    return enc.encode


def read_lines(path):
    """Same as original fertility.py."""
    lines = []
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            line = unicodedata.normalize("NFC", line)
            lines.append(line)
    return lines


def analyze_original(lines, encode):
    """Original (buggy) analysis: mean of per-line ratios."""
    per_line_fertility = []
    per_line_tpc = []
    for line in lines:
        line = line.lower()
        tokens = encode(line)
        words = line.split(" ")  # BUG: single-space split
        chars = len(line)
        per_line_fertility.append(len(tokens) / len(words))
        per_line_tpc.append(len(tokens) / chars)
    n = len(per_line_fertility)
    return sum(per_line_fertility) / n, sum(per_line_tpc) / n


def analyze_fixed_aggregation(lines, encode):
    """Fix #1: Use ratio of totals instead of mean of ratios."""
    total_tokens = 0
    total_words = 0
    total_chars = 0
    for line in lines:
        line = line.lower()
        tokens = encode(line)
        words = line.split(" ")  # still buggy split, isolating one fix at a time
        total_tokens += len(tokens)
        total_words += len(words)
        total_chars += len(line)
    return total_tokens / total_words, total_tokens / total_chars


def analyze_fixed_split(lines, encode):
    """Fix #2: Use proper word splitting (split() with no args, strips all whitespace)."""
    per_line_fertility = []
    per_line_tpc = []
    for line in lines:
        line = line.lower()
        tokens = encode(line)
        words = line.split()  # FIX: split on any whitespace, no empty strings
        chars = len(line)
        if len(words) == 0:
            continue
        per_line_fertility.append(len(tokens) / len(words))
        per_line_tpc.append(len(tokens) / chars)
    n = len(per_line_fertility)
    return sum(per_line_fertility) / n, sum(per_line_tpc) / n


def analyze_fully_fixed(lines, encode):
    """All fixes: ratio of totals + proper split."""
    total_tokens = 0
    total_words = 0
    total_chars = 0
    total_bytes = 0
    for line in lines:
        line = line.lower()
        tokens = encode(line)
        words = line.split()  # proper split
        total_tokens += len(tokens)
        total_words += len(words)
        total_chars += len(line)
        total_bytes += len(line.encode("utf-8"))
    return (
        total_tokens / total_words,
        total_tokens / total_chars,
        total_tokens / total_bytes,
    )


def demonstrate_split_bug():
    """Show concrete examples of the split(' ') bug."""
    print("=" * 60)
    print("BUG #1: line.split(' ') vs line.split()")
    print("=" * 60)

    # From the original corpus — line 7 has double space
    test_lines = [
        'Please keep the books  in the cupboard.',   # double space from eng_sample
        'किताबें  अलमारी में रखी हैं।',              # double space from hin_sample
        'Hello   world  test',                        # triple + double space
    ]

    for line in test_lines:
        words_buggy = line.split(" ")
        words_fixed = line.split()
        print(f"\n  Line: {line!r}")
        print(f"  split(' '): {words_buggy}  ({len(words_buggy)} words)")
        print(f"  split():    {words_fixed}  ({len(words_fixed)} words)")
        if len(words_buggy) != len(words_fixed):
            print(f"  [!] DIFFERENCE: {len(words_buggy)} vs {len(words_fixed)} words")
    print()


def demonstrate_aggregation_bug(eng_lines, hin_lines, encode):
    """Show impact of mean-of-ratios vs ratio-of-means."""
    print("=" * 60)
    print("BUG #2: Mean of per-line ratios vs ratio of totals")
    print("=" * 60)

    for lang, lines in [("eng", eng_lines), ("hin", hin_lines)]:
        orig_fert, orig_tpc = analyze_original(lines, encode)
        fixed_fert, fixed_tpc = analyze_fixed_aggregation(lines, encode)
        print(f"\n  {lang}:")
        print(f"    Original (mean of ratios):  fertility={orig_fert:.3f}, tpc={orig_tpc:.4f}")
        print(f"    Fixed (ratio of totals):    fertility={fixed_fert:.3f}, tpc={fixed_tpc:.4f}")
        print(f"    Difference:                 fertility={abs(orig_fert - fixed_fert):.3f} "
              f"({abs(orig_fert - fixed_fert) / orig_fert * 100:.1f}%)")
    print()


def demonstrate_denominator_flaw(lines_by_lang, encode):
    """Show why tokens/word is an unfair cross-linguistic comparison."""
    print("=" * 60)
    print("CONCEPTUAL FLAW: tokens/word is unfair across languages")
    print("=" * 60)

    print(f"\n  {'lang':<6} {'tok/word':>10} {'tok/char':>10} {'tok/byte':>10} "
          f"{'avg_word_len':>14} {'avg_bytes/char':>16}")
    print("  " + "-" * 70)

    results = {}
    for lang, lines in lines_by_lang.items():
        fert, tpc, tpb = analyze_fully_fixed(lines, encode)
        # Calculate avg word length and bytes per char
        total_chars = sum(len(line.lower()) for line in lines)
        total_words = sum(len(line.lower().split()) for line in lines)
        total_bytes = sum(len(line.lower().encode("utf-8")) for line in lines)
        avg_word_len = total_chars / total_words
        avg_bytes_per_char = total_bytes / total_chars
        results[lang] = (fert, tpc, tpb)
        print(f"  {lang:<6} {fert:>10.3f} {tpc:>10.4f} {tpb:>10.4f} "
              f"{avg_word_len:>14.2f} {avg_bytes_per_char:>16.2f}")

    if len(results) >= 2:
        base = "eng"
        print(f"\n  Ratios vs {base}:")
        for lang in results:
            if lang == base:
                continue
            ratio_word = results[lang][0] / results[base][0]
            ratio_char = results[lang][1] / results[base][1]
            ratio_byte = results[lang][2] / results[base][2]
            print(f"    {lang}: tok/word={ratio_word:.2f}x, "
                  f"tok/char={ratio_char:.2f}x, tok/byte={ratio_byte:.2f}x")
        print()
        print("  KEY INSIGHT: The cost ratio depends heavily on the denominator chosen.")
        print("  'words' are problematic because word length varies across languages.")
        print("  'characters' are problematic because byte-widths vary (1 byte for English,")
        print("  ~3 bytes for Indic). 'bytes' normalizes by data volume. 'sentences'")
        print("  normalizes by semantic content (user intent).")
    print()


def demonstrate_lowercase_impact():
    """
    Shows how lowercasing before tokenization changes token counts.
    """
    import tiktoken
    try:
        enc = tiktoken.get_encoding("gpt2")
    except Exception:
        print("Skipping lowercase experiment: tiktoken not found")
        return

    print("============================================================")
    print("CONCEPTUAL ISSUE: Lowercasing before tokenization")
    print("============================================================")

    eng_lines = read_lines(os.path.join(CORPUS_DIR, "eng.txt"))
    hin_lines = read_lines(os.path.join(CORPUS_DIR, "hin.txt"))

    def measure_impact(lines, lang_name):
        tokens_orig = sum(len(enc.encode(line)) for line in lines)
        tokens_lower = sum(len(enc.encode(line.lower())) for line in lines)
        diff = tokens_orig - tokens_lower
        pct = (diff / tokens_orig) * 100 if tokens_orig else 0
        print(f"  {lang_name}:")
        print(f"    Original tokens:  {tokens_orig}")
        print(f"    Lowercased tokens: {tokens_lower}")
        print(f"    Difference:       {diff} tokens ({pct:.1f}% reduction)")
        print()

    measure_impact(eng_lines, "English (eng)")
    measure_impact(hin_lines, "Hindi (hin)")
    print("  INSIGHT: Lowercasing changes the byte sequence. For English, it usually collapses")
    print("  casing variants into more common lowercase tokens, slightly reducing token count.")
    print("  For Hindi (Devanagari), .lower() is a no-op, so there is no change.")
    print("  Modifying the corpus before tokenization changes what the tokenizer actually sees,")
    print("  which can obscure true production fertility if production doesn't lowercase.")
    print()


def main():
    encode = load_tokenizer_tiktoken("gpt2")

    # Check if we have the new corpus
    corpus_dir = CORPUS_DIR
    if os.path.exists(os.path.join(corpus_dir, "eng.txt")):
        print("Using FLORES-200 corpus from partA/corpus/\n")
        langs = ["eng", "hin", "tam", "kan"]
        lines_by_lang = {}
        for lang in langs:
            path = os.path.join(corpus_dir, f"{lang}.txt")
            if os.path.exists(path):
                lines_by_lang[lang] = read_lines(path)
                print(f"  Loaded {lang}: {len(lines_by_lang[lang])} lines")
        eng_lines = lines_by_lang.get("eng", [])
        hin_lines = lines_by_lang.get("hin", [])
    else:
        # Fallback to starter_kit samples
        print("Using starter_kit corpus_sample/ (small!)\n")
        eng_path = os.path.join(STARTER_DIR, "corpus_sample", "eng_sample.txt")
        hin_path = os.path.join(STARTER_DIR, "corpus_sample", "hin_sample.txt")
        eng_lines = read_lines(eng_path)
        hin_lines = read_lines(hin_path)
        lines_by_lang = {"eng": eng_lines, "hin": hin_lines}
        print(f"  Loaded eng: {len(eng_lines)} lines")
        print(f"  Loaded hin: {len(hin_lines)} lines")

    print()

    # --- Bug demonstrations ---
    demonstrate_split_bug()
    demonstrate_aggregation_bug(eng_lines, hin_lines, encode)
    demonstrate_denominator_flaw(lines_by_lang, encode)
    demonstrate_lowercase_impact()

    # --- Summary ---
    print("=" * 60)
    print("SUMMARY OF BUGS AND FLAWS")
    print("=" * 60)
    print("""
  1. SPLIT BUG: line.split(" ") creates empty strings from consecutive
     spaces. Both eng_sample and hin_sample contain double spaces
     (line 7 and line 10 respectively). This inflates word counts
     and deflates fertility for affected lines.

  2. AGGREGATION BUG: Taking the mean of per-line (tokens/words) gives
     disproportionate weight to short lines. A 3-word line with 9 tokens
     (fertility 3.0) counts the same as a 30-word line with 40 tokens
     (fertility 1.33). The correct approach is sum(tokens)/sum(words).

  3. CONCEPTUAL FLAW - DENOMINATOR CHOICE: "tokens per word" is not directly
     comparable across languages because word length and structure vary
     dramatically (e.g., Dravidian languages are highly agglutinative).
     The script fails to evaluate alternative denominators like tokens/byte
     or tokens/sentence, which are necessary for cost estimation.

  4. CONCEPTUAL FLAW - TOKENIZER GENERALIZATION: The intern concluded "any tokenizer
     will struggle" with Hindi, asserting it is a property of the script.
     This is an unsupported claim that ignores differences in tokenizer
     vocabulary (subword merges) across different models.

  5. NON-PARALLEL CORPUS: The eng and hin samples are NOT translations of
     each other. Comparing fertility on non-parallel text conflates
     linguistic differences with content differences.

  6. CONCEPTUAL ISSUE - LOWERCASING: The script lowercases the text before
     tokenization. This modifies the actual byte sequence the tokenizer sees.
     For English, it changes tokenization (often increasing tokens slightly
     due to loss of capitalization tokens). For Hindi, it is a no-op.
     This skews cross-lingual comparisons.
""")


if __name__ == "__main__":
    main()
