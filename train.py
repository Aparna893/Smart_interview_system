"""
train.py  —  One-click training launcher for single T5-small model.

Run ONCE before starting the app:
    python train.py

What it does:
  1. Generates training data from real resumes + synthetic fallback
  2. Fine-tunes flan-T5-small for BOTH skill extraction AND question generation
  3. Saves model to models/t5_resume/

Time on 8GB RAM (CPU only):
  - Data generation : < 10 seconds
  - Training        : ~20–35 minutes
  - Total           : ~35 minutes (one-time only)

RAM usage peak: ~1.8 GB  (well within 8GB)
"""

import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def section(title):
    print("\n" + "=" * 58)
    print(f"  {title}")
    print("=" * 58)


def main():
    print("\n" + "=" * 58)
    print("  Resume AI — Single T5-small Training Pipeline")
    print("  Tasks : Skill Extraction + Question Generation")
    print("  RAM   : ~1.8 GB peak  |  Time : ~35 min (CPU)")
    print("=" * 58)

    # ── Step 1: Generate data ─────────────────────────────────────────────
    section("Step 1 / 2 — Building Training Data")
    t0 = time.time()
    from data.synthetic_dataset import build_datasets
    train_data, val_data = build_datasets()
    print(f"  Done in {time.time() - t0:.1f}s")

    # ── Step 2: Train ─────────────────────────────────────────────────────
    section("Step 2 / 2 — Fine-tuning flan-T5-small")
    print("  ~20–35 minutes on CPU. Go make some tea ☕")
    t0 = time.time()
    from core.train_t5 import train
    train()
    print(f"\n  Training complete in {(time.time() - t0)/60:.1f} min")

    # ── Done ──────────────────────────────────────────────────────────────
    section("Done!")
    print("  Model saved → models/t5_resume/")
    print()
    print("  Run the app:")
    print("    python run_app.py")
    print("    — or —")
    print("    streamlit run Home.py")


if __name__ == "__main__":
    main()