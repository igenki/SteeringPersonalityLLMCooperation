#!/usr/bin/env python3
"""
BFIスコア再現性実験

【実験の流れ】
1. 初回BFI測定（ペルソナなし）- BFI-44の44問に回答
2. 測定されたスコアを明示的にプロンプトで与えて2回目のBFI測定
3. スコアの差異を計算して再現性を分析

【既存プログラムとの違い】
- 囚人のジレンマゲームは実行しない
- BFI測定のみに特化した実験
- スコアの再現性に焦点を当てた分析
"""

import argparse
import json
import os
import sys
import numpy as np
from pathlib import Path
from datetime import datetime
import logging
from typing import Dict, Any, List, Optional

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

# 既存モジュールをインポート
from src.prompt_logger import PromptLogger

# Re_BFI専用のラッパーをインポート
from Re_BFI.model_client_wrapper import ModelClientWrapper as ModelClient
from Re_BFI.bfi_analyzer_wrapper import BFIAnalyzerWrapper as BFIAnalyzer

# ログディレクトリの作成
LOG_DIR = PROJECT_ROOT / "Re_BFI" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "re_bfi_research.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class CustomJSONEncoder(json.JSONEncoder):
    """カスタムJSONエンコーダー（既存のものと同じ）"""

    def default(self, obj):
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        elif hasattr(obj, "__dict__"):
            return obj.__dict__
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return super().default(obj)


