# Sentio.io — model results (dataset v1)

Data: sentio_dataset_v1.csv, 1,844 reviews. Split 70/15/15 stratified, seed 42
(train 1,290 / val 277 / test 277). Every model picks its best epoch on VAL and
is scored on the frozen TEST split exactly once.

Task: one shared encoder, 8 heads — overall sentiment (neg/neu/pos) + 7 aspects
(none/negative/positive; the 29 aspect-level "neutral" labels merged into positive).

## Comparison (test split)

| Model | Overall macro-F1 | Accuracy | Positive F1 | Aspect detection F1 | Aspect sentiment F1 |
|---|---|---|---|---|---|
| Always 'negative' (majority class) | 0.304 | 0.838 | 0.000 | – | – |
| TF-IDF + Logistic Regression | 0.637 | 0.863 | 0.564 | 0.645 | 0.595 |
| **HingRoBERTa** | **0.800** | **0.928** | **0.778** | **0.721** | **0.664** |
| mBERT | 0.635 | 0.863 | 0.432 | 0.628 | 0.564 |
| XLM-RoBERTa | 0.598 | 0.870 | 0.550 | 0.586 | 0.566 |
| MuRIL (float32, lr 5e-5, 10 epochs) | 0.486 | 0.863 | 0.533 | 0.127 | 0.387 |
| MuRIL (float16, did not converge) | 0.304 | 0.838 | 0.000 | 0.112 | 0.364 |

Settings: lr 3e-5, batch 16, 6 epochs, max length 96, float16 mixed precision,
sqrt-inverse-frequency class weights, Colab T4 GPU — unless stated otherwise.

## Key points

- **HingRoBERTa is the selected model**: +16.3 macro-F1 points over the TF-IDF baseline,
  and the only model that handles neutral reviews reasonably (neutral F1 0.65).
  HingRoBERTa was pretrained on Hinglish text, which matches our Romanised code-mixed data.
- **Accuracy is misleading here**: always answering "negative" already gets 83.8%
  accuracy, because 84% of reviews are negative. Macro-F1 is the primary metric.
- **MuRIL** did not learn in float16 (loss 8.65 → 7.61, constant "negative" output).
  Re-run in float32 with lr 5e-5 for 10 epochs it learned slowly (loss 8.64 → 5.68)
  and reached 0.486 macro-F1, still well below HingRoBERTa (loss 6.43 → 1.19 in 6 epochs).
  Reported as observed; MuRIL might do better with further tuning.

## HingRoBERTa per aspect (test)

| Aspect | Detection F1 | Sentiment macro-F1 | Test mentions |
|---|---|---|---|
| refund_support | 0.894 | 0.617 | 66 |
| price_offers | 0.874 | 0.835 | 53 |
| delivery_time | 0.853 | 0.699 | 63 |
| food_quality | 0.851 | 0.819 | 72 |
| delivery_partner | 0.723 | 0.571 | 25 |
| app_experience | 0.652 | 0.514 | 69 |
| packaging | 0.200 | 0.593 | 8 |

Packaging is weak because it has only 37 training examples (and 1 positive).
Positive aspect labels are rare overall — the 450 new 4/5-star reviews
(to_annotate_v2.csv) are being annotated to fix this for dataset v2.

## Where things are

- Trained models (float16 weights): Google Drive → MyDrive/Sentio/models/{hingroberta, muril_v1, muril_fp32}
- All results, logs and test predictions: Google Drive → MyDrive/Sentio/results, /logs

## Dataset v2 (added 447 annotated 4/5-star reviews) — trained on the laptop GPU (RTX 5050)

Same script, settings and frozen test split as above. v1 was re-trained on the
laptop too, so v1 and v2 are compared on identical hardware.

| HingRoBERTa | Overall macro-F1 | Accuracy | Positive F1 | Neutral F1 | Aspect detection F1 | Aspect sentiment F1 |
|---|---|---|---|---|---|---|
| v1 (Colab T4) | 0.800 | 0.928 | 0.778 | 0.654 | 0.721 | 0.664 |
| v1 (laptop) | 0.772 | 0.917 | 0.750 | 0.600 | 0.711 | 0.682 |
| **v2 (laptop)** | **0.817** | 0.921 | **0.800** | **0.689** | 0.706 | 0.687 |
| TF-IDF + LR, v1 → v2 | 0.637 → 0.670 | | 0.564 → 0.622 | | 0.645 → 0.628 | 0.595 → 0.604 |

- The identical v1 run scored 0.800 on Colab and 0.772 on the laptop: single runs vary by about ±0.03.
  The v2 gain (+0.045 on the same machine) is real but modest; it shows mainly in positive and neutral reviews.
- Aspect-level test scores barely move because the frozen test set has very few positive aspect
  labels (e.g. 0 positive packaging, 1 positive refund) — there is little for the new data to improve on.
- **Deployed model:** hingroberta_local_v2 (ML/models/hingroberta_local_v2), served by ML/serve.py on port 8001.
