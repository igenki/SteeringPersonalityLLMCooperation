## 概要

1. **BFI（Big Five Inventory）測定** — ペルソナなしの LLM に 44 問の性格診断を実施し、ベースラインスコアを取得
2. **性格特性操作** — 特定の Big Five 特性（外向性・協調性・誠実性・神経症傾向・開放性）を高/低に強制設定
3. **囚人のジレンマゲーム** — 操作後の LLM を複数の戦略（TFT, GRIM, ALLC, ALLD 等）と対戦させ、協力率や報酬を測定
4. **結果出力** — 全ラウンドの行動データ・BFI スコア・プロンプトログを CSV/JSON で保存

## ディレクトリ構成

```
.
├── main.py                  # 実験のエントリーポイント
├── config.json              # 実験設定ファイル
├── requirements.txt         # Python 依存パッケージ
├── src/
│   ├── bfi_analyzer.py      # BFI 質問の送信・回答解析・スコア計算
│   ├── model_client.py      # OpenAI / HuggingFace API クライアント
│   ├── pd_game.py           # 囚人のジレンマゲームの実行
│   ├── strategies.py        # 対戦相手の戦略（TFT, GRIM, ALLC 等）
│   ├── prompt_templates.py  # BFI モード別プロンプト生成
│   ├── csv_exporter.py      # 実験結果の CSV 出力
│   └── prompt_logger.py     # LLM への入出力ログ記録
├── Re_BFI/                  # BFI 再実験用スクリプト群
├── scripts/                 # ユーティリティスクリプト
├── results/                 # 実験結果（git 管理外）
└── logs/                    # 実行ログ（自動生成）
```

## セットアップ

### 1. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 2. API キーの設定

以下のいずれかで OpenAI API キーを設定してください。

```bash
# 方法 A: 環境変数
export OPENAI_API_KEY="sk-..."

# 方法 B: config.json の model_settings.api_key に記入
```

### 3. 実験設定の編集

`config.json` を編集して実験パラメータを指定します。

```json
{
    "model_settings": {
        "model_name": "gpt-3.5-turbo",
        "provider": "openai"
    },
    "bfi_settings": {
        "iterations": 2,
        "modes": ["numbers_and_language", "no_prompt"]
    },
    "pd_game_settings": {
        "iterations": 10,
        "repetitions": 3,
        "prompt_templates": ["competitive"],
        "collect_reasoning": true
    },
    "strategy_settings": {
        "strategies": ["ALLC", "ALLD", "TFT", "GRIM"]
    },
    "personality_modification_settings": {
        "target_traits": ["extraversion", "agreeableness"],
        "forced_scores": [1, 5]
    }
}
```

主な設定項目:

| セクション | キー | 説明 |
|---|---|---|
| `model_settings` | `model_name` | 使用する LLM モデル名 |
| `bfi_settings` | `iterations` | BFI 質問の繰り返し回数 |
| `bfi_settings` | `modes` | BFI プロンプトモード（`numbers_and_language`, `no_prompt` 等） |
| `pd_game_settings` | `iterations` | 1 ゲームあたりのラウンド数 |
| `pd_game_settings` | `repetitions` | 同一条件での繰り返し回数 |
| `strategy_settings` | `strategies` | 対戦相手の戦略リスト |
| `personality_modification_settings` | `target_traits` | 操作対象の Big Five 特性 |
| `personality_modification_settings` | `forced_scores` | 強制設定するスコア（1〜5） |

## 実行

```bash
python main.py
```

カスタム設定ファイルを使用する場合:

```bash
python main.py --config path/to/custom_config.json
```

## 出力

実験結果は `data/` ディレクトリ（`config.json` の `output_dir` で変更可能）に以下の構成で保存されます。

```
data/
└── 20260306_120000_BFI2_PDI10_PDR3_Mgpt35turbo/
    ├── control_BFI.json                         # ベースライン BFI スコア
    ├── BFInumbers_and_language_PDcompetitive/
    │   ├── control_pd_games.json                # コントロール条件の PD ゲーム結果
    │   ├── agreeableness_score_1_modification_experiment.json
    │   ├── agreeableness_score_5_modification_experiment.json
    │   ├── ...
    │   └── prompt_logs/                         # プロンプト入出力ログ
    ├── BFIno_prompt_PDcompetitive/
    │   └── ...
    └── prompt_logs/                             # 統合プロンプトログ
```

## 利用可能な戦略

| 名前 | 説明 |
|---|---|
| `TFT` | Tit for Tat — 相手の前回の行動を真似する |
| `STFT` | Suspicious TFT — 最初に裏切り、以降は相手を真似 |
| `GRIM` | 一度裏切られたら永遠に裏切る |
| `PAVLOV` | Win-Stay, Lose-Shift |
| `ALLC` | 常に協力 |
| `ALLD` | 常に裏切り |
| `RANDOM` | ランダム（協力確率 50%） |
| `UNFAIR_RANDOM` | ランダム（協力確率 30%） |
| `FIXED_SEQUENCE` | 固定シーケンスで行動 |
| `GRADUAL` | 段階的に報復 |
| `SOFT_MAJORITY` | 直近 3 回の多数決 |
| `HARD_MAJORITY` | 全履歴の多数決 |

### このREADMEはAIによって作成されています