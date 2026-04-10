# 既存実験結果を使ったBFI再現性実験の実行ガイド

## 概要

既存の3つのモデル（GPT-3.5-turbo、GPT-4o、GPT-5）の実験結果を使って、BFIスコアの再現性を検証します。

## 既存実験の結果サマリー

### GPT-3.5-turbo (2025-12-27実施)
- **データソース**: `results/20251227_100957_BFI20_PDI10_PDR100_Mgpt35turbo/control_BFI.json`
- **測定回数**: 20回
- **平均BFIスコア**:
  - 開放性 (Openness): 4.58
  - 誠実性 (Conscientiousness): 4.06
  - 外向性 (Extraversion): 3.78
  - 協調性 (Agreeableness): 4.24
  - 神経症傾向 (Neuroticism): 1.96

### GPT-4o (2026-01-01実施)
- **データソース**: `results/20260101_094922_BFI20_PDI10_PDR100_Mgpt4o/control_BFI.json`
- **測定回数**: 20回
- **平均BFIスコア**:
  - 開放性 (Openness): 4.68
  - 誠実性 (Conscientiousness): 4.12
  - 外向性 (Extraversion): 3.15
  - 協調性 (Agreeableness): 4.27
  - 神経症傾向 (Neuroticism): 1.98

### GPT-5 (2026-01-02実施)
- **データソース**: `results/20260102_081814_BFI20_PDI10_PDR100_Mgpt5/control_BFI.json`
- **測定回数**: 20回
- **平均BFIスコア**:
  - 開放性 (Openness): 4.69
  - 誠実性 (Conscientiousness): 4.69
  - 外向性 (Extraversion): 3.11
  - 協調性 (Agreeableness): 4.27
  - 神経症傾向 (Neuroticism): 2.11

## 実験の実行方法

### ステップ1: APIキーの設定

```bash
export OPENAI_API_KEY="your-api-key-here"
```

### ステップ2: 各モデルで実験を実行

#### GPT-3.5-turbo の実験実行

```bash
python Re_BFI/main_re_bfi.py --config Re_BFI/config_gpt35turbo.json
```

**実行時間**: 約30-45分
**APIコスト**: 2回目のBFI測定のみ（44問×20回）

#### GPT-4o の実験実行

```bash
python Re_BFI/main_re_bfi.py --config Re_BFI/config_gpt4o.json
```

**実行時間**: 約30-45分
**APIコスト**: 2回目のBFI測定のみ（44問×20回）

#### GPT-5 の実験実行

```bash
python Re_BFI/main_re_bfi.py --config Re_BFI/config_gpt5.json
```

**実行時間**: 約30-45分
**APIコスト**: 2回目のBFI測定のみ（44問×20回）

### ステップ3: すべてのモデルを一括実行（オプション）

```bash
# 順次実行
for model in gpt35turbo gpt4o gpt5; do
    echo "=== Running experiment for $model ==="
    python Re_BFI/main_re_bfi.py --config Re_BFI/config_${model}.json
    echo "=== Completed $model ==="
    echo ""
done
```

## 実験の仕様

### 実験フロー

```
[既存スコアの読み込み]
↓
既存実験の初回BFIスコア（20回の平均）を取得
↓
[2回目のBFI測定] × 20回
↓
各測定で既存スコアをシステムプロンプトに明示
"You have the following Big Five personality scores: [O, C, E, A, N]"
↓
44問のBFI質問に回答
↓
[スコア差異の分析]
↓
- MAE（平均絶対誤差）
- 相関係数
- RMSE
- 特性ごとの詳細分析
```

### 設定の詳細

- **`first_bfi_iterations: 0`** - 初回測定をスキップ
- **`second_bfi_iterations: 20`** - 2回目測定を20回実施
- **`total_experiments: 1`** - 1つの既存スコアを使用
- **`use_existing_scores: true`** - 既存スコアを使用
- **`bfi_mode: "numbers_and_language"`** - 既存実験と同じモード

## 結果の確認

### 実験完了後の出力

```
Re_BFI/results/YYYYMMDD_HHMMSS_ReBFI_<model>/
├── final_results.json          # 全結果データ
├── summary.txt                 # 読みやすいサマリー
├── intermediate_results_exp1.json  # 中間結果
└── prompt_logs/                # プロンプトログ
```

### サマリーの表示

