# クイックスタートガイド

## 1分で始めるBFI再現性実験

### ステップ1: APIキーの設定

```bash
export OPENAI_API_KEY="your-api-key-here"
```

### ステップ2: テスト実行（約5分）

```bash
cd /path/to/llm_personality_game
python Re_BFI/main_re_bfi.py --config Re_BFI/config_re_bfi_test.json
```

この設定では：
- 実験回数：2回
- 初回BFI繰り返し：1回
- 2回目BFI繰り返し：1回

### ステップ3: 結果の確認

実験完了後、以下のファイルが生成されます：

```
Re_BFI/results/YYYYMMDD_HHMMSS_ReBFI_gpt35turbo/
├── final_results.json      # JSON形式の全結果
├── summary.txt             # 読みやすいサマリー
└── intermediate_*.json     # 中間結果
```

`summary.txt`を開いて結果を確認：

```bash
cat Re_BFI/results/*/summary.txt
```

### ステップ4: 結果の分析とグラフ生成

```bash
# 最新の結果ファイルを指定
python Re_BFI/analyze_re_bfi.py --results Re_BFI/results/YYYYMMDD_HHMMSS_ReBFI_gpt35turbo/final_results.json
```

生成されるファイル：
- `scatter_plots.png` - 初回 vs 2回目のスコア散布図
- `difference_boxplot.png` - 特性ごとの差異
- `mae_histogram.png` - MAEの分布
- `correlation_heatmap.png` - 特性間の相関
- `detailed_results.csv` - 詳細データ（Excel等で開ける）
- `summary_statistics.csv` - 統計サマリー

## 本番実験の実行

テストが成功したら、本番設定で実行：

```bash
python Re_BFI/main_re_bfi.py --config Re_BFI/config_re_bfi.json
```

この設定では：
- 実験回数：10回
- 初回BFI繰り返し：5回
- 2回目BFI繰り返し：5回

実行時間の目安：約30-60分（モデルとAPI速度に依存）

## 既存のBFIスコアを使用する

既存実験の結果を使って、2回目のBFI測定のみを実行できます：

```bash
# ステップ1: 既存実験の結果を確認
ls results/YYYYMMDD_HHMMSS_*/control_BFI.json

# ステップ2: 設定ファイルを編集
# config_re_bfi_existing.json の existing_scores_source を設定

# ステップ3: 実験実行
python Re_BFI/main_re_bfi.py --config Re_BFI/config_re_bfi_existing.json
```

詳細は[USAGE_EXISTING_SCORES.md](USAGE_EXISTING_SCORES.md)を参照してください。

## よくある質問

### Q: 実験を途中で止めてしまった
A: 中間結果が自動保存されているため、最新の`intermediate_results_*.json`から状況を確認できます。

### Q: 別のモデルで実行したい
A: `config_re_bfi.json`の`model_name`を変更してください：
```json
"model_name": "gpt-4"  // または他のモデル
```

### Q: 実験回数を増やしたい
A: `config_re_bfi.json`の`total_experiments`を変更：
```json
"total_experiments": 20  // 20回実行
```

### Q: 結果をExcelで開きたい
A: `detailed_results.csv`をExcelで開けます。UTF-8エンコーディングで保存されています。

### Q: グラフが日本語で表示されない
A: システムに日本語フォントがインストールされていることを確認してください。

## トラブルシューティング

### エラー: "OpenAI API key not found"
```bash
export OPENAI_API_KEY="your-api-key-here"
```

### エラー: "モジュールが見つかりません"
```bash
pip install numpy pandas matplotlib seaborn
```

### エラー: "メモリ不足"
実験回数を減らすか、繰り返し回数を減らしてください。

## 実験結果の見方

### 高い再現性の例
```
平均絶対誤差 (MAE): 0.15
相関係数: 0.92
```
→ LLMは与えられたスコアを非常に一貫して再現している

### 低い再現性の例
```
平均絶対誤差 (MAE): 0.85
相関係数: 0.42
```
→ LLMは与えられたスコアを安定して再現できていない

## 次のステップ

1. 異なるモデルで実験を実行して比較
2. 異なる`bfi_mode`を試す（`"no_prompt"`, `"language_only"`など）
3. 繰り返し回数を変えて安定性への影響を調査
4. 結果を論文やプレゼンテーションに使用

## サポート

問題が発生した場合は、以下を確認：
1. ログファイル：`Re_BFI/logs/re_bfi_research.log`
2. エラーメッセージ
3. 設定ファイルの内容

ハッピーリサーチ！ 🔬
