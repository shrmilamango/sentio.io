| Model | Overall macro-F1 | Accuracy | Positive F1 | Aspect detection F1 | Aspect sentiment F1 |
|---|---|---|---|---|---|
| Always 'negative' (majority class) | 0.304 | 0.838 | 0.000 | – | – |
| TF-IDF + Logistic Regression | 0.637 | 0.863 | 0.564 | 0.645 | 0.595 |
| TF-IDF + Logistic Regression (dataset v2) | 0.670 | 0.859 | 0.622 | 0.628 | 0.604 |
| HingRoBERTa - dataset v1 (Colab T4) | 0.800 | 0.928 | 0.778 | 0.721 | 0.664 |
| HingRoBERTa - dataset v1 (laptop GPU) | 0.772 | 0.917 | 0.750 | 0.711 | 0.682 |
| HingRoBERTa - dataset v2 (laptop GPU) | 0.817 | 0.921 | 0.800 | 0.706 | 0.687 |
| mBERT | 0.635 | 0.863 | 0.432 | 0.628 | 0.564 |
| MuRIL (float32, lr 5e-5, 10 epochs) | 0.486 | 0.863 | 0.533 | 0.127 | 0.387 |
| MuRIL (float16, did not converge) | 0.304 | 0.838 | 0.000 | 0.112 | 0.364 |
| XLM-RoBERTa | 0.598 | 0.870 | 0.550 | 0.586 | 0.566 |