class ReBFIResearch:
    """BFIスコア再現性実験のメインクラス"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

        # タイムスタンプと実験設定を含む出力ディレクトリを作成
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_name = config.get("model_settings", {}).get("model_name", "gpt-3.5-turbo")
        model_short = self._get_model_short_name(model_name)

        # 出力ディレクトリの設定
        output_dir_setting = config.get("experiment_settings", {}).get(
            "output_dir", "Re_BFI/results"
        )
        if Path(output_dir_setting).is_absolute():
            base_output_dir = Path(output_dir_setting)
        else:
            base_output_dir = PROJECT_ROOT / output_dir_setting

        self.output_dir = base_output_dir / f"{timestamp}_ReBFI_{model_short}"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"出力ディレクトリが作成されました: {self.output_dir}")

        # プロンプトロガーの初期化
        self.prompt_logger = PromptLogger(self.output_dir)

        # 実験開始時間の記録
        self.start_time = datetime.now()

        # モデルクライアントの初期化
        api_key = config.get("model_settings", {}).get("api_key", "")
        if not api_key:
            api_key = os.getenv("OPENAI_API_KEY", "")

        self.model_client = ModelClient(
            model_name=model_name,
            api_key=api_key,
            provider=config.get("model_settings", {}).get("provider", "openai"),
            prompt_logger=self.prompt_logger,
        )

        # BFI分析器の初期化
        self.bfi_analyzer = BFIAnalyzer(self.model_client)

        # 既存スコアの読み込み（オプション）
        self.existing_scores = self._load_existing_scores()

        logger.info("実験の初期化が完了しました")

    def _get_model_short_name(self, model_name: str) -> str:
        """モデル名を短縮（出力ディレクトリ用）"""
        model_short = model_name.replace("-", "").replace(".", "").replace("_", "")
        return model_short[:10]

    def _load_existing_scores(self) -> Optional[List[Dict[str, float]]]:
        """
        既存のBFIスコアを読み込み（オプション）

        Returns:
            既存スコアのリスト、または None
        """
        re_bfi_settings = self.config.get("re_bfi_settings", {})
        use_existing = re_bfi_settings.get("use_existing_scores", False)

        if not use_existing:
            return None

        # 既存スコアファイルのパスを取得
        scores_source = re_bfi_settings.get("existing_scores_source", None)

        if scores_source is None:
            logger.warning("use_existing_scores=true ですが、existing_scores_source が指定されていません")
            return None

        # ファイルパスまたは直接スコアの判定
        if isinstance(scores_source, str):
            # ファイルパスの場合
            scores_file = Path(scores_source)
            if not scores_file.is_absolute():
                scores_file = PROJECT_ROOT / scores_source

            if not scores_file.exists():
                logger.error(f"既存スコアファイルが見つかりません: {scores_file}")
                return None

            logger.info(f"既存スコアファイルを読み込みます: {scores_file}")

            try:
                with open(scores_file, "r") as f:
                    data = json.load(f)

                # ファイル形式に応じてスコアを抽出
                scores = self._extract_scores_from_file(data)
                logger.info(f"既存スコアを {len(scores)} 件読み込みました")
                return scores

            except Exception as e:
                logger.error(f"既存スコアファイルの読み込みに失敗: {e}")
                return None

        elif isinstance(scores_source, list):
            # 設定ファイルに直接スコアが書かれている場合
            logger.info(f"設定ファイルから既存スコアを {len(scores_source)} 件読み込みました")
            return scores_source

        else:
            logger.error(f"existing_scores_source の形式が不正です: {type(scores_source)}")
            return None

    def _extract_scores_from_file(self, data: Dict[str, Any]) -> List[Dict[str, float]]:
        """
        JSONファイルからBFIスコアを抽出

        Args:
            data: JSONファイルの内容

        Returns:
            BFIスコアのリスト
        """
        scores_list = []

        # パターン1: control_BFI.json形式（既存実験の初回BFI結果）
        if "bfi_scores" in data and "final_averages" in data["bfi_scores"]:
            scores = data["bfi_scores"]["final_averages"]
            scores_list.append(scores)
            logger.info(f"control_BFI.json形式のスコアを抽出: {scores}")

        # パターン2: final_results.json形式（Re_BFI実験の結果）
        elif "all_experiment_results" in data:
            for result in data["all_experiment_results"]:
                if "first_bfi_results" in result:
                    scores = result["first_bfi_results"]["final_averages"]
                    scores_list.append(scores)
            logger.info(f"final_results.json形式から {len(scores_list)} 件のスコアを抽出")

        # パターン3: 直接final_averages形式
        elif all(key in data for key in ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]):
            scores_list.append(data)
            logger.info(f"direct形式のスコアを抽出: {data}")

        # パターン4: リスト形式
        elif isinstance(data, list):
            for item in data:
                if all(key in item for key in ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]):
                    scores_list.append(item)
            logger.info(f"リスト形式から {len(scores_list)} 件のスコアを抽出")

        else:
            logger.warning(f"サポートされていないファイル形式です。キー: {list(data.keys())[:5]}")

        return scores_list

    def run_single_experiment(
        self, experiment_id: int, bfi_mode: str, iterations_1: int, iterations_2: int
    ) -> Dict[str, Any]:
        """
        単一の再現性実験を実行

        Args:
            experiment_id: 実験ID
            bfi_mode: BFIモード
            iterations_1: 初回BFI測定の繰り返し回数
            iterations_2: 2回目のBFI測定の繰り返し回数

        Returns:
            実験結果の辞書
        """
        logger.info(f"=== 実験 {experiment_id} を開始 ===")

        # ステップ1: 初回BFI測定（既存スコアがある場合はスキップ）
        if self.existing_scores is not None and len(self.existing_scores) > 0:
            # 既存スコアを使用
            if experiment_id - 1 < len(self.existing_scores):
                first_bfi_scores = self.existing_scores[experiment_id - 1]
                logger.info(f"ステップ1: 既存スコアを使用（実験 {experiment_id}）")
                logger.info(f"既存BFIスコア: {first_bfi_scores}")
                
                # 既存スコア用の結果構造を作成
                first_bfi_results = {
                    "bfi_scores": None,
                    "iterations": [{"iteration": 1, "trait_averages": first_bfi_scores}],
                    "final_averages": first_bfi_scores,
                    "total_iterations": 0,
                    "source": "existing_scores"
                }
            else:
                logger.warning(f"既存スコアが不足しています（実験 {experiment_id} / 全 {len(self.existing_scores)} 件）")
                logger.info(f"ステップ1: 新規BFI測定を実行（{iterations_1}回繰り返し）")
                first_bfi_results = self.bfi_analyzer.get_bfi_scores(
                    bfi_scores=None, bfi_mode=bfi_mode, iterations=iterations_1
                )
                first_bfi_scores = first_bfi_results["final_averages"]
                logger.info(f"初回BFIスコア: {first_bfi_scores}")
        else:
            # 既存スコアがない場合は通常通り測定
            logger.info(f"ステップ1: 初回BFI測定（{iterations_1}回繰り返し）")
            first_bfi_results = self.bfi_analyzer.get_bfi_scores(
                bfi_scores=None, bfi_mode=bfi_mode, iterations=iterations_1
            )
            first_bfi_scores = first_bfi_results["final_averages"]
            logger.info(f"初回BFIスコア: {first_bfi_scores}")

        # ステップ2: 測定されたスコアを明示的に与えて2回目のBFI測定
        logger.info(f"ステップ2: 2回目のBFI測定（{iterations_2}回繰り返し）")
        logger.info("初回のスコアをプロンプトに明示的に含めます")

        second_bfi_results = self.bfi_analyzer.get_bfi_scores(
            bfi_scores=first_bfi_scores, bfi_mode=bfi_mode, iterations=iterations_2
        )

        second_bfi_scores = second_bfi_results["final_averages"]
        logger.info(f"2回目のBFIスコア: {second_bfi_scores}")

        # ステップ3: スコアの差異を計算
        logger.info("ステップ3: スコアの差異を計算")
        score_differences = self._calculate_score_differences(
            first_bfi_scores, second_bfi_scores
        )

        # 結果を構造化
        experiment_result = {
            "experiment_id": experiment_id,
            "timestamp": datetime.now().isoformat(),
            "bfi_mode": bfi_mode,
            "first_bfi_iterations": iterations_1,
            "second_bfi_iterations": iterations_2,
            "first_bfi_results": first_bfi_results,
            "second_bfi_results": second_bfi_results,
            "score_differences": score_differences,
        }

        logger.info(f"=== 実験 {experiment_id} が完了 ===")
        logger.info(f"平均絶対誤差 (MAE): {score_differences['mae']:.4f}")
        logger.info(f"相関係数: {score_differences['correlation']:.4f}")

        return experiment_result

    def _calculate_score_differences(
        self, first_scores: Dict[str, float], second_scores: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        2つのBFIスコア間の差異を計算

        Args:
            first_scores: 初回のBFIスコア
            second_scores: 2回目のBFIスコア

        Returns:
            差異の統計情報
        """
        traits = ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]

        differences = {}
        absolute_differences = []
        first_values = []
        second_values = []

        for trait in traits:
            first_value = first_scores[trait]
            second_value = second_scores[trait]
            diff = second_value - first_value
            abs_diff = abs(diff)

            differences[trait] = {
                "first_score": first_value,
                "second_score": second_value,
                "difference": diff,
                "absolute_difference": abs_diff,
            }

            absolute_differences.append(abs_diff)
            first_values.append(first_value)
            second_values.append(second_value)

        # 統計量の計算
        mae = np.mean(absolute_differences)  # 平均絶対誤差
        mse = np.mean([d ** 2 for d in [differences[t]["difference"] for t in traits]])  # 平均二乗誤差
        rmse = np.sqrt(mse)  # 二乗平均平方根誤差

        # 相関係数の計算
        correlation = np.corrcoef(first_values, second_values)[0, 1]

        return {
            "trait_differences": differences,
            "mae": float(mae),
            "mse": float(mse),
            "rmse": float(rmse),
            "correlation": float(correlation),
            "max_abs_difference": float(max(absolute_differences)),
            "min_abs_difference": float(min(absolute_differences)),
        }

    def run_multiple_experiments(
        self, total_experiments: int, bfi_mode: str, iterations_1: int, iterations_2: int
    ) -> Dict[str, Any]:
        """
        複数回の再現性実験を実行

        Args:
            total_experiments: 実験の総回数
            bfi_mode: BFIモード
            iterations_1: 初回BFI測定の繰り返し回数
            iterations_2: 2回目のBFI測定の繰り返し回数

        Returns:
            全実験結果の辞書
        """
        logger.info(f"=== {total_experiments}回の再現性実験を開始 ===")

        all_results = []

        for i in range(total_experiments):
            result = self.run_single_experiment(
                experiment_id=i + 1,
                bfi_mode=bfi_mode,
                iterations_1=iterations_1,
                iterations_2=iterations_2,
            )
            all_results.append(result)

            # 中間結果を保存（実験が中断された場合に備えて）
            self._save_intermediate_results(all_results, i + 1)

        # 全実験の統計を計算
        aggregated_stats = self._aggregate_experiment_results(all_results)

        # 最終結果を保存
        final_results = {
            "config": self.config,
            "total_experiments": total_experiments,
            "bfi_mode": bfi_mode,
            "first_bfi_iterations": iterations_1,
            "second_bfi_iterations": iterations_2,
            "all_experiment_results": all_results,
            "aggregated_statistics": aggregated_stats,
            "experiment_duration": str(datetime.now() - self.start_time),
        }

        self._save_final_results(final_results)

        logger.info(f"=== 全{total_experiments}回の実験が完了 ===")
        logger.info(f"平均MAE: {aggregated_stats['mae_mean']:.4f} (±{aggregated_stats['mae_std']:.4f})")
        logger.info(f"平均相関係数: {aggregated_stats['correlation_mean']:.4f} (±{aggregated_stats['correlation_std']:.4f})")

        return final_results

    def _aggregate_experiment_results(
        self, all_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        複数実験の結果を集約して統計情報を計算

        Args:
            all_results: 全実験結果のリスト

        Returns:
            集約された統計情報
        """
        traits = ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]

        # 各指標を集約
        all_maes = [r["score_differences"]["mae"] for r in all_results]
        all_correlations = [r["score_differences"]["correlation"] for r in all_results]
        all_rmses = [r["score_differences"]["rmse"] for r in all_results]

        # 特性ごとの差異を集約
        trait_differences = {trait: [] for trait in traits}
        trait_abs_differences = {trait: [] for trait in traits}

        for result in all_results:
            for trait in traits:
                diff = result["score_differences"]["trait_differences"][trait]["difference"]
                abs_diff = result["score_differences"]["trait_differences"][trait]["absolute_difference"]
                trait_differences[trait].append(diff)
                trait_abs_differences[trait].append(abs_diff)

        # 特性ごとの統計を計算
        trait_statistics = {}
        for trait in traits:
            trait_statistics[trait] = {
                "mean_difference": float(np.mean(trait_differences[trait])),
                "std_difference": float(np.std(trait_differences[trait])),
                "mean_abs_difference": float(np.mean(trait_abs_differences[trait])),
                "std_abs_difference": float(np.std(trait_abs_differences[trait])),
            }

        return {
            "mae_mean": float(np.mean(all_maes)),
            "mae_std": float(np.std(all_maes)),
            "mae_min": float(np.min(all_maes)),
            "mae_max": float(np.max(all_maes)),
            "correlation_mean": float(np.mean(all_correlations)),
            "correlation_std": float(np.std(all_correlations)),
            "correlation_min": float(np.min(all_correlations)),
            "correlation_max": float(np.max(all_correlations)),
            "rmse_mean": float(np.mean(all_rmses)),
            "rmse_std": float(np.std(all_rmses)),
            "trait_statistics": trait_statistics,
        }

    def _save_intermediate_results(
        self, all_results: List[Dict[str, Any]], current_experiment: int
    ):
        """中間結果を保存"""
        intermediate_file = self.output_dir / f"intermediate_results_exp{current_experiment}.json"
        with open(intermediate_file, "w") as f:
            json.dump(all_results, f, indent=2, cls=CustomJSONEncoder)
        logger.debug(f"中間結果を保存しました: {intermediate_file}")

    def _save_final_results(self, final_results: Dict[str, Any]):
        """最終結果を保存"""
        final_file = self.output_dir / "final_results.json"
        with open(final_file, "w") as f:
            json.dump(final_results, f, indent=2, cls=CustomJSONEncoder)
        logger.info(f"最終結果を保存しました: {final_file}")

        # サマリーファイルも作成
        summary_file = self.output_dir / "summary.txt"
        with open(summary_file, "w") as f:
            stats = final_results["aggregated_statistics"]
            f.write("=" * 60 + "\n")
            f.write("BFIスコア再現性実験 - サマリー\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"実験回数: {final_results['total_experiments']}\n")
            f.write(f"BFIモード: {final_results['bfi_mode']}\n")
            f.write(f"初回BFI繰り返し回数: {final_results['first_bfi_iterations']}\n")
            f.write(f"2回目BFI繰り返し回数: {final_results['second_bfi_iterations']}\n")
            f.write(f"実験時間: {final_results['experiment_duration']}\n\n")
            f.write("=" * 60 + "\n")
            f.write("統計結果\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"平均絶対誤差 (MAE):\n")
            f.write(f"  平均: {stats['mae_mean']:.4f}\n")
            f.write(f"  標準偏差: {stats['mae_std']:.4f}\n")
            f.write(f"  最小: {stats['mae_min']:.4f}\n")
            f.write(f"  最大: {stats['mae_max']:.4f}\n\n")
            f.write(f"相関係数:\n")
            f.write(f"  平均: {stats['correlation_mean']:.4f}\n")
            f.write(f"  標準偏差: {stats['correlation_std']:.4f}\n")
            f.write(f"  最小: {stats['correlation_min']:.4f}\n")
            f.write(f"  最大: {stats['correlation_max']:.4f}\n\n")
            f.write(f"二乗平均平方根誤差 (RMSE):\n")
            f.write(f"  平均: {stats['rmse_mean']:.4f}\n")
            f.write(f"  標準偏差: {stats['rmse_std']:.4f}\n\n")
            f.write("=" * 60 + "\n")
            f.write("特性ごとの統計\n")
            f.write("=" * 60 + "\n\n")
            for trait, trait_stats in stats["trait_statistics"].items():
                f.write(f"{trait.capitalize()}:\n")
                f.write(f"  平均差: {trait_stats['mean_difference']:.4f} (±{trait_stats['std_difference']:.4f})\n")
                f.write(f"  平均絶対差: {trait_stats['mean_abs_difference']:.4f} (±{trait_stats['std_abs_difference']:.4f})\n\n")

        logger.info(f"サマリーを保存しました: {summary_file}")


def load_config(config_path: str) -> Dict[str, Any]:
    """設定ファイルを読み込み"""
    config_file_path = Path(config_path)

    if not config_file_path.exists():
        raise FileNotFoundError(
            f"設定ファイルが見つかりません: {config_file_path}\n"
            "config_re_bfi.jsonファイルを作成するか、--configオプションで正しいパスを指定してください。"
        )

    try:
        with open(config_file_path, "r") as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"設定ファイルのJSON形式が正しくありません: {config_file_path}\n"
            f"エラー詳細: {e}"
        )

    return config


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description="BFIスコア再現性実験")
    parser.add_argument(
        "--config",
        type=str,
        default="Re_BFI/config_re_bfi.json",
        help="設定ファイルのパス",
    )
    args = parser.parse_args()

    # 設定ファイルの読み込み
    config = load_config(args.config)

    # 実験オブジェクトの初期化
    research = ReBFIResearch(config)

    # 実験設定の取得
    re_bfi_settings = config.get("re_bfi_settings", {})
    total_experiments = re_bfi_settings.get("total_experiments", 10)
    first_bfi_iterations = re_bfi_settings.get("first_bfi_iterations", 5)
    second_bfi_iterations = re_bfi_settings.get("second_bfi_iterations", 5)
    bfi_mode = re_bfi_settings.get("bfi_mode", "numbers_and_language")

    logger.info("BFIスコア再現性実験を開始します")
    logger.info(f"実験回数: {total_experiments}")
    logger.info(f"初回BFI繰り返し回数: {first_bfi_iterations}")
    logger.info(f"2回目BFI繰り返し回数: {second_bfi_iterations}")
    logger.info(f"BFIモード: {bfi_mode}")

    # 実験の実行
    results = research.run_multiple_experiments(
        total_experiments=total_experiments,
        bfi_mode=bfi_mode,
        iterations_1=first_bfi_iterations,
        iterations_2=second_bfi_iterations,
    )

    # プロンプトログの保存
    research.prompt_logger.save_logs()
    research.prompt_logger.print_summary()

    logger.info("すべての実験が正常に完了しました")


if __name__ == "__main__":
    main()
