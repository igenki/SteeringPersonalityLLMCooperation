# BFIスコア再現性実験

## 概要

このディレクトリには、BFI（Big Five Inventory）スコアの再現性を検証する実験が含まれています。

### 実験の目的

LLMに対して以下の手順でBFIスコアの再現性を測定します：

1. **初回BFI測定**：ペルソナなしの状態でBFI-44（44問の質問）に回答
2. **2回目BFI測定**：初回で測定されたスコアを明示的にプロンプトで与えた状態で、もう一度BFI-44に回答
3. **再現性の分析**：2つのスコアを比較し、LLMがどれほど一貫してスコアを再現できるかを分析

### 既存の実験との違い

- **既存の実験**：BFI測定 → 繰り返し囚人のジレンマゲーム
- **この実験**：BFI測定 → BFI測定（再現性チェック）

囚人のジレンマゲームは実行せず、BFIスコアの安定性のみに焦点を当てています。

## ファイル構成

```
Re_BFI/
├── README.md                    # このファイル
├── config_re_bfi.json          # 実験設定ファイル
├── main_re_bfi.py              # メインスクリプト
├── analyze_re_bfi.py           # 結果分析スクリプト
├── logs/                       # ログファイル
└── results/                    # 実験結果
    └── YYYYMMDD_HHMMSS_ReBFI_<model>/
        ├── final_results.json           # 最終結果（JSON形式）
        ├── summary.txt                   # サマリー（テキスト形式）
        ├── intermediate_results_*.json  # 中間結果
        ├── detailed_results.csv         # 詳細結果（CSV形式）
        ├── summary_statistics.csv       # 統計サマリー（CSV形式）
        ├── scatter_plots.png            # 散布図
        ├── difference_boxplot.png       # 箱ひげ図
        ├── mae_histogram.png            # MAEヒストグラム
        └── correlation_heatmap.png      # 相関ヒートマップ
```

## 使い方

### 1. 設定ファイルの準備

`config_re_bfi.json`を編集して、実験設定を変更できます：

```json
{
    "model_settings": {
        "model_name": "gpt-3.5-turbo",  # 使用するモデル
        "api_key": "",                   # APIキー（環境変数OPENAI_API_KEYでも指定可能）
        "temperature": 0.7
    },
    "re_bfi_settings": {
        "first_bfi_iterations": 5,      # 初回BFI測定の繰り返し回数
        "second_bfi_iterations": 5,     # 2回目BFI測定の繰り返し回数
        "total_experiments": 10,        # 実験の総回数
        "bfi_mode": "numbers_and_language",
        
        "use_existing_scores": false,   # 既存スコアを使用する場合は true
        "existing_scores_source": null  # 既存スコアのファイルパスまたは配列
    }
}
```

#### 既存のBFIスコアを使用する場合

既存実験の結果を使って2回目の測定のみを実行できます。詳細は[USAGE_EXISTING_SCORES.md](USAGE_EXISTING_SCORES.md)を参照してください。

**クイック例**:
```json
{
    "re_bfi_settings": {
        "use_existing_scores": true,
        "existing_scores_source": "results/YYYYMMDD_HHMMSS_*/control_BFI.json",
        "total_experiments": 1
    }
}
```

### 2. 実験の実行

プロジェクトルートから以下のコマンドを実行：

```bash
# デフォルト設定で実行
python Re_BFI/main_re_bfi.py

# カスタム設定ファイルを指定
python Re_BFI/main_re_bfi.py --config /path/to/custom_config.json
```

### 3. 結果の分析

実験が完了したら、分析スクリプトを実行：

```bash
python Re_BFI/analyze_re_bfi.py --results Re_BFI/results/YYYYMMDD_HHMMSS_ReBFI_<model>/final_results.json
```

このコマンドにより以下が生成されます：
- 散布図（初回 vs 2回目のスコア）
- 箱ひげ図（特性ごとの差異）
- MAEヒストグラム
- 相関ヒートマップ
- CSVファイル

## 実験の詳細

### 測定される指標

1. **MAE（Mean Absolute Error）**：平均絶対誤差
   - 初回と2回目のスコア差の絶対値の平均
   - 小さいほど再現性が高い

2. **相関係数（Correlation）**
   - 初回と2回目のスコアの相関
   - 1に近いほど再現性が高い

3. **RMSE（Root Mean Square Error）**：二乗平均平方根誤差
   - MAEよりも大きな誤差にペナルティを与える指標

4. **特性ごとの差異**
   - 各Big Five特性（開放性、誠実性、外向性、協調性、神経症傾向）ごとの差異

### 実験フロー

```
[初回BFI測定]
↓
システムプロンプトなし
↓
44問のBFI質問に回答
↓
スコアを計算（5つの特性ごと）
↓
[2回目BFI測定]
↓
システムプロンプト：「あなたのBig Fiveスコアは[O, C, E, A, N] = [3.5, 4.2, 2.8, 4.0, 3.1]です」
↓
44問のBFI質問に回答
↓
スコアを計算
↓
[差異の分析]
↓
MAE、相関係数、RMSEを計算
```

## 実験結果の解釈

### 高い再現性の指標
- MAE < 0.3
- 相関係数 > 0.8
- すべての特性で一貫した差異

### 低い再現性の指標
- MAE > 0.7
- 相関係数 < 0.5
- 特性ごとに大きくばらつく差異

## トラブルシューティング

### APIキーエラー
```
export OPENAI_API_KEY="your-api-key-here"
```

または`config_re_bfi.json`の`api_key`フィールドに直接記入してください。

### メモリ不足
`total_experiments`の値を減らして実験回数を調整してください。

### 実験の中断
中間結果は自動的に保存されます。`intermediate_results_exp*.json`ファイルから再開できます。

## 引用

この実験は以下の研究に基づいています：

- PersonaLLM研究のBFI測定手法
- 既存の囚人のジレンマ実験のフレームワーク

## ライセンス

このコードは研究目的で使用してください。
