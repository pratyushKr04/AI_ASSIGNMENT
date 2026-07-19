#!/usr/bin/env python3
"""
build_corpus.py -- Download parallel corpus from FLORES-200 for tokenizer evaluation.

Downloads the devtest split for English, Hindi, Tamil, and Kannada from
the HuggingFace `facebook/flores` dataset. Outputs one text file per language
with ~1012 parallel sentences.

This dataset is gated, meaning you must authenticate with a HuggingFace
account that has agreed to the FLORES dataset terms.

Usage:
    pip install datasets huggingface_hub
    python build_corpus.py
    
    (The script will prompt for your HF_TOKEN if not set in your environment).

Output:
    corpus/eng.txt
    corpus/hin.txt
    corpus/tam.txt
    corpus/kan.txt
    corpus/README.md
"""

import os
import sys
import getpass

def main():
    try:
        from datasets import load_dataset
        from huggingface_hub import login
    except ImportError:
        print("ERROR: Missing required packages. Run:")
        print("pip install datasets huggingface_hub")
        sys.exit(1)

    # Handle Authentication
    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token:
        print("This script requires access to the gated 'facebook/flores' dataset.")
        print("You can get a token from: https://huggingface.co/settings/tokens")
        print("Please enter your HuggingFace Read token below (input will be hidden):")
        hf_token = getpass.getpass("HF_TOKEN: ").strip()
        
    if hf_token:
        try:
            login(token=hf_token)
        except Exception as e:
            print(f"Failed to login: {e}")
            sys.exit(1)
    else:
        print("Error: No token provided. Exiting.")
        sys.exit(1)

    # FLORES-200 language codes
    # Format: lang_Script (ISO 639-3 + script)
    lang_map = {
        "eng": "eng_Latn",
        "hin": "hin_Deva",
        "tam": "tam_Taml",
        "kan": "kan_Knda",
    }

    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "corpus")
    os.makedirs(out_dir, exist_ok=True)

    print("\nDownloading FLORES-200 devtest split...")
    
    sentences = {lang: [] for lang in lang_map}
    
    for lang_short, lang_flores in lang_map.items():
        print(f"  Loading {lang_short} ({lang_flores})...")
        try:
            # We don't use trust_remote_code=True anymore per modern datasets best practices
            ds = load_dataset(
                "facebook/flores",
                lang_flores,
                split="devtest"
            )
            for row in ds:
                sentences[lang_short].append(row["sentence"].strip())
        except Exception as e:
            print(f"\nERROR: Could not load {lang_flores}.")
            print(f"Details: {e}")
            print("\nMake sure your HuggingFace account has accepted the terms for the")
            print("facebook/flores dataset at: https://huggingface.co/datasets/facebook/flores")
            sys.exit(1)

    # Verify all languages have the same number of sentences (parallel)
    lengths = {lang: len(sents) for lang, sents in sentences.items()}
    print(f"\nSentence counts: {lengths}")
    
    if len(set(lengths.values())) != 1:
        print("WARNING: Not all languages have the same number of sentences!")
        min_len = min(lengths.values())
        print(f"Truncating all to {min_len} sentences for parallelism.")
        for lang in sentences:
            sentences[lang] = sentences[lang][:min_len]
    else:
        min_len = next(iter(lengths.values()))

    # Write output files
    for lang_short, sents in sentences.items():
        out_path = os.path.join(out_dir, f"{lang_short}.txt")
        with open(out_path, "w", encoding="utf-8") as f:
            for s in sents:
                f.write(s + "\n")
        file_size = os.path.getsize(out_path)
        print(f"  Wrote {out_path}: {len(sents)} sentences, {file_size} bytes")

    # Write README
    readme_path = os.path.join(out_dir, "README.md")
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(f"# Evaluation Corpus\n\n")
        f.write(f"**Source:** FLORES-200 devtest split (facebook/flores on HuggingFace)\n")
        f.write(f"**Sentences per language:** {min_len}\n")
        f.write(f"**Languages:** English (eng), Hindi (hin), Tamil (tam), Kannada (kan)\n")
        f.write(f"**Parallel:** Yes — line N in every file is the same sentence.\n\n")
        f.write(f"## Domain & Caveats\n\n")
        f.write(f"- FLORES-200 is drawn from English Wikipedia and Wikinews, then\n")
        f.write(f"  professionally translated into 200+ languages.\n")
        f.write(f"- Domain: general knowledge / news. Not conversational.\n")
        f.write(f"- Caveat: translationese may slightly inflate target-language\n")
        f.write(f"  complexity (translators may use more formal/verbose phrasing).\n")

    print(f"\nDone! FLORES-200 corpus written to {out_dir}/")


if __name__ == "__main__":
    main()
