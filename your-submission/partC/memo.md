# Decision Memo: Casual Tone for Indic Languages

## Executive Summary
**Objective:** Improve the tone of FLM-4B-Instruct in six Indic languages (Hindi, Kannada, Tamil, Telugu, Bengali, Marathi) from "formal/textbook" to casual and colloquial within 3 weeks. 
**Constraints & Resources:** 
- 1 native-speaker reviewer (fluent in Hindi and Kannada only) available for 10 hours/week for 3 weeks (30 person-hours total).
- 1× A100-80GB GPU available for two weeks for training.
- The serving stack (L4 24GB GPUs) runs near capacity; serving cost cannot increase by more than 10%.
**Recommendation:** **LoRA-based Supervised Fine-Tuning (SFT)**. By training a LoRA adapter and merging it into the base model prior to deployment, we can fundamentally alter the model's tone without increasing serving latency or architecture complexity. Prompt engineering will serve as our Day 1 baseline and fallback.

---

## Evaluation of Approaches

### 1. Supervised Fine-Tuning (SFT) using LoRA (Recommended)
Train a Parameter-Efficient Fine-Tuning (PEFT) LoRA adapter on casual Indic data, then merge the learned weights back into the base model before deployment.

*   **Assumptions:** The provided A100-80GB GPU is highly sufficient for fine-tuning a 4.2B parameter model using LoRA. Merging the weights allows us to serve the new model on the existing L4 hardware without architecture changes.
*   **Engineering Trade-offs:**
    *   *Compute:* Training easily fits on the provided A100-80GB.
    *   *Serving Cost:* Zero increase. Once the LoRA adapter is merged into the base model, the deployed model has the exact same parameter count and architecture as the original. Inference latency and memory requirements remain essentially unchanged after the merge.
    *   *Development Time:* Requires curating a high-quality dataset, which is the primary bottleneck given our 30 total reviewer hours.
*   **Pros:** Can fundamentally alter deeply learned linguistic styles rather than just nudging the model. Zero serving overhead. Best long-term maintainability.
*   **Cons:** High dependency on data quality. Human review is limited to Hindi and Kannada; Tamil, Telugu, Bengali, and Marathi must rely on synthetic data generation and automatic evaluation initially.
*   **Success Criteria:** $\geq$ 70% reviewer preference over the baseline in blinded pairwise evaluation; no statistically significant increase in factual errors; no measurable increase (>5%) in inference latency after deployment.
*   **Kill Criteria:** Abort the SFT approach if, after the first week and initial training run: reviewer preference remains below 60%, OR factual error rate increases by more than 5%, OR the merged model shows any measurable serving regression beyond the deployment budget.

### 2. Prompt Engineering (System Prompt Modifications)
Modify the system prompt with language-specific instructions and few-shot examples.

*   **Assumptions:** The base model has sufficient instruction-following capability in all six languages to consistently alter its tone based solely on the prompt.
*   **Engineering Trade-offs:**
    *   *Compute/Memory:* Adding few-shot examples increases the prompt length. While prefill is relatively fast, longer prompts linearly increase the KV-cache memory required per request. On our memory-constrained L4s, this increases the percentage of VRAM allocated to KV-cache, reducing the maximum concurrent batch size and slightly degrading throughput.
    *   *Development Time:* Nearly instant. The lowest-risk and fastest approach to evaluate.
*   **Pros:** Zero training cost. Safest fallback if SFT fails.
*   **Cons:** Highly dependent on instruction following, which often fails to reliably change deeply learned formal styles in under-represented languages. Extremely difficult to guarantee a consistent casual tone across all six languages.
*   **Conclusion:** Use as the baseline experiment, but not the long-term solution.

### 3. Small Rewriter Model
Deploy a secondary, lightweight model to post-process and "casualize" the output of the main model.

*   **Assumptions:** A small model can accurately perform stylistic rewriting across six Indic languages without hallucinating facts.
*   **Engineering Trade-offs:**
    *   *Compute/Memory:* Requires loading a second set of model weights into the already constrained L4 GPUs, or provisioning entirely new hardware.
    *   *Serving Cost:* Every user request requires a second sequential decoding pass. This decreases system throughput, increases latency, and significantly increases the serving cost.
*   **Pros:** Isolates reasoning from tone formatting.
*   **Cons:** The architectural complexity and serving cost regressions make this unviable.

---

## Recommendation & Day 1 Experiment

**Recommendation:** Proceed with **LoRA-based SFT**. The assignment explicitly provides dedicated training hardware (A100-80GB) specifically to enable this. By merging the adapter, we achieve the tone shift without paying any ongoing serving tax, perfectly respecting the L4 memory constraints. 

**Reviewer Allocation:** The single reviewer (30 hours total) will focus exclusively on Hindi and Kannada for human-in-the-loop evaluation and data curation. For Tamil, Telugu, Bengali, and Marathi, we will generate synthetic casual data using a larger frontier model, relying on automatic evaluation (e.g., LLM-as-a-judge) and internal non-native review for the initial 3-week sprint, deferring native human validation until post-launch.

**Day 1 Experiment Design:**
Day 1 should not start with training. Before spending GPU time, we must establish our baseline and evaluate the low-hanging fruit:
1.  **Build Multilingual Eval Set:** Construct a small, diverse evaluation set across all 6 languages.
2.  **Generate Baselines:** Run the eval set through the current unmodified model.
3.  **Evaluate Prompt Variants:** Test prompt engineering variants (direct instructions vs. few-shot) to determine how far prompting alone can move the tone.
4.  **Decision Gate:** Determine whether prompt engineering alone reaches the target (unlikely for all 6 languages).
5.  **Begin LoRA Prep:** If prompt engineering falls short, immediately utilize the reviewer's first hours to curate the Hindi/Kannada training data and trigger the synthetic data pipeline for the other four languages. This reduces risk by establishing a strong baseline before utilizing the A100.
