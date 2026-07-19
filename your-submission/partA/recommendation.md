# Recommendation Memo: Tokenizer Cost Analysis for Indic Languages

**From:** AI Serving Team  
**To:** Leadership  
**Date:** 2026-07-19  
**Subject:** Corrected tokenizer fertility numbers and routing recommendation  

---

## Executive Summary

The previous analysis (REPORT_v0) claimed Hindi is **5.89× more expensive** to serve than English based on tokenizer fertility. After a thorough audit, we found this number to be **misleading due to five issues** in the methodology. Our corrected analysis, using a parallel corpus and proper methodology, shows:

- **With GPT-2 tokenizer**: Hindi is **2.9× more expensive per byte** than English (not 5.9×). Tamil and Kannada are **~4.8× more expensive**.
- **With cl100k_base (GPT-4)**: Hindi drops to **1.9×**, Tamil to **2.4×**, Kannada to **3.1×**.
- **With IndicBERTv2 (Indic-aware)**: Hindi is **0.46×** (actually *cheaper* per byte than English!), Tamil is **0.33×**, Kannada is **0.39×**. This completely disproves the intern's claim that "any tokenizer will struggle".

## Bugs Found in the Original Analysis

| # | Issue | Impact |
|---|-------|--------|
| 1 | `split(" ")` creates phantom empty words from double spaces | Deflates English fertility (makes gap look worse) |
| 2 | Mean of per-line ratios instead of ratio of totals | ~0.5% skew, minor but methodologically wrong |
| 3 | `tok/word` denominator unfair across languages | Overstates gap by ~2× (Hindi words are longer) |
| 4 | Non-parallel corpus (different content in each language) | Conflates content differences with tokenizer cost |
| 5 | Tested only one tokenizer, concluded "all will struggle" | Ignored how vocabulary size/composition impacts fertility |
| 6 | Lowercased text before tokenization | Skews results (changes Eng byte sequence, no-op for Hin) |

## Corrected Numbers (GPT-2, parallel corpus, 1012 sentences)

### GPT-2 (baseline, non-Indic-aware)
| Language | tok/word | tok/byte | tok/sentence | Cost ratio (tok/byte vs English) |
|----------|----------|----------|-------------|----------------------------------|
| English  | 1.24     | 0.205    | 26.7        | 1.00×                            |
| Hindi    | 7.83     | 0.595    | 198.3       | 2.90×                            |
| Tamil    | 25.05    | 0.997    | 415.2       | 4.87×                            |
| Kannada  | 22.82    | 0.979    | 363.0       | 4.78×                            |

### cl100k_base (GPT-4 tokenizer)
| Language | tok/word | tok/byte | tok/sentence | Cost ratio (tok/byte vs English) |
|----------|----------|----------|-------------|----------------------------------|
| English  | 1.24     | 0.206    | 26.9        | 1.00×                            |
| Hindi    | 5.05     | 0.384    | 128.0       | 1.87×                            |
| Tamil    | 12.39    | 0.493    | 205.3       | 2.39×                            |
| Kannada  | 14.95    | 0.641    | 237.9       | 3.12×                            |

### IndicBERTv2 (Indic-optimized)
| Language | tok/word | tok/byte | tok/sentence | Cost ratio (tok/byte vs English) |
|----------|----------|----------|-------------|----------------------------------|
| English  | 1.24     | 0.205    | 26.8        | 1.00×                            |
| Hindi    | 1.24     | 0.094    | 31.3        | 0.46×                            |
| Tamil    | 1.70     | 0.067    | 28.1        | 0.33×                            |
| Kannada  | 1.85     | 0.079    | 29.4        | 0.39×                            |

**Key findings on Tokenizers:**
- The intern claimed "any tokenizer will struggle" due to the Devanagari script. Our results show this is incorrect.
- The high fertility of GPT-2 is due to its **vocabulary composition**, not the script. GPT-2's vocabulary lacks Devanagari subwords, forcing it to fall back to byte-level tokenization for Hindi.
- IndicBERTv2, which allocates a large portion of its vocabulary to Indic subwords, tokenizes Hindi far more efficiently (fewer tokens per word/byte/sentence).

## Why Tokenizer Fertility $\neq$ Serving Cost

The intern concluded that because Hindi has ~6× higher fertility, it costs ~6× more to serve. This is a major conceptual flaw. Tokenizer fertility is only one factor in the overall serving cost equation:

1. **Prompt vs. Generation:** High fertility increases both prompt length and generation length. However, prompt processing (prefill) is highly parallelized and memory-bandwidth bound, while token generation (decode) is sequential and compute/memory-latency bound. A 6× longer prompt does not take 6× as long to process.
2. **KV Cache Exhaustion:** As seen in Part B, long sequences exhaust the GPU's KV cache capacity, leading to sequence preemption and thrashing. High fertility causes requests to hit this memory wall much faster, which can cause latency spikes far worse than a simple 6× multiplier.
3. **Batching Dynamics:** If Hindi requests take longer to generate, they hold up batch slots in the serving engine, reducing overall throughput for all users (including English).
4. **Model Architecture:** Different models have different FLOPs-per-token overheads. 

Cost cannot be estimated by multiplying English cost by the tokenizer fertility ratio. True cost requires end-to-end benchmarking of the serving stack with the expected workload mixture.

## Routing Recommendation

1. **Switch to a tokenizer with Indic vocabulary coverage.** IndicBERTv2 reduces Hindi tokens/byte from 2.9× to 0.46× compared to GPT-2. The choice of tokenizer vocabulary matters far more than the choice of language.

2. **Benchmark multiple denominators.** When comparing tokenizers, rely on `tok/byte` for estimating network/storage volume and `tok/sentence` for estimating compute cost per user intent.

3. **Route Indic traffic to dedicated model instances** with Indic-optimized tokenizers. Do not share tokenizer infrastructure with English-only models.

## Production Monitoring Metric

**Monitor: `tok/byte` ratio per language, computed on a rolling window of real traffic.**

- Compute `total_output_tokens / total_output_bytes` per language per hour.
- Alert if any language exceeds 4× the English baseline ratio.
- This requires no parallel corpus and works on live traffic.

Periodically (monthly), re-run the parallel-sentence benchmark to validate that `tok/sentence` ratios remain stable.
