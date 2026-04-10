#!/usr/bin/env python3
"""
BFIスコア再現性実験の結果分析

【このスクリプトの役割】
- 実験結果を読み込み
- 詳細な統計分析を実施
- グラフの生成（散布図、箱ひげ図、相関図など）
- CSVファイルへのエクスポート
"""

import argparse
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, Any, List

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

# 日本語フォントの設定
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'Hiragino Sans', 'Yu Gothic', 'Meirio', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


class ReBFIAnalyzer:
    """BFIスコア再現性実験の分析クラス"""

    def __init__(self, results_file: str):
        self.results_file = Path(results_file)
        self.output_dir = self.results_file.parent
        self.results = self._load_results()

    def _load_results(self) -> Dict[str, Any]:
        """結果ファイルを読み込み"""
        if not self.results_file.exists():
            raise FileNotFoundError(f"結果ファイルが見つかりません: {self.results_file}")

        with open(self.results_file, "r") as f:
            return json.load(f)

    def create_scatter_plots(self):
        """初回スコアと2回目スコアの散布図を作成"""
        traits = ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]
        trait_names_jp = {
            "openness": "開放性 (Openness)",
            "conscientiousness": "誠実性 (Conscientiousness)",
            "extraversion": "外向性 (Extraversion)",
            "agreeableness": "協調性 (Agreeableness)",
            "neuroticism": "神経症傾向 (Neuroticism)",
        }

        fig, axes = plt.subplots(2, 3, figsize=(15, 10))
        fig.suptitle("BFIスコアの再現性: 初回測定 vs 2回目測定", fontsize=16)

        for idx, trait in enumerate(traits):
            row = idx // 3
            col = idx % 3
            ax = axes[row, col]

            # データの抽出
            first_scores = []
            second_scores = []
            for result in self.results["all_experiment_results"]:
                first_score = result["first_bfi_results"]["final_averages"][trait]
                second_score = result["second_bfi_results"]["final_averages"][trait]
                first_scores.append(first_score)
                second_scores.append(second_score)

            # 散布図をプロット
            ax.scatter(first_scores, second_scores, alpha=0.6, s=50)

            # 完全な再現性を示す対角線を追加
            min_val = min(min(first_scores), min(second_scores))
            max_val = max(max(first_scores), max(second_scores))
            ax.plot([min_val, max_val], [min_val, max_val], 'r--', label='完全な再現性')

            # 相関係数を計算して表示
            correlation = np.corrcoef(first_scores, second_scores)[0, 1]
            ax.text(
                0.05, 0.95, f'r = {correlation:.3f}',
                transform=ax.transAxes,
                verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5)
            )

            ax.set_xlabel("初回測定スコア", fontsize=10)
            ax.set_ylabel("2回目測定スコア", fontsize=10)
            ax.set_title(trait_names_jp[trait], fontsize=12)
            ax.legend()
            ax.grid(True, alpha=0.3)

        # 最後のサブプロットを削除（5つしか使わないため）
        fig.delaxes(axes[1, 2])

        # 保存
        output_file = self.output_dir / "scatter_plots.png"
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"散布図を保存しました: {output_file}")

    def create_difference_boxplot(self):
        """特性ごとの差異の箱ひげ図を作成"""
        traits = ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]
        trait_names_jp = {
            "openness": "開放性",
            "conscientiousness": "誠実性",
            "extraversion": "外向性",
            "agreeableness": "協調性",
            "neuroticism": "神経症傾向",
        }

        # データの抽出
        data = []
        for result in self.results["all_experiment_results"]:
            for trait in traits:
                abs_diff = result["score_differences"]["trait_differences"][trait]["absolute_difference"]
                data.append({
                    "特性": trait_names_jp[trait],
                    "絶対差": abs_diff
                })

        df = pd.DataFrame(data)

        # 箱ひげ図を作成
        plt.figure(figsize=(12, 6))
        sns.boxplot(data=df, x="特性", y="絶対差", palette="Set2")
        plt.title("特性ごとのBFIスコア絶対差の分布", fontsize=14)
        plt.xlabel("特性", fontsize=12)
        plt.ylabel("絶対差", fontsize=12)
        plt.grid(True, alpha=0.3, axis='y')

        # 保存
        output_file = self.output_dir / "difference_boxplot.png"
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"箱ひげ図を保存しました: {output_file}")

    def create_mae_histogram(self):
        """MAEのヒストグラムを作成"""
        maes = [r["score_differences"]["mae"] for r in self.results["all_experiment_results"]]

        plt.figure(figsize=(10, 6))
        plt.hist(maes, bins=15, edgecolor='black', alpha=0.7, color='skyblue')
        plt.axvline(np.mean(maes), color='red', linestyle='--', linewidth=2, label=f'平均: {np.mean(maes):.4f}')
        plt.title("平均絶対誤差 (MAE) の分布", fontsize=14)
        plt.xlabel("MAE", fontsize=12)
        plt.ylabel("頻度", fontsize=12)
        plt.legend()
        plt.grid(True, alpha=0.3, axis='y')

        # 保存
        output_file = self.output_dir / "mae_histogram.png"
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"MAEヒストグラムを保存しました: {output_file}")

    def create_correlation_heatmap(self):
        """特性間の相関ヒートマップを作成"""
        traits = ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]
        trait_names_jp = {
            "openness": "開放性",
            "conscientiousness": "誠実性",
            "extraversion": "外向性",
            "agreeableness": "協調性",
            "neuroticism": "神経症傾向",
        }

        # 初回測定のデータを抽出
        first_data = {trait: [] for trait in traits}
        for result in self.results["all_experiment_results"]:
            for trait in traits:
                first_data[trait].append(result["first_bfi_results"]["final_averages"][trait])

        # DataFrameを作成
        df_first = pd.DataFrame(first_data)
        df_first.columns = [trait_names_jp[t] for t in traits]

        # 相関行列を計算
        correlation_matrix = df_first.corr()

        # ヒートマップを作成
        plt.figure(figsize=(10, 8))
        sns.heatmap(
            correlation_matrix,
            annot=True,
            fmt=".3f",
            cmap="coolwarm",
            center=0,
            square=True,
            linewidths=1,
            cbar_kws={"shrink": 0.8}
        )
        plt.title("BFI特性間の相関（初回測定）", fontsize=14)

        # 保存
        output_file = self.output_dir / "correlation_heatmap.png"
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"相関ヒートマップを保存しました: {output_file}")

    def export_to_csv(self):
        """結果をCSVファイルにエクスポート"""
        traits = ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]

        # 詳細データのエクスポート
        detailed_data = []
        for result in self.results["all_experiment_results"]:
            row = {
                "experiment_id": result["experiment_id"],
                "timestamp": result["timestamp"],
            }

            # 初回と2回目のスコアを追加
            for trait in traits:
                first_score = result["first_bfi_results"]["final_averages"][trait]
                second_score = result["second_bfi_results"]["final_averages"][trait]
                diff = result["score_differences"]["trait_differences"][trait]["difference"]
                abs_diff = result["score_differences"]["trait_differences"][trait]["absolute_difference"]

                row[f"{trait}_first"] = first_score
                row[f"{trait}_second"] = second_score
                row[f"{trait}_diff"] = diff
                row[f"{trait}_abs_diff"] = abs_diff

            # 全体統計を追加
            row["mae"] = result["score_differences"]["mae"]
            row["rmse"] = result["score_differences"]["rmse"]
            row["correlation"] = result["score_differences"]["correlation"]

            detailed_data.append(row)

        df_detailed = pd.DataFrame(detailed_data)
        csv_file = self.output_dir / "detailed_results.csv"
        df_detailed.to_csv(csv_file, index=False, encoding='utf-8-sig')
        print(f"詳細結果をCSVに保存しました: {csv_file}")

        # 集約統計のエクスポート
        stats = self.results["aggregated_statistics"]
        summary_data = [
            {"指標": "MAE 平均", "値": stats["mae_mean"]},
            {"指標": "MAE 標準偏差", "値": stats["mae_std"]},
            {"指標": "MAE 最小", "値": stats["mae_min"]},
            {"指標": "MAE 最大", "値": stats["mae_max"]},
            {"指標": "相関係数 平均", "値": stats["correlation_mean"]},
            {"指標": "相関係数 標準偏差", "値": stats["correlation_std"]},
            {"指標": "相関係数 最小", "値": stats["correlation_min"]},
            {"指標": "相関係数 最大", "値": stats["correlation_max"]},
            {"指標": "RMSE 平均", "値": stats["rmse_mean"]},
            {"指標": "RMSE 標準偏差", "値": stats["rmse_std"]},
        ]

        df_summary = pd.DataFrame(summary_data)
        summary_csv_file = self.output_dir / "summary_statistics.csv"
        df_summary.to_csv(summary_csv_file, index=False, encoding='utf-8-sig')
        print(f"サマリー統計をCSVに保存しました: {summary_csv_file}")

    def run_all_analyses(self):
        """すべての分析を実行"""
        print("=" * 60)
        print("BFIスコア再現性実験の分析を開始します")
        print("=" * 60)

        print("\n1. 散布図の作成...")
        self.create_scatter_plots()

        print("\n2. 箱ひげ図の作成...")
        self.create_difference_boxplot()

        print("\n3. MAEヒストグラムの作成...")
        self.create_mae_histogram()

        print("\n4. 相関ヒートマップの作成...")
        self.create_correlation_heatmap()

        print("\n5. CSVエクスポート...")
        self.export_to_csv()

        print("\n" + "=" * 60)
        print("すべての分析が完了しました")
        print(f"出力ディレクトリ: {self.output_dir}")
        print("=" * 60)


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description="BFIスコア再現性実験の結果分析")
    parser.add_argument(
        "--results",
        type=str,
        required=True,
        help="final_results.jsonファイルのパス",
    )
    args = parser.parse_args()

    # 分析の実行
    analyzer = ReBFIAnalyzer(args.results)
    analyzer.run_all_analyses()


if __name__ == "__main__":
    main()
