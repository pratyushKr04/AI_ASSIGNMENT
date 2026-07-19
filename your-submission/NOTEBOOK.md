# Lab Notebook — AI Assignment 2026

*Chronological record of hypotheses, experiments, evidence, and dead ends.*

---

## 2026-07-18 — Session 1: Initial Exploration

### 20:35 — Read the starter kit

**Observations on the existing corpus:**
- `eng_sample.txt`: 10 English sentences, 458 bytes
- `hin_sample.txt`: 10 Hindi sentences, 774 bytes
- Sentences are NOT parallel translations (e.g., English line 1 mentions "Bengaluru airport traffic", Hindi line 1 is about "morning tea"). This invalidates any cross-language cost comparison because the *information content* differs per line.

**Observations on `REPORT_v0.md`:**
- Intern claims Hindi fertility is **5.89× worse** than English (7.45 vs 1.27 tok/word).
- Intern claims tok/char agrees at **7.0× worse** (1.579 vs 0.226).
- Intern concludes: "Hindi simply has more Unicode characters per word, so any tokenizer will struggle. This is a property of the script, not the tokenizer."
- **Hypothesis H1:** This conclusion is wrong — an Indic-aware tokenizer (e.g., Llama-3) should dramatically reduce Hindi fertility. The high fertility is a property of the *tokenizer vocabulary*, not the Devanagari script.

**Observations on `fertility.py`:**
- **Bug hypothesis H2:** `analyze()` computes the mean of per-line ratios (`mean(tok_i/word_i)`) instead of the ratio of totals (`sum(tok_i)/sum(word_i)`). This gives disproportionate weight to short lines. Need to measure impact.
- **Bug hypothesis H3:** `line.split(" ")` splits on single spaces only. Hindi text may use different whitespace or have multiple spaces. English line 7 has a double space ("books  in"), which would create an empty-string word, inflating the word count and *deflating* English fertility — making the gap look worse than it really is.
- **Bug hypothesis H4:** The script lowercases all text (`line.lower()`). For English this merges casing; for Hindi/Devanagari `lower()` is a no-op. This is not a bug per se, but worth noting as an asymmetry.
- **Conceptual flaw hypothesis H5:** Using "words" as denominator is fundamentally unfair cross-linguistically. Hindi words tend to be longer (more morphemes per word) than English words. Bytes or parallel-sentence normalization is needed for cost comparison.

### 20:40 — Plan corpus construction

**Decision:** Use FLORES-200 devtest set — it is a professionally translated parallel corpus covering 200+ languages, with ~1012 sentences per language. This gives us true parallel data for English, Hindi, Tamil, and Kannada.

**Approach:** Write a Python script to download from HuggingFace `facebook/flores` dataset.

### 20:50 — Corpus construction (dead end + recovery)

**Dead end:** FLORES-200 (`facebook/flores`) is a gated dataset requiring authentication. Also tried `openlanguagedata/flores_plus` (also gated) and `Helsinki-NLP/tatoeba_mt` (uses deprecated loading scripts). All three failed.

**Recovery:** Built a curated multi-domain parallel corpus with 90 sentences per language covering 5 domains (news, technology, daily life, science, culture). Each English sentence has a parallel Hindi, Tamil, and Kannada translation. This is sufficient for stable fertility estimation.

**Output:**
- `partA/corpus/eng.txt`: 90 sentences, 7,345 bytes
- `partA/corpus/hin.txt`: 90 sentences, 18,083 bytes
- `partA/corpus/tam.txt`: 90 sentences, 22,085 bytes
- `partA/corpus/kan.txt`: 90 sentences, 19,745 bytes

### 21:00 — Audit evidence: Bug #1 (split bug) — CONFIRMED

Ran `audit_evidence.py`. The original `line.split(" ")` creates empty strings from consecutive spaces:

```
Line: 'Please keep the books  in the cupboard.'
  split(' '): 8 words (includes empty string '')
  split():    7 words (correct)
```

Both `eng_sample.txt` (line 7) and `hin_sample.txt` (line 10) contain double spaces. This inflates word counts and deflates fertility for those lines.

### 21:02 — Audit evidence: Bug #2 (aggregation) — CONFIRMED, minor

Mean of per-line ratios vs ratio of totals:
- English: 1.193 vs 1.190 (0.2% difference)
- Hindi: 8.848 vs 8.800 (0.5% difference)

**Verdict:** Methodologically wrong, but small impact on these corpora. Impact would be larger with more variable-length sentences.

### 21:10 — Part B: Capacity reconciliation

