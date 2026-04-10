#!/bin/bash
# 全モデルでBFI再現性実験を実行するスクリプト

set -e  # エラーが発生したら停止

echo "========================================"
echo "BFI再現性実験 - 全モデル実行"
echo "========================================"
echo ""

# APIキーの確認
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  OPENAI_API_KEYが設定されていません"
    echo "以下のコマンドでAPIキーを設定してください："
    echo "  export OPENAI_API_KEY='your-api-key-here'"
    echo ""
    read -p "APIキーを設定してから続行しますか? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# プロジェクトルートに移動
cd "$(dirname "$0")/.."

echo "プロジェクトディレクトリ: $(pwd)"
echo ""

# 実行するモデルのリスト
MODELS=("gpt35turbo" "gpt4o" "gpt5")

# 各モデルで実験を実行
for model in "${MODELS[@]}"; do
    echo "========================================"
    echo "🚀 $model の実験を開始"
    echo "========================================"
    echo ""
    
    # 実験開始時刻を記録
    start_time=$(date +%s)
    
    # 実験実行
    if python Re_BFI/main_re_bfi.py --config Re_BFI/config_${model}.json; then
        # 実験終了時刻を記録
        end_time=$(date +%s)
        duration=$((end_time - start_time))
        minutes=$((duration / 60))
        seconds=$((duration % 60))
        
        echo ""
        echo "✅ $model の実験が完了しました"
        echo "   実行時間: ${minutes}分${seconds}秒"
        echo ""
        
        # 次のモデルの前に少し待機（APIレート制限対策）
        if [ "$model" != "${MODELS[-1]}" ]; then
            echo "次のモデルの前に60秒待機します..."
            sleep 60
        fi
    else
        echo ""
        echo "❌ $model の実験でエラーが発生しました"
        echo ""
        read -p "続行しますか? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    echo ""
done

echo "========================================"
echo "🎉 すべての実験が完了しました！"
echo "========================================"
echo ""
echo "結果の確認："
echo "  ls -la Re_BFI/results/"
echo ""
echo "分析の実行："
echo "  python Re_BFI/analyze_re_bfi.py --results Re_BFI/results/YYYYMMDD_HHMMSS_ReBFI_gpt35turbo/final_results.json"
echo "  python Re_BFI/analyze_re_bfi.py --results Re_BFI/results/YYYYMMDD_HHMMSS_ReBFI_gpt4o/final_results.json"
echo "  python Re_BFI/analyze_re_bfi.py --results Re_BFI/results/YYYYMMDD_HHMMSS_ReBFI_gpt5/final_results.json"
echo ""
