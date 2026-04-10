# 既存のBFIスコアを使用する方法

## 概要

既存の実験で得られたBFIスコアを使用して、2回目のBFI測定のみを実行できます。これにより、初回BFI測定をスキップし、既存の結果と整合性を保った実験が可能です。

## 使用方法

### 方法1: 既存実験の結果ファイルを使用

既存の`control_BFI.json`ファイルからスコアを読み込みます。

#### ステップ1: 既存実験の結果を確認

```bash
# 既存実験の結果ディレクトリを確認
ls results/

# 例: results/20260128_123456_BFI5_PDI10_PDR10_Mgpt35turbo/control_BFI.json
```

#### ステップ2: 設定ファイルを編集

`config_re_bfi_existing.json`を編集：

```json
{
    "re_bfi_settings": {
        "first_bfi_iterations": 0,
        "second_bfi_iterations": 5,
        "total_experiments": 10,
        "bfi_mode": "numbers_and_language",
        
        "use_existing_scores": true,
        "existing_scores_source": "results/20260128_123456_BFI5_PDI10_PDR10_Mgpt35turbo/control_BFI.json"
    }
}
```

**注意**: `total_experiments`は1に設定してください（`control_BFI.json`には1つのスコアしか含まれていないため）

#### ステップ3: 実験を実行

```bash
python Re_BFI/main_re_bfi.py --config Re_BFI/config_re_bfi_existing.json
```

### 方法2: 設定ファイルに直接スコアを記述

複数の既存スコアを設定ファイルに直接記述できます。

#### ステップ1: 設定ファイルを編集

`config_re_bfi_direct_scores.json`を参考に編集：

```json
{
    "re_bfi_settings": {
        "use_existing_scores": true,
        "existing_scores_source": [
            {
                "openness": 3.5,
                "conscientiousness": 4.2,
                "extraversion": 2.8,
                "agreeableness": 4.0,
                "neuroticism": 3.1
            },
            {
                "openness": 4.0,
                "conscientiousness": 3.8,
                "extraversion": 3.5,
                "agreeableness": 3.7,
                "neuroticism": 2.9
            }
        ],
        "total_experiments": 2
    }
}
```

**注意**: `total_experiments`は`existing_scores_source`配列の要素数と一致させてください。

#### ステップ2: 実験を実行

```bash
python Re_BFI/main_re_bfi.py --config Re_BFI/config_re_bfi_direct_scores.json
```

## サポートされるファイル形式

### 1. control_BFI.json（既存実験の初回BFI結果）

```json
{
    "condition": "control",
    "bfi_scores": {
        "final_averages": {
            "openness": 3.5,
            "conscientiousness": 4.2,
            "extraversion": 2.8,
            "agreeableness": 4.0,
            "neuroticism": 3.1
        }
    }
}
```

→ `final_averages`が自動的に抽出されます

### 2. final_results.json（Re_BFI実験の結果）

```json
{
    "all_experiment_results": [
        {
            "experiment_id": 1,
            "first_bfi_results": {
                "final_averages": {
                    "openness": 3.5,
                    ...
                }
            }
        },
        {
            "experiment_id": 2,
            "first_bfi_results": {
                "final_averages": {
                    "openness": 4.0,
                    ...
                }
            }
        }
    ]
}
```

→ 各実験の`first_bfi_results.final_averages`が自動的に抽出されます

### 3. 直接スコア形式

```json
{
    "openness": 3.5,
    "conscientiousness": 4.2,
    "extraversion": 2.8,
    "agreeableness": 4.0,
    "neuroticism": 3.1
}
```

### 4. スコアのリスト

```json
[
    {
        "openness": 3.5,
        "conscientiousness": 4.2,
        "extraversion": 2.8,
        "agreeableness": 4.0,
        "neuroticism": 3.1
    },
    {
        "openness": 4.0,
        ...
    }
]
```

## 実験フロー

### 既存スコアを使用する場合

```
[既存スコアの読み込み]
↓
[実験ループ]
│
├─ [初回BFI測定をスキップ]
│  └─ 既存スコアを使用
│
├─ [2回目BFI測定]
│  ├─ システムプロンプト: 既存スコアを明示
│  ├─ BFI-44質問に回答
│  └─ スコア計算
│
└─ [差異計算]
   ├─ MAE
   ├─ 相関係数
   └─ RMSE
```