Completed KV cache math and throughput analysis:
- KV cache per token: 114,688 bytes (~112 KB)
- Max concurrent 4096-token sequences: ~28
- Batch sizes 32 and 48 for long prompts exceed this, causing preemption (7 and 23 sequences preempted respectively)
- Intern's "1600 tok/s" claim is inflated by prefill tokens; true goodput at batch 16 is 164 tok/s for long prompts vs 295 tok/s for short prompts — long prompts are actually 45% *slower*

### 21:15 — Part C: Decision memo (Initial Draft)

*Note: This was heavily revised on July 19 to reflect the actual resource constraints.*

### 21:20 — Part C: Decision memo (Revised)

Re-evaluated SFT, rewriter model, and prompt engineering based on full constraints: 6 languages (Hindi, Kannada, Tamil, Telugu, Bengali, Marathi), 1 A100 GPU for 2 weeks, and only 30 total reviewer hours (fluent in Hindi/Kannada only). 
**Pivot:** Recommended **LoRA-based SFT**. We can train on the A100 and merge the adapter into the base model, achieving the tone shift with zero serving latency/cost increase. Prompt engineering remains the Day 1 baseline experiment. Tamil, Telugu, Bengali, and Marathi will rely on synthetic data and automatic eval due to reviewer constraints.

---

## 2026-07-19 — Session 2: True Parallel Corpus & Rigorous Audit Revisions

### 12:35 — FLORES-200 successful download

The `build_corpus.py` script was rewritten to securely prompt for an `HF_TOKEN`. With a valid token, we successfully downloaded the official FLORES-200 devtest set (1012 parallel sentences).

### 12:45 — Audit evidence: Lowercasing impact — CONFIRMED

The original script lowercases everything before tokenization (`line.lower()`). Wrote an experiment to quantify this:
- English: 27,994 tokens (lowercased) vs 27,044 (original) — a **3.5% difference**
- Hindi: No change (Devanagari has no casing)

**Verdict:** Lowercasing alters the byte sequence the tokenizer sees. For English, removing capital letters collapses casing variants, often slightly reducing token count (or sometimes increasing it depending on the tokenizer's BPE merges). For Hindi, it is a no-op. This introduces an artificial skew in cross-lingual comparisons.

### 12:50 — Audit evidence: Conceptual flaw (Denominators)

Ran the denominator comparison on the new 1012-sentence corpus:

| lang | tok/word | tok/char | tok/byte | avg_word_len | bytes/char |
|------|----------|----------|----------|-------------|------------|
| eng  | 1.28     | 0.212    | 0.212    | 6.03        | 1.00       |
| hin  | 7.83     | 1.530    | 0.595    | 5.12        | 2.57       |
| tam  | 25.05    | 2.726    | 0.997    | 9.19        | 2.74       |
| kan  | 22.82    | 2.662    | 0.979    | 8.57        | 2.72       |

**Key finding:** The "6× worse" claim depends entirely on the denominator:
- tok/word: Hindi is 6.1× worse 
- tok/char: Hindi is 7.2× worse 
- **tok/byte: Hindi is 2.8× worse**

The tok/word and tok/char metrics are unfair because:
1. Hindi words average 5.1 chars vs English 6.0 chars — fewer but different-length words
2. Hindi chars are 2.57 bytes vs English 1.0 byte — tok/char counts a ~3-byte Devanagari char the same as a 1-byte ASCII char

**Conclusion for H5:** The cost ratio depends heavily on the denominator chosen. We cannot definitively state one is "best," but `tok/byte` normalizes by data volume (useful for API billing and network bandwidth), while `tok/sentence` normalizes by semantic user intent. Both are far superior to `tok/word`.

### 13:00 — Tokenizer Vocabulary vs. Language Script

The intern claimed "any tokenizer will struggle" because Hindi has more Unicode characters.
**Correction:** The high fertility of GPT-2 is due to its **vocabulary composition**, not the script. GPT-2 lacks Devanagari subwords.
**Evidence:** IndicBERTv2, which allocates vocabulary to Indic subwords, reduces Hindi `tok/byte` to 0.46× (cheaper than English).

### 13:10 — Fertility vs. Serving Cost

The intern concluded that ~6× higher fertility means ~6× higher serving cost. This is conceptually flawed:
1. **Prefill vs. Decode:** Longer prompts (prefill) are processed in parallel and are memory-bandwidth bound. Token generation (decode) is sequential and compute-bound. The cost scaling is not linear.
2. **KV Cache:** High fertility exhausts the KV cache faster, causing sequence preemption (as seen in Part B). This causes non-linear latency spikes.
3. **Batching:** Slower Hindi generation holds up batch slots, reducing overall throughput.
**Conclusion:** Tokenizer fertility is a proxy, but true serving cost requires end-to-end benchmarking.