```bash
# GPT-3.5-turboの結果
cat Re_BFI/results/YYYYMMDD_HHMMSS_ReBFI_gpt35turbo/summary.txt

# GPT-4oの結果
cat Re_BFI/results/YYYYMMDD_HHMMSS_ReBFI_gpt4o/summary.txt

# GPT-5の結果
cat Re_BFI/results/YYYYMMDD_HHMMSS_ReBFI_gpt5/summary.txt
```

### 期待される指標

各モデルの再現性を以下の指標で評価：

- **MAE（平均絶対誤差）**: 0.2-0.5程度を期待
- **相関係数**: 0.7-0.9程度を期待
- **RMSE**: MAEより若干大きい値

## 結果の分析

### グラフとCSVの生成

```bash
# GPT-3.5-turboの分析
python Re_BFI/analyze_re_bfi.py --results Re_BFI/results/YYYYMMDD_HHMMSS_ReBFI_gpt35turbo/final_results.json

# GPT-4oの分析
python Re_BFI/analyze_re_bfi.py --results Re_BFI/results/YYYYMMDD_HHMMSS_ReBFI_gpt4o/final_results.json

# GPT-5の分析
python Re_BFI/analyze_re_bfi.py --results Re_BFI/results/YYYYMMDD_HHMMSS_ReBFI_gpt5/final_results.json
```

### 生成されるファイル

各モデルについて以下が生成されます：

1. **散布図** (`scatter_plots.png`)
   - 初回 vs 2回目のスコア
   - 5つの特性すべて
   - 相関係数を表示

2. **箱ひげ図** (`difference_boxplot.png`)
   - 特性ごとのスコア差異

3. **MAEヒストグラム** (`mae_histogram.png`)
   - 平均絶対誤差の分布

4. **相関ヒートマップ** (`correlation_heatmap.png`)
   - 特性間の相関

5. **CSV** (`detailed_results.csv`, `summary_statistics.csv`)
   - Excelで開ける詳細データ

## モデル間の比較

### 比較分析のヒント

1. **再現性の比較**
   - どのモデルが最も一貫してスコアを再現できるか？
   - MAEが最も小さいモデルは？

2. **特性ごとの傾向**
   - 開放性が最も再現しやすい？
   - 神経症傾向が最もブレやすい？

3. **モデルの違い**
   - GPT-3.5-turbo vs GPT-4o vs GPT-5
   - より高度なモデルほど再現性が高い？

### 結果のまとめ方

すべてのモデルの結果をまとめた比較表を作成：

| モデル | MAE | 相関係数 | RMSE | 最も安定した特性 | 最も不安定な特性 |
|--------|-----|----------|------|------------------|------------------|
| GPT-3.5-turbo | ? | ? | ? | ? | ? |
| GPT-4o | ? | ? | ? | ? | ? |
| GPT-5 | ? | ? | ? | ? | ? |

## トラブルシューティング

### エラー: "既存スコアファイルが見つかりません"

**確認事項**:
```bash
# ファイルの存在確認
ls results/20251227_100957_BFI20_PDI10_PDR100_Mgpt35turbo/control_BFI.json
ls results/20260101_094922_BFI20_PDI10_PDR100_Mgpt4o/control_BFI.json
ls results/20260102_081814_BFI20_PDI10_PDR100_Mgpt5/control_BFI.json
```

### 実験の中断

中間結果は自動保存されています：
```bash
ls Re_BFI/results/YYYYMMDD_HHMMSS_ReBFI_*/intermediate_*.json
```

### APIレート制限

実験間に休憩を入れる：
```bash
python Re_BFI/main_re_bfi.py --config Re_BFI/config_gpt35turbo.json
sleep 300  # 5分休憩
python Re_BFI/main_re_bfi.py --config Re_BFI/config_gpt4o.json
sleep 300
python Re_BFI/main_re_bfi.py --config Re_BFI/config_gpt5.json
```

## 次のステップ

1. ✅ 既存実験の結果を確認
2. ✅ 設定ファイルの作成
3. 🔄 各モデルで実験を実行
4. 📊 結果の分析とグラフ生成
5. 📝 モデル間の比較とまとめ
6. 📄 論文やプレゼンテーションに使用

## 期待される成果

- 各モデルのBFIスコア再現性の定量的評価
- モデル間の再現性の比較
- LLMの性格一貫性に関する洞察
- 既存実験との整合性の検証

実験が成功することを祈っています！🔬✨