### 既存スコアを使用しない場合（デフォルト）

```
[実験ループ]
│
├─ [初回BFI測定]
│  ├─ システムプロンプト: なし
│  ├─ BFI-44質問に回答
│  └─ スコア計算
│
├─ [2回目BFI測定]
│  ├─ システムプロンプト: 初回スコアを明示
│  ├─ BFI-44質問に回答
│  └─ スコア計算
│
└─ [差異計算]
```

## 実践例

### 例1: 既存実験の結果を検証

```bash
# ステップ1: 既存実験のBFIスコアを特定
EXISTING_FILE="results/20260128_123456_BFI5_PDI10_PDR10_Mgpt35turbo/control_BFI.json"

# ステップ2: 設定ファイルを作成
cat > Re_BFI/my_config.json << EOF
{
    "model_settings": {
        "model_name": "gpt-3.5-turbo",
        "api_key": "",
        "temperature": 0.7
    },
    "re_bfi_settings": {
        "first_bfi_iterations": 0,
        "second_bfi_iterations": 5,
        "total_experiments": 1,
        "bfi_mode": "numbers_and_language",
        "use_existing_scores": true,
        "existing_scores_source": "$EXISTING_FILE"
    }
}
EOF

# ステップ3: 実験実行
python Re_BFI/main_re_bfi.py --config Re_BFI/my_config.json
```

### 例2: 複数の既存スコアをバッチ処理

以前のRe_BFI実験の結果を使って、さらに分析を深める：

```bash
# 既存のRe_BFI結果を使用
python Re_BFI/main_re_bfi.py --config Re_BFI/config_re_bfi_existing.json
```

`config_re_bfi_existing.json`:
```json
{
    "re_bfi_settings": {
        "use_existing_scores": true,
        "existing_scores_source": "Re_BFI/results/20260128_140000_ReBFI_gpt35turbo/final_results.json",
        "total_experiments": 10
    }
}
```

## トラブルシューティング

### エラー: "既存スコアファイルが見つかりません"

**原因**: ファイルパスが間違っているか、ファイルが存在しません。

**解決方法**:
```bash
# ファイルの存在を確認
ls results/YYYYMMDD_HHMMSS_*/control_BFI.json

# 絶対パスを使用
"existing_scores_source": "/full/path/to/control_BFI.json"
```

### エラー: "既存スコアが不足しています"

**原因**: `total_experiments`が既存スコアの数より多い。

**解決方法**:
- `total_experiments`を既存スコアの数に合わせる
- または、不足分は新規に測定される（自動的にフォールバック）

### 警告: "use_existing_scores=true ですが、existing_scores_source が指定されていません"

**原因**: `use_existing_scores`が`true`だが、ソースが指定されていない。

**解決方法**:
```json
"use_existing_scores": true,
"existing_scores_source": "path/to/file.json"
```

## 注意事項

1. **total_experimentsの設定**
   - ファイルから読み込む場合: ファイル内のスコア数に合わせる
   - 直接指定する場合: 配列の要素数に合わせる
   - 既存スコアが不足する場合は、新規測定が実行されます

2. **BFIモードの一致**
   - 既存実験と同じ`bfi_mode`を使用することを推奨
   - 異なるモードを使うと、結果の比較が困難になる可能性があります

3. **first_bfi_iterations**
   - 既存スコアを使用する場合、この設定は無視されます
   - `0`に設定することを推奨（明示的に初回測定をスキップすることを示す）

4. **APIコストの削減**
   - 既存スコアを使用すると、初回BFI測定（44問×繰り返し回数）をスキップできます
   - これにより、APIコストとトークン使用量を大幅に削減できます

## まとめ

既存のBFIスコアを使用する機能により：

✅ 既存実験の結果を活用できる
✅ 初回測定をスキップしてAPIコストを削減
✅ 既存データとの整合性を保った実験が可能
✅ 複数の既存スコアをバッチ処理できる

この機能は、既存の実験結果を検証したり、異なる条件で2回目のBFI測定のみを繰り返したりする場合に特に有用です。
