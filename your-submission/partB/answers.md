# Part B: AI Serving Assignment Answers

## B1: KV Cache Math
**1. KV-cache size per token:**
Each token's KV cache requires storing the Key and Value vectors for all layers.
- Number of layers: 28
- KV heads (GQA): 8
- Head dimension: 128
- Vectors per token per layer: 2 (Key and Value)
- Values per token per layer: 2 × 8 × 128 = 2,048
- Precision: fp16 (2 bytes per value)
- Size per token per layer: 2,048 × 2 bytes = 4,096 bytes (4 KB)
- Total size per token (all layers): 28 × 4,096 bytes = **114,688 bytes (~112 KB)**

**2. Maximum concurrent 4096-token sequences:**
We must calculate the total GPU memory available for the KV cache.
- Total GPU Memory: 24 GiB = 25,769,803,776 bytes (assuming standard GiB typical for an L4 GPU)
- Usable GPU Memory (`gpu_memory_utilization` = 0.92): 25,769,803,776 × 0.92 = 23,708,622,848 bytes
- Model Weights Memory (4.2B params at fp16): 4,200,000,000 × 2 bytes = 8,400,000,000 bytes
- Non-KV runtime overhead: 1.6 GiB = 1,717,986,918 bytes (using GiB to match conventions)
- Memory available for KV Cache = Usable - Weights - Overhead 
  = 23,708,622,848 - 8,400,000,000 - 1,717,986,918 = **13,590,635,930 bytes**

*(Note: If using GB = 10^9 bytes strictly: 24 GB × 0.92 = 22.08 GB usable. KV Pool = 22.08 - 8.4 (weights) - 1.6 (overhead) = 12.08 GB = 12,080,000,000 bytes)*

- Max total tokens in KV cache: 13,590,635,930 / 114,688 ≈ **118,500 tokens**
- Max concurrent 4096-token sequences: 118,500 / 4096 ≈ **28.9 sequences** (i.e., maximum 28 concurrent sequences).

## B2: Throughput Anomaly
The intern assumed long-context throughput would scale linearly with batch size, but the bench log shows that throughput actually drops after batch size 24 (falling from 1607.4 tok/s at BS 24 to 1298.5 tok/s at BS 48). 

**Explanation:**
This degradation is caused by **KV cache exhaustion leading to sequence preemption**. From B1, the GPU can only hold ~28 concurrent sequences of length 4096. 
Looking at the bench log for the 3584 prompt + 512 gen runs:
- At batch size 24, `kv_cache_util` is at 0.93 and `preempted_seqs` is 0. Throughput is healthy (1607.4 tok/s).
- At batch size 32, the sequence count exceeds the max capacity of ~28. The `kv_cache_util` maxes out at 0.97, and the scheduler must preempt and swap/recompute sequences (`preempted_seqs` = 7). Throughput drops to 1384.0 tok/s.
- At batch size 48, severe thrashing occurs (`preempted_seqs` = 23). The system spends immense resources recomputing or swapping KV caches instead of generating new tokens, causing end-to-end latency to skyrocket (e2e_ms_p95 jumps from 69s to 105s) and throughput to collapse to 1298.5 tok/s.

## B3: Goodput
The intern claimed that "long prompts hit 1311 tok/s vs only 883 tok/s for short prompts," making long prompts seem more efficient. However, `reported_tok_s` includes both prefill (prompt) tokens and decode (generated) tokens. Prefill is highly parallelizable and processed quickly, artificially inflating the total token rate for long prompts.

The honest metric for a user-facing application is **Goodput** (useful generated output tokens per second).

**Goodput Calculation at Batch 16:**
* Short prompts (512 prompt, 256 gen):
  - Total generated tokens: 16 sequences × 256 tokens = 4,096 tokens
  - Wall clock time: 13.91 s
  - Goodput: 4,096 / 13.91 = **294.5 output tok/s**

* Long prompts (3584 prompt, 512 gen):
  - Total generated tokens: 16 sequences × 512 tokens = 8,192 tokens
  - Wall clock time: 49.97 s
  - Goodput: 8,192 / 49.97 = **163.9 output tok/s**

**Conclusion:** 
The intern misread the numbers by including the easily parallelizable prefill tokens. When we isolate the actual output generation speed (Goodput), the long prompts are nearly 45% *slower* per token (163.9 vs 294.5 tok/s) due to the heavier memory bandwidth toll per generated token.

## B4: Serving Metric
To monitor and prevent the throughput collapse described in B2, the single most critical metric to monitor is **`preempted_seqs`** (or alternatively, the sequence swap-out rate). 
If this metric is strictly greater than 0, it directly indicates that the system is taking on more concurrent sequences than the KV cache can hold, causing catastrophic latency and throughput degradation. Alerts should be configured to trigger when `preempted_seqs` > 0.
