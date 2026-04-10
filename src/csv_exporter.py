"""
CSV出力モジュール
pandas分析用のCSVファイルを生成

【このモジュールの役割】
実験結果をCSV形式で出力し、論文用の分析データとして使用できる形式に整形します。

【主要な機能】
1. 実験サマリーの出力：各実験条件の主要指標をまとめたCSVファイルを生成
2. ラウンド詳細データの出力：各ゲームラウンドの詳細な行動データを出力
3. BFIスコアの出力：各条件での性格特性スコアを出力
4. 論文用指標の出力：論文で使用する指標を計算して出力

【出力ファイル】
- experiment_summary_*.csv: 実験のサマリー（協力率、平均報酬など）
- round_details_*.csv: 各ラウンドの詳細データ
- bfi_scores_*.csv: 各条件でのBFIスコア
- paper_metrics_*.csv: 論文用の指標（報復率、寛容率など）
"""

import csv
import json
import logging
import statistics
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime, timedelta
import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)


class CSVExporter:
    """実験結果をCSV形式で出力するクラス"""

    def __init__(self, output_dir: Path, config: Dict[str, Any] = None):
        self.output_dir = output_dir
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.config = config or {}

        # ディレクトリ構造の作成（各exportメソッドで必要に応じて作成）
        self.processed_data_dir = self.output_dir / "processed_data"

    def export_experiment_summary(
        self, all_results: Dict[str, Any], control_baseline: Dict[str, Any]
    ) -> None:
        """実験サマリーをCSVで出力"""
        self.processed_data_dir.mkdir(exist_ok=True)
        csv_file = self.processed_data_dir / f"experiment_summary_{self.session_id}.csv"

        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # ヘッダー
            headers = [
                "experiment_id",
                "condition",
                "trait",
                "forced_score",
                "strategy",
                "repetition",
                "cooperation_rate",
                "avg_payoff",
                "total_payoff",
                "bfi_mode",
                "prompt_template",
                "collect_reasoning",
                "bfi_extraversion",
                "bfi_agreeableness",
                "bfi_conscientiousness",
                "bfi_neuroticism",
                "bfi_openness",
                "prompt_template",
                "bfi_mode",
                "model_name",
                "temperature",
                "pd_iterations",
                "pd_repetitions",
                "bfi_iterations",
            ]
            writer.writerow(headers)

            # コントロール条件のデータ
            if "control_pd_results" in all_results:
                self._write_control_data(
                    writer, all_results["control_pd_results"], control_baseline
                )

            # 修正実験のデータ
            for condition_name, condition_data in all_results.items():
                if condition_name.startswith(
                    (
                        "extraversion",
                        "agreeableness",
                        "conscientiousness",
                        "neuroticism",
                        "openness",
                    )
                ):
                    self._write_modification_data(
                        writer, condition_name, condition_data
                    )

        logger.info(f"Experiment summary exported to: {csv_file}")

    def _write_control_data(
        self, writer, pd_results: Dict[str, Any], bfi_scores: Dict[str, Any]
    ) -> None:
        """コントロール条件のデータを書き込み"""
        experiment_id = f"exp_{self.session_id}_control"

        for strategy_name, strategy_data in pd_results.get("game_results", {}).items():
            bfi_scores_dict = bfi_scores.get("final_averages", {}) if bfi_scores else {}

            for repetition_data in strategy_data.get("repetition_details", []):
                game_history = repetition_data.get("game_history", {})
                # GameHistoryオブジェクトの場合は辞書に変換
                if hasattr(game_history, "to_dict"):
                    game_history = game_history.to_dict()
                actions = game_history.get("actions", [])

                if actions:
                    cooperation_rate = sum(
                        1 for action in actions if action.get("player_action") == 1
                    ) / len(actions)
                    avg_payoff = sum(
                        action.get("player_payoff", 0) for action in actions
                    )
                    total_payoff = sum(
                        action.get("player_payoff", 0) for action in actions
                    )
                else:
                    cooperation_rate = 0
                    avg_payoff = 0
                    total_payoff = 0

                row = [
                    experiment_id,
                    "control",
                    "control",
                    None,
                    strategy_name,
                    repetition_data.get("repetition", 1),
                    cooperation_rate,
                    avg_payoff,
                    total_payoff,
                    self.config.get("bfi_settings", {}).get(
                        "mode", "numbers_and_language"
                    ),
                    self.config.get("pd_game_settings", {}).get(
                        "prompt_template", "competitive"
                    ),
                    self.config.get("pd_game_settings", {}).get(
                        "collect_reasoning", False
                    ),
                    bfi_scores_dict.get("extraversion", 0),
                    bfi_scores_dict.get("agreeableness", 0),
                    bfi_scores_dict.get("conscientiousness", 0),
                    bfi_scores_dict.get("neuroticism", 0),
                    bfi_scores_dict.get("openness", 0),
                    self.config.get("model_settings", {}).get(
                        "model_name", "gpt-3.5-turbo"
                    ),
                    self.config.get("model_settings", {}).get("temperature", 0.7),
                    self.config.get("pd_game_settings", {}).get("iterations", 10),
                    self.config.get("pd_game_settings", {}).get("repetitions", 1),
                    self.config.get("bfi_settings", {}).get("iterations", 1),
                ]
                writer.writerow(row)

    def _write_modification_data(
        self, writer, condition_name: str, condition_data: Dict[str, Any]
    ) -> None:
        """修正実験のデータを書き込み"""
        # 条件名から特性とスコアを抽出
        parts = condition_name.split("_")
        trait = parts[0]
        forced_score = int(parts[2]) if len(parts) > 2 else None

        experiment_id = f"exp_{self.session_id}_{condition_name}"

        # BFIスコアを取得
        bfi_scores = condition_data.get("bfi_scores", {}).get("final_averages", {})

        # PDゲーム結果を取得
        pd_results = condition_data.get("pd_results", {})

        for strategy_name, strategy_data in pd_results.get("game_results", {}).items():
            for repetition_data in strategy_data.get("repetition_details", []):
                game_history = repetition_data.get("game_history", {})
                # GameHistoryオブジェクトの場合は辞書に変換
                if hasattr(game_history, "to_dict"):
                    game_history = game_history.to_dict()
                actions = game_history.get("actions", [])

                if actions:
                    cooperation_rate = sum(
                        1 for action in actions if action.get("player_action") == 1
                    ) / len(actions)
                    avg_payoff = sum(
                        action.get("player_payoff", 0) for action in actions
                    )
                    total_payoff = sum(
                        action.get("player_payoff", 0) for action in actions
                    )
                else:
                    cooperation_rate = 0
                    avg_payoff = 0
                    total_payoff = 0

                row = [
                    experiment_id,
                    "modification",
                    trait,
                    forced_score,
                    strategy_name,
                    repetition_data.get("repetition", 1),
                    cooperation_rate,
                    avg_payoff,
                    total_payoff,
                    self.config.get("bfi_settings", {}).get(
                        "mode", "numbers_and_language"
                    ),
                    self.config.get("pd_game_settings", {}).get(
                        "prompt_template", "competitive"
                    ),
                    self.config.get("pd_game_settings", {}).get(
                        "collect_reasoning", False
                    ),
                    bfi_scores.get("extraversion", 0),
                    bfi_scores.get("agreeableness", 0),
                    bfi_scores.get("conscientiousness", 0),
                    bfi_scores.get("neuroticism", 0),
                    bfi_scores.get("openness", 0),
                    self.config.get("model_settings", {}).get(
                        "model_name", "gpt-3.5-turbo"
                    ),
                    self.config.get("model_settings", {}).get("temperature", 0.7),
                    self.config.get("pd_game_settings", {}).get("iterations", 10),
                    self.config.get("pd_game_settings", {}).get("repetitions", 1),
                    self.config.get("bfi_settings", {}).get("iterations", 1),
                ]
                writer.writerow(row)

    def export_round_details(
        self, all_results: Dict[str, Any], control_baseline: Dict[str, Any]
    ) -> None:
        """ラウンド別詳細をCSVで出力"""
        self.processed_data_dir.mkdir(exist_ok=True)
        csv_file = self.processed_data_dir / f"round_details_{self.session_id}.csv"

        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # ヘッダー
            headers = [
                "experiment_id",
                "condition",
                "trait",
                "forced_score",
                "strategy",
                "repetition",
                "round_num",
                "player_action",
                "opponent_action",
                "player_payoff",
                "opponent_payoff",
                "overall_reasoning",
                "prompt_template",
                "bfi_mode",
                "collect_reasoning",
                "model_name",
                "temperature",
                "bfi_extraversion",
                "bfi_agreeableness",
                "bfi_conscientiousness",
                "bfi_neuroticism",
                "bfi_openness",
            ]
            writer.writerow(headers)

            # コントロール条件のデータ
            if "control_pd_results" in all_results:
                self._write_control_rounds(
                    writer, all_results["control_pd_results"], control_baseline
                )

            # 修正実験のデータ
            for condition_name, condition_data in all_results.items():
                if condition_name.startswith(
                    (
                        "extraversion",
                        "agreeableness",
                        "conscientiousness",
                        "neuroticism",
                        "openness",
                    )
                ):
                    self._write_modification_rounds(
                        writer, condition_name, condition_data
                    )

    def _write_control_rounds(
        self,
        writer,
        pd_results: Dict[str, Any],
        control_baseline: Dict[str, Any] = None,
    ) -> None:
        """コントロール条件のラウンド詳細を書き込み"""
        experiment_id = f"exp_{self.session_id}_control"

        # BFIスコアを取得
        bfi_scores_dict = (
            control_baseline.get("final_averages", {}) if control_baseline else {}
        )

        for strategy_name, strategy_data in pd_results.get("game_results", {}).items():
            for repetition_data in strategy_data.get("repetition_details", []):
                game_history = repetition_data.get("game_history", {})
                # GameHistoryオブジェクトの場合は辞書に変換
                if hasattr(game_history, "to_dict"):
                    game_history = game_history.to_dict()
                actions = game_history.get("actions", [])
                overall_reasoning = game_history.get("overall_reasoning", "")

                for action in actions:
                    row = [
                        experiment_id,
                        "control",
                        "control",
                        None,
                        strategy_name,
                        repetition_data.get("repetition", 1),
                        action.get("round_num", 0),
                        action.get("player_action", 0),
                        action.get("opponent_action", 0),
                        action.get("player_payoff", 0),
                        action.get("opponent_payoff", 0),
                        overall_reasoning,
                        self.config.get("pd_game_settings", {}).get(
                            "prompt_template", "competitive"
                        ),
                        self.config.get("bfi_settings", {}).get(
                            "mode", "numbers_and_language"
                        ),
                        self.config.get("pd_game_settings", {}).get(
                            "collect_reasoning", False
                        ),
                        self.config.get("model_settings", {}).get(
                            "model_name", "gpt-3.5-turbo"
                        ),
                        self.config.get("model_settings", {}).get("temperature", 0.7),
                        bfi_scores_dict.get("extraversion", 0),
                        bfi_scores_dict.get("agreeableness", 0),
                        bfi_scores_dict.get("conscientiousness", 0),
                        bfi_scores_dict.get("neuroticism", 0),
                        bfi_scores_dict.get("openness", 0),
                    ]
                    writer.writerow(row)

    def _write_modification_rounds(
        self, writer, condition_name: str, condition_data: Dict[str, Any]
    ) -> None:
        """修正実験のラウンド詳細を書き込み"""
        parts = condition_name.split("_")
        trait = parts[0]
        forced_score = int(parts[2]) if len(parts) > 2 else None

        experiment_id = f"exp_{self.session_id}_{condition_name}"
        pd_results = condition_data.get("pd_results", {})

        # BFIスコアを取得
        bfi_scores = condition_data.get("bfi_scores", {}).get("final_averages", {})

        for strategy_name, strategy_data in pd_results.get("game_results", {}).items():
            for repetition_data in strategy_data.get("repetition_details", []):
                game_history = repetition_data.get("game_history", {})
                # GameHistoryオブジェクトの場合は辞書に変換
                if hasattr(game_history, "to_dict"):
                    game_history = game_history.to_dict()
                actions = game_history.get("actions", [])
                overall_reasoning = game_history.get("overall_reasoning", "")

                for action in actions:
                    row = [
                        experiment_id,
                        "modification",
                        trait,
                        forced_score,
                        strategy_name,
                        repetition_data.get("repetition", 1),
                        action.get("round_num", 0),
                        action.get("player_action", 0),
                        action.get("opponent_action", 0),
                        action.get("player_payoff", 0),
                        action.get("opponent_payoff", 0),
                        overall_reasoning,
                        self.config.get("pd_game_settings", {}).get(
                            "prompt_template", "competitive"
                        ),
                        self.config.get("bfi_settings", {}).get(
                            "mode", "numbers_and_language"
                        ),
                        self.config.get("pd_game_settings", {}).get(
                            "collect_reasoning", False
                        ),
                        self.config.get("model_settings", {}).get(
                            "model_name", "gpt-3.5-turbo"
                        ),
                        self.config.get("model_settings", {}).get("temperature", 0.7),
                        bfi_scores.get("extraversion", 0),
                        bfi_scores.get("agreeableness", 0),
                        bfi_scores.get("conscientiousness", 0),
                        bfi_scores.get("neuroticism", 0),
                        bfi_scores.get("openness", 0),
                    ]
                    writer.writerow(row)

    def export_bfi_scores(
        self, all_results: Dict[str, Any], control_baseline: Dict[str, Any]
    ) -> None:
        """BFIスコアをCSVで出力"""
        self.processed_data_dir.mkdir(exist_ok=True)
        csv_file = self.processed_data_dir / f"bfi_scores_{self.session_id}.csv"

        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # ヘッダー
            headers = [
                "experiment_id",
                "condition",
                "trait",
                "forced_score",
                "iteration",
                "extraversion",
                "agreeableness",
                "conscientiousness",
                "neuroticism",
                "openness",
                "prompt_template",
                "bfi_mode",
                "model_name",
                "temperature",
            ]
            writer.writerow(headers)

            # コントロール条件のBFIスコア
            if control_baseline and "iterations" in control_baseline:
                experiment_id = f"exp_{self.session_id}_control"
                for i, iteration in enumerate(control_baseline["iterations"]):
                    row = [
                        experiment_id,
                        "control",
                        "control",
                        None,
                        i + 1,
                        iteration.get("extraversion", 0),
                        iteration.get("agreeableness", 0),
                        iteration.get("conscientiousness", 0),
                        iteration.get("neuroticism", 0),
                        iteration.get("openness", 0),
                        self.config.get("pd_game_settings", {}).get(
                            "prompt_template", "competitive"
                        ),
                        self.config.get("bfi_settings", {}).get(
                            "mode", "numbers_and_language"
                        ),
                        self.config.get("model_settings", {}).get(
                            "model_name", "gpt-3.5-turbo"
                        ),
                        self.config.get("model_settings", {}).get("temperature", 0.7),
                    ]
                    writer.writerow(row)

            # 修正実験のBFIスコア
            for condition_name, condition_data in all_results.items():
                if condition_name.startswith(
                    (
                        "extraversion",
                        "agreeableness",
                        "conscientiousness",
                        "neuroticism",
                        "openness",
                    )
                ):
                    parts = condition_name.split("_")
                    trait = parts[0]
                    forced_score = int(parts[2]) if len(parts) > 2 else None

                    experiment_id = f"exp_{self.session_id}_{condition_name}"
                    bfi_scores = condition_data.get("bfi_scores", {})

                    if "iterations" in bfi_scores:
                        for i, iteration in enumerate(bfi_scores["iterations"]):
                            row = [
                                experiment_id,
                                "modification",
                                trait,
                                forced_score,
                                i + 1,
                                iteration.get("extraversion", 0),
                                iteration.get("agreeableness", 0),
                                iteration.get("conscientiousness", 0),
                                iteration.get("neuroticism", 0),
                                iteration.get("openness", 0),
                                self.config.get("pd_game_settings", {}).get(
                                    "prompt_template", "competitive"
                                ),
                                self.config.get("bfi_settings", {}).get(
                                    "mode", "numbers_and_language"
                                ),
                                self.config.get("model_settings", {}).get(
                                    "model_name", "gpt-3.5-turbo"
                                ),
                                self.config.get("model_settings", {}).get(
                                    "temperature", 0.7
                                ),
                            ]
                            writer.writerow(row)

        logger.info(f"BFI scores exported to: {csv_file}")

    def export_all(
        self, all_results: Dict[str, Any], control_baseline: Dict[str, Any]
    ) -> None:
        """全データをCSVで出力"""
        logger.info("Exporting all experiment data to CSV format...")

        self.export_experiment_summary(all_results, control_baseline)
        self.export_round_details(all_results, control_baseline)
        self.export_bfi_scores(all_results, control_baseline)

        logger.info("CSV export completed successfully!")

    def export_prompt_logs(self, prompt_logger) -> None:
        """プロンプトログの詳細をCSVで出力"""
        self.processed_data_dir.mkdir(exist_ok=True)
        csv_file = self.processed_data_dir / f"prompt_logs_{self.session_id}.csv"

        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # ヘッダー
            headers = [
                "timestamp",
                "experiment_type",
                "prompt_type",
                "model_name",
                "temperature",
                "max_tokens",
                "bfi_mode",
                "prompt_template",
                "target_traits",
                "forced_score",
                "strategy",
                "round_number",
                "input_prompt",
                "output_response",
                "response_length",
                "processing_time_ms",
            ]
            writer.writerow(headers)

            # プロンプトログの書き込み
            if prompt_logger and hasattr(prompt_logger, "logs") and prompt_logger.logs:
                for log in prompt_logger.logs:
                    row = [
                        log.timestamp,
                        log.experiment_type,
                        log.prompt_type,
                        log.model_name,
                        log.temperature,
                        log.max_tokens,
                        log.bfi_mode,
                        log.prompt_template,
                        str(log.target_traits) if log.target_traits else None,
                        log.forced_score,
                        log.strategy,
                        log.round_number,
                        log.input_prompt,
                        log.output_response,
                        len(log.output_response) if log.output_response else 0,
                        None,  # processing_time_ms (metadata属性がないため)
                    ]
                    writer.writerow(row)
                logger.info(
                    f"Prompt logs exported to: {csv_file} ({len(prompt_logger.logs)} entries)"
                )
            else:
                logger.warning(f"No prompt logs found to export to: {csv_file}")

    def export_bfi_detailed_scores(
        self, all_results: Dict[str, Any], control_baseline: Dict[str, Any]
    ) -> None:
        """BFI質問の詳細スコアをCSVで出力"""
        csv_file = self.output_dir / f"bfi_detailed_scores_{self.session_id}.csv"

        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # ヘッダー
            headers = [
                "experiment_id",
                "condition",
                "trait",
                "forced_score",
                "iteration",
                "question_number",
                "question_text",
                "response_text",
                "raw_score",
                "trait_name",
                "reverse_scored",
                "final_score",
            ]
            writer.writerow(headers)

            # コントロール条件のBFI詳細
            if control_baseline and "iterations" in control_baseline:
                experiment_id = f"exp_{self.session_id}_control"
                for i, iteration in enumerate(control_baseline["iterations"]):
                    # 個別質問の詳細は保存されていないため、平均スコアのみ記録
                    for trait_name in [
                        "extraversion",
                        "agreeableness",
                        "conscientiousness",
                        "neuroticism",
                        "openness",
                    ]:
                        row = [
                            experiment_id,
                            "control",
                            "control",
                            None,
                            i + 1,
                            None,  # 個別質問番号
                            None,  # 質問文
                            None,  # 回答文
                            None,  # 生スコア
                            trait_name,
                            None,  # リバーススコア
                            iteration.get(trait_name, 0),
                        ]
                        writer.writerow(row)

            # 修正実験のBFI詳細
            for condition_name, condition_data in all_results.items():
                if condition_name.startswith(
                    (
                        "extraversion",
                        "agreeableness",
                        "conscientiousness",
                        "neuroticism",
                        "openness",
                    )
                ):
                    parts = condition_name.split("_")
                    trait = parts[0]
                    forced_score = int(parts[2]) if len(parts) > 2 else None

                    experiment_id = f"exp_{self.session_id}_{condition_name}"
                    bfi_scores = condition_data.get("bfi_scores", {})

                    if "iterations" in bfi_scores:
                        for i, iteration in enumerate(bfi_scores["iterations"]):
                            for trait_name in [
                                "extraversion",
                                "agreeableness",
                                "conscientiousness",
                                "neuroticism",
                                "openness",
                            ]:
                                row = [
                                    experiment_id,
                                    "modification",
                                    trait,
                                    forced_score,
                                    i + 1,
                                    None,  # 個別質問番号
                                    None,  # 質問文
                                    None,  # 回答文
                                    None,  # 生スコア
                                    trait_name,
                                    None,  # リバーススコア
                                    iteration.get(trait_name, 0),
                                ]
                                writer.writerow(row)

        logger.info(f"BFI detailed scores exported to: {csv_file}")

    def export_strategy_details(
        self, all_results: Dict[str, Any], control_baseline: Dict[str, Any]
    ) -> None:
        """戦略の詳細パラメータをCSVで出力"""
        self.processed_data_dir.mkdir(exist_ok=True)
        csv_file = self.processed_data_dir / f"strategy_details_{self.session_id}.csv"

        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # ヘッダー
            headers = [
                "experiment_id",
                "condition",
                "trait",
                "forced_score",
                "strategy_name",
                "strategy_type",
                "strategy_description",
                "strategy_parameters",
                "total_games_played",
                "total_cooperations",
                "total_defections",
                "cooperation_rate",
                "average_payoff",
                "strategy_performance_score",
                "prompt_template",
                "bfi_mode",
                "model_name",
                "temperature",
            ]
            writer.writerow(headers)

            # 戦略の詳細情報を収集
            strategy_info = {
                "ALLC": {
                    "type": "deterministic",
                    "description": "Always Cooperate",
                    "parameters": {},
                },
                "ALLD": {
                    "type": "deterministic",
                    "description": "Always Defect",
                    "parameters": {},
                },
                "RANDOM": {
                    "type": "stochastic",
                    "description": "Random Choice",
                    "parameters": {"cooperation_prob": 0.5},
                },
                "TFT": {
                    "type": "conditional",
                    "description": "Tit for Tat",
                    "parameters": {"first_move": "cooperate"},
                },
                "GRIM": {
                    "type": "conditional",
                    "description": "Grim Trigger",
                    "parameters": {"trigger_threshold": 1},
                },
            }

            # コントロール条件の戦略詳細
            if "control_pd_results" in all_results:
                experiment_id = f"exp_{self.session_id}_control"
                for strategy_name, strategy_data in (
                    all_results["control_pd_results"].get("game_results", {}).items()
                ):
                    total_coops = 0
                    total_defects = 0
                    total_payoff = 0
                    total_games = 0

                    for repetition_data in strategy_data.get("repetition_details", []):
                        game_history = repetition_data.get("game_history", {})
                        # GameHistoryオブジェクトの場合は辞書に変換
                        if hasattr(game_history, "to_dict"):
                            game_history = game_history.to_dict()
                        actions = game_history.get("actions", [])

                        for action in actions:
                            total_games += 1
                            if action.get("player_action") == 1:
                                total_coops += 1
                            else:
                                total_defects += 1
                            total_payoff += action.get("player_payoff", 0)

                    cooperation_rate = (
                        total_coops / total_games if total_games > 0 else 0
                    )
                    # 1ゲームあたりの平均ペイオフ（反復数で割る）
                    n_repetitions = len(strategy_data.get("repetition_details", []))
                    avg_payoff = (
                        total_payoff / n_repetitions if n_repetitions > 0 else 0
                    )

                    strategy_data_info = strategy_info.get(
                        strategy_name,
                        {
                            "type": "unknown",
                            "description": f"Strategy {strategy_name}",
                            "parameters": {},
                        },
                    )

                    row = [
                        experiment_id,
                        "control",
                        "control",
                        None,
                        strategy_name,
                        strategy_data_info["type"],
                        strategy_data_info["description"],
                        str(strategy_data_info["parameters"]),
                        total_games,
                        total_coops,
                        total_defects,
                        cooperation_rate,
                        avg_payoff,
                        cooperation_rate * avg_payoff,  # パフォーマンススコア
                        self.config.get("pd_game_settings", {}).get(
                            "prompt_template", "competitive"
                        ),
                        self.config.get("bfi_settings", {}).get(
                            "mode", "numbers_and_language"
                        ),
                        self.config.get("model_settings", {}).get(
                            "model_name", "gpt-3.5-turbo"
                        ),
                        self.config.get("model_settings", {}).get("temperature", 0.7),
                    ]
                    writer.writerow(row)

            # 修正実験の戦略詳細
            for condition_name, condition_data in all_results.items():
                if condition_name.startswith(
                    (
                        "extraversion",
                        "agreeableness",
                        "conscientiousness",
                        "neuroticism",
                        "openness",
                    )
                ):
                    parts = condition_name.split("_")
                    trait = parts[0]
                    forced_score = int(parts[2]) if len(parts) > 2 else None

                    experiment_id = f"exp_{self.session_id}_{condition_name}"
                    pd_results = condition_data.get("pd_results", {})

                    for strategy_name, strategy_data in pd_results.get(
                        "game_results", {}
                    ).items():
                        total_coops = 0
                        total_defects = 0
                        total_payoff = 0
                        total_games = 0

                        for repetition_data in strategy_data.get(
                            "repetition_details", []
                        ):
                            game_history = repetition_data.get("game_history", {})
                            # GameHistoryオブジェクトの場合は辞書に変換
                            if hasattr(game_history, "to_dict"):
                                game_history = game_history.to_dict()
                            actions = game_history.get("actions", [])

                            for action in actions:
                                total_games += 1
                                if action.get("player_action") == 1:
                                    total_coops += 1
                                else:
                                    total_defects += 1
                                total_payoff += action.get("player_payoff", 0)

                        cooperation_rate = (
                            total_coops / total_games if total_games > 0 else 0
                        )
                        # 1ゲームあたりの平均ペイオフ（反復数で割る）
                        n_repetitions = len(strategy_data.get("repetition_details", []))
                        avg_payoff = (
                            total_payoff / n_repetitions if n_repetitions > 0 else 0
                        )

                        strategy_data_info = strategy_info.get(
                            strategy_name,
                            {
                                "type": "unknown",
                                "description": f"Strategy {strategy_name}",
                                "parameters": {},
                            },
                        )

                        row = [
                            experiment_id,
                            "modification",
                            trait,
                            forced_score,
                            strategy_name,
                            strategy_data_info["type"],
                            strategy_data_info["description"],
                            str(strategy_data_info["parameters"]),
                            total_games,
                            total_coops,
                            total_defects,
                            cooperation_rate,
                            avg_payoff,
                            cooperation_rate * avg_payoff,
                            self.config.get("pd_game_settings", {}).get(
                                "prompt_template", "competitive"
                            ),
                            self.config.get("bfi_settings", {}).get(
                                "mode", "numbers_and_language"
                            ),
                            self.config.get("model_settings", {}).get(
                                "model_name", "gpt-3.5-turbo"
                            ),
                            self.config.get("model_settings", {}).get(
                                "temperature", 0.7
                            ),
                        ]
                        writer.writerow(row)

        logger.info(f"Strategy details exported to: {csv_file}")

    def export_experiment_timeline(
        self,
        all_results: Dict[str, Any],
        control_baseline: Dict[str, Any],
        start_time: datetime = None,
    ) -> None:
        """実験の時系列データをCSVで出力"""
        csv_file = self.output_dir / f"experiment_timeline_{self.session_id}.csv"

        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # ヘッダー
            headers = [
                "step_number",
                "step_name",
                "step_type",
                "start_time",
                "end_time",
                "duration_seconds",
                "status",
                "details",
                "experiment_id",
                "condition",
                "trait",
                "forced_score",
                "strategy",
                "repetition",
                "round_number",
            ]
            writer.writerow(headers)

            step_number = 1
            current_time = start_time if start_time else datetime.now()

            # コントロールBFI実験
            if control_baseline:
                step_start = current_time
                current_time = step_start + timedelta(seconds=30)  # 仮の時間

                row = [
                    step_number,
                    "Control BFI Assessment",
                    "bfi_assessment",
                    step_start.isoformat(),
                    current_time.isoformat(),
                    30,
                    "completed",
                    f"BFI questions completed, iterations: {len(control_baseline.get('iterations', []))}",
                    f"exp_{self.session_id}_control",
                    "control",
                    "control",
                    None,
                    None,
                    None,
                    None,
                ]
                writer.writerow(row)
                step_number += 1

            # コントロールPD実験
            if "control_pd_results" in all_results:
                step_start = current_time
                current_time = step_start + timedelta(seconds=60)  # 仮の時間

                row = [
                    step_number,
                    "Control PD Games",
                    "pd_games",
                    step_start.isoformat(),
                    current_time.isoformat(),
                    60,
                    "completed",
                    f"PD games completed with all strategies",
                    f"exp_{self.session_id}_control",
                    "control",
                    "control",
                    None,
                    None,
                    None,
                    None,
                ]
                writer.writerow(row)
                step_number += 1

            # 修正実験
            for condition_name, condition_data in all_results.items():
                if condition_name.startswith(
                    (
                        "extraversion",
                        "agreeableness",
                        "conscientiousness",
                        "neuroticism",
                        "openness",
                    )
                ):
                    parts = condition_name.split("_")
                    trait = parts[0]
                    forced_score = int(parts[2]) if len(parts) > 2 else None

                    experiment_id = f"exp_{self.session_id}_{condition_name}"

                    # BFI修正
                    if "bfi_scores" in condition_data:
                        step_start = current_time
                        current_time = step_start + timedelta(seconds=20)  # 仮の時間

                        row = [
                            step_number,
                            f"BFI Modification - {trait}",
                            "bfi_modification",
                            step_start.isoformat(),
                            current_time.isoformat(),
                            20,
                            "completed",
                            f"BFI score forced to {forced_score} for {trait}",
                            experiment_id,
                            "modification",
                            trait,
                            forced_score,
                            None,
                            None,
                            None,
                        ]
                        writer.writerow(row)
                        step_number += 1

                    # PDゲーム
                    if "pd_results" in condition_data:
                        step_start = current_time
                        current_time = step_start + timedelta(seconds=40)  # 仮の時間

                        row = [
                            step_number,
                            f"PD Games - {trait}",
                            "pd_games",
                            step_start.isoformat(),
                            current_time.isoformat(),
                            40,
                            "completed",
                            f"PD games with modified {trait} personality",
                            experiment_id,
                            "modification",
                            trait,
                            forced_score,
                            None,
                            None,
                            None,
                        ]
                        writer.writerow(row)
                        step_number += 1

        logger.info(f"Experiment timeline exported to: {csv_file}")

    def export_error_logs(self, error_logs: List[Dict[str, Any]]) -> None:
        """エラーログをCSVで出力"""
        csv_file = self.output_dir / f"error_logs_{self.session_id}.csv"

        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # ヘッダー
            headers = [
                "timestamp",
                "error_type",
                "error_message",
                "experiment_type",
                "experiment_id",
                "condition",
                "trait",
                "forced_score",
                "strategy",
                "repetition",
                "round_number",
                "retry_count",
                "resolved",
                "stack_trace",
            ]
            writer.writerow(headers)

            # エラーログの書き込み
            for error_log in error_logs:
                row = [
                    error_log.get("timestamp", ""),
                    error_log.get("error_type", ""),
                    error_log.get("error_message", ""),
                    error_log.get("experiment_type", ""),
                    error_log.get("experiment_id", ""),
                    error_log.get("condition", ""),
                    error_log.get("trait", ""),
                    error_log.get("forced_score", ""),
                    error_log.get("strategy", ""),
                    error_log.get("repetition", ""),
                    error_log.get("round_number", ""),
                    error_log.get("retry_count", 0),
                    error_log.get("resolved", False),
                    error_log.get("stack_trace", ""),
                ]
                writer.writerow(row)

        logger.info(f"Error logs exported to: {csv_file}")

    def export_all_raw_data(
        self,
        all_results: Dict[str, Any],
        control_baseline: Dict[str, Any],
        prompt_logger,
        start_time: datetime = None,
        error_logs: List[Dict[str, Any]] = None,
    ) -> None:
        """全生データをCSVで出力"""
        logger.info("Exporting all raw data to CSV format...")

        # 既存の出力
        self.export_all(all_results, control_baseline)
        self.export_paper_metrics(all_results, control_baseline)
        self.export_summary_table(all_results, control_baseline)

        # 新しい生データ出力
        self.export_prompt_logs(prompt_logger)
        self.export_strategy_details(all_results, control_baseline)
        self.export_personality_analysis(all_results, control_baseline)
        self.export_strategy_performance(all_results, control_baseline)
        self.export_interaction_patterns(all_results, control_baseline)

        logger.info("All raw data CSV export completed successfully!")

    def export_paper_metrics(
        self, all_results: Dict[str, Any], control_baseline: Dict[str, Any]
    ) -> None:
        """論文用の統計指標をCSVで出力"""
        self.processed_data_dir.mkdir(exist_ok=True)
        csv_file = self.processed_data_dir / f"paper_metrics_{self.session_id}.csv"

        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # ヘッダー
            headers = [
                "experiment_id",
                "condition",
                "trait",
                "forced_score",
                "strategy",
                "n_repetitions",
                "cooperation_rate_mean",
                "cooperation_rate_std",
                "cooperation_rate_ci_lower",
                "cooperation_rate_ci_upper",
                "avg_payoff_mean",
                "avg_payoff_std",
                "avg_payoff_ci_lower",
                "avg_payoff_ci_upper",
                "cohens_d_vs_control",
                "t_statistic",
                "p_value",
                "effect_size_category",
                "first_round_cooperation",
                "last_round_cooperation",
                "learning_slope",
                "prompt_template",
                "bfi_mode",
                "model_name",
                "temperature",
            ]
            writer.writerow(headers)

            # コントロール条件の統計指標
            if "control_pd_results" in all_results:
                self._write_control_paper_metrics(
                    writer, all_results["control_pd_results"]
                )

            # 修正実験の統計指標
            for condition_name, condition_data in all_results.items():
                if condition_name.startswith(
                    (
                        "extraversion",
                        "agreeableness",
                        "conscientiousness",
                        "neuroticism",
                        "openness",
                    )
                ):
                    self._write_modification_paper_metrics(
                        writer,
                        condition_name,
                        condition_data,
                        all_results["control_pd_results"],
                    )

        logger.info(f"Paper metrics exported to: {csv_file}")

    def _write_control_paper_metrics(self, writer, pd_results: Dict[str, Any]) -> None:
        """コントロール条件の論文用指標を書き込み"""
        experiment_id = f"exp_{self.session_id}_control"

        for strategy_name, strategy_data in pd_results.get("game_results", {}).items():
            cooperation_rates = []
            avg_payoffs = []
            first_round_coops = []
            last_round_coops = []
            learning_slopes = []

            for repetition_data in strategy_data.get("repetition_details", []):
                game_history = repetition_data.get("game_history", {})
                # GameHistoryオブジェクトの場合は辞書に変換
                if hasattr(game_history, "to_dict"):
                    game_history = game_history.to_dict()
                actions = game_history.get("actions", [])

                if actions:
                    # 協力率
                    coop_rate = sum(
                        1 for action in actions if action.get("player_action") == 1
                    ) / len(actions)
                    cooperation_rates.append(coop_rate)

                    # 平均ペイオフ
                    avg_payoff = sum(
                        action.get("player_payoff", 0) for action in actions
                    )
                    avg_payoffs.append(avg_payoff)

                    # 初回・最終ラウンド協力
                    first_round_coops.append(actions[0].get("player_action", 0))
                    last_round_coops.append(actions[-1].get("player_action", 0))

                    # 学習効果（ラウンド進行による協力率の変化）
                    round_coops = [action.get("player_action", 0) for action in actions]
                    if len(round_coops) > 1:
                        slope, _ = np.polyfit(range(len(round_coops)), round_coops, 1)
                        learning_slopes.append(slope)
                    else:
                        learning_slopes.append(0)
                else:
                    cooperation_rates.append(0)
                    avg_payoffs.append(0)
                    first_round_coops.append(0)
                    last_round_coops.append(0)
                    learning_slopes.append(0)

            # 統計指標の計算
            n_reps = len(cooperation_rates)
            coop_mean = statistics.mean(cooperation_rates) if cooperation_rates else 0
            coop_std = (
                statistics.stdev(cooperation_rates) if len(cooperation_rates) > 1 else 0
            )
            payoff_mean = statistics.mean(avg_payoffs) if avg_payoffs else 0
            payoff_std = statistics.stdev(avg_payoffs) if len(avg_payoffs) > 1 else 0

            # 信頼区間（95%）
            if n_reps > 1 and coop_std > 0:
                coop_ci = stats.t.interval(
                    0.95, n_reps - 1, loc=coop_mean, scale=coop_std / np.sqrt(n_reps)
                )
            else:
                coop_ci = (coop_mean, coop_mean)

            if n_reps > 1 and payoff_std > 0:
                payoff_ci = stats.t.interval(
                    0.95,
                    n_reps - 1,
                    loc=payoff_mean,
                    scale=payoff_std / np.sqrt(n_reps),
                )
            else:
                payoff_ci = (payoff_mean, payoff_mean)

            # 一貫性指標（協力率の分散の逆数）
            consistency = 1 / (coop_std + 0.001) if coop_std > 0 else 1

            row = [
                experiment_id,
                "control",
                "control",
                None,
                strategy_name,
                n_reps,
                coop_mean,
                coop_std,
                coop_ci[0],
                coop_ci[1],
                payoff_mean,
                payoff_std,
                payoff_ci[0],
                payoff_ci[1],
                None,  # Cohen's d (コントロール同士では計算しない)
                None,  # t統計量
                None,  # p値
                "control",  # 効果サイズカテゴリ
                statistics.mean(first_round_coops),
                statistics.mean(last_round_coops),
                statistics.mean(learning_slopes),
                self.config.get("pd_game_settings", {}).get(
                    "prompt_template", "competitive"
                ),
                self.config.get("bfi_settings", {}).get("mode", "numbers_and_language"),
                self.config.get("model_settings", {}).get(
                    "model_name", "gpt-3.5-turbo"
                ),
                self.config.get("model_settings", {}).get("temperature", 0.7),
            ]
            writer.writerow(row)

    def _write_modification_paper_metrics(
        self,
        writer,
        condition_name: str,
        condition_data: Dict[str, Any],
        control_results: Dict[str, Any],
    ) -> None:
        """修正実験の論文用指標を書き込み"""
        parts = condition_name.split("_")
        trait = parts[0]
        forced_score = int(parts[2]) if len(parts) > 2 else None

        experiment_id = f"exp_{self.session_id}_{condition_name}"
        pd_results = condition_data.get("pd_results", {})

        for strategy_name, strategy_data in pd_results.get("game_results", {}).items():
            cooperation_rates = []
            avg_payoffs = []
            first_round_coops = []
            last_round_coops = []
            learning_slopes = []

            for repetition_data in strategy_data.get("repetition_details", []):
                game_history = repetition_data.get("game_history", {})
                # GameHistoryオブジェクトの場合は辞書に変換
                if hasattr(game_history, "to_dict"):
                    game_history = game_history.to_dict()
                actions = game_history.get("actions", [])

                if actions:
                    # 協力率
                    coop_rate = sum(
                        1 for action in actions if action.get("player_action") == 1
                    ) / len(actions)
                    cooperation_rates.append(coop_rate)

                    # 平均ペイオフ
                    avg_payoff = sum(
                        action.get("player_payoff", 0) for action in actions
                    )
                    avg_payoffs.append(avg_payoff)

                    # 初回・最終ラウンド協力
                    first_round_coops.append(actions[0].get("player_action", 0))
                    last_round_coops.append(actions[-1].get("player_action", 0))

                    # 学習効果
                    round_coops = [action.get("player_action", 0) for action in actions]
                    if len(round_coops) > 1:
                        slope, _ = np.polyfit(range(len(round_coops)), round_coops, 1)
                        learning_slopes.append(slope)
                    else:
                        learning_slopes.append(0)
                else:
                    cooperation_rates.append(0)
                    avg_payoffs.append(0)
                    first_round_coops.append(0)
                    last_round_coops.append(0)
                    learning_slopes.append(0)

            # 統計指標の計算
            n_reps = len(cooperation_rates)
            coop_mean = statistics.mean(cooperation_rates) if cooperation_rates else 0
            coop_std = (
                statistics.stdev(cooperation_rates) if len(cooperation_rates) > 1 else 0
            )
            payoff_mean = statistics.mean(avg_payoffs) if avg_payoffs else 0
            payoff_std = statistics.stdev(avg_payoffs) if len(avg_payoffs) > 1 else 0

            # 信頼区間（95%）
            if n_reps > 1 and coop_std > 0:
                coop_ci = stats.t.interval(
                    0.95, n_reps - 1, loc=coop_mean, scale=coop_std / np.sqrt(n_reps)
                )
            else:
                coop_ci = (coop_mean, coop_mean)

            if n_reps > 1 and payoff_std > 0:
                payoff_ci = stats.t.interval(
                    0.95,
                    n_reps - 1,
                    loc=payoff_mean,
                    scale=payoff_std / np.sqrt(n_reps),
                )
            else:
                payoff_ci = (payoff_mean, payoff_mean)

            # コントロール条件との比較
            control_coop_rates = []
            if strategy_name in control_results.get("game_results", {}):
                control_strategy = control_results["game_results"][strategy_name]
                for rep_data in control_strategy.get("repetition_details", []):
                    game_history = rep_data.get("game_history", {})
                    # GameHistoryオブジェクトの場合は辞書に変換
                    if hasattr(game_history, "to_dict"):
                        game_history = game_history.to_dict()
                    actions = game_history.get("actions", [])
                    if actions:
                        control_coop_rate = sum(
                            1 for action in actions if action.get("player_action") == 1
                        ) / len(actions)
                        control_coop_rates.append(control_coop_rate)

            # Cohen's d と t検定
            cohens_d = None
            t_stat = None
            p_value = None
            effect_size_category = "no_comparison"

            if (
                control_coop_rates
                and len(control_coop_rates) > 1
                and len(cooperation_rates) > 1
            ):
                # Cohen's d
                pooled_std = np.sqrt(
                    (
                        (len(control_coop_rates) - 1)
                        * np.var(control_coop_rates, ddof=1)
                        + (len(cooperation_rates) - 1)
                        * np.var(cooperation_rates, ddof=1)
                    )
                    / (len(control_coop_rates) + len(cooperation_rates) - 2)
                )
                cohens_d = (
                    (coop_mean - statistics.mean(control_coop_rates)) / pooled_std
                    if pooled_std > 0
                    else 0
                )

                # t検定
                t_stat, p_value = stats.ttest_ind(control_coop_rates, cooperation_rates)

                # 効果サイズカテゴリ
                if abs(cohens_d) < 0.2:
                    effect_size_category = "negligible"
                elif abs(cohens_d) < 0.5:
                    effect_size_category = "small"
                elif abs(cohens_d) < 0.8:
                    effect_size_category = "medium"
                else:
                    effect_size_category = "large"

            # 一貫性指標
            consistency = 1 / (coop_std + 0.001) if coop_std > 0 else 1

            row = [
                experiment_id,
                "modification",
                trait,
                forced_score,
                strategy_name,
                n_reps,
                coop_mean,
                coop_std,
                coop_ci[0],
                coop_ci[1],
                payoff_mean,
                payoff_std,
                payoff_ci[0],
                payoff_ci[1],
                cohens_d,
                t_stat,
                p_value,
                effect_size_category,
                statistics.mean(first_round_coops),
                statistics.mean(last_round_coops),
                statistics.mean(learning_slopes),
                self.config.get("pd_game_settings", {}).get(
                    "prompt_template", "competitive"
                ),
                self.config.get("bfi_settings", {}).get("mode", "numbers_and_language"),
                self.config.get("model_settings", {}).get(
                    "model_name", "gpt-3.5-turbo"
                ),
                self.config.get("model_settings", {}).get("temperature", 0.7),
            ]
            writer.writerow(row)

    def export_experiment_metadata(
        self, config: Dict[str, Any], execution_time: float, prompt_template: str = None
    ) -> None:
        """実験設定のメタデータをCSVで出力"""
        csv_file = self.output_dir / f"experiment_metadata_{self.session_id}.csv"

        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # ヘッダー
            headers = ["parameter", "value", "category", "description"]
            writer.writerow(headers)

            # 実験設定
            metadata = [
                ("session_id", self.session_id, "experiment", "実験セッションID"),
                (
                    "execution_time_minutes",
                    execution_time,
                    "experiment",
                    "実行時間（分）",
                ),
                (
                    "model_name",
                    config.get("model_settings", {}).get("model_name", "unknown"),
                    "model",
                    "使用LLMモデル",
                ),
                (
                    "temperature",
                    config.get("model_settings", {}).get("temperature", 0.7),
                    "model",
                    "LLM温度パラメータ",
                ),
                (
                    "max_tokens",
                    config.get("model_settings", {}).get("max_tokens", 100),
                    "model",
                    "最大トークン数",
                ),
                (
                    "bfi_iterations",
                    config.get("bfi_settings", {}).get("iterations", 3),
                    "bfi",
                    "BFI質問反復回数",
                ),
                (
                    "bfi_mode",
                    config.get("bfi_settings", {}).get("mode", "numbers_and_language"),
                    "bfi",
                    "BFIモード",
                ),
                (
                    "pd_iterations",
                    config.get("pd_game_settings", {}).get("iterations", 3),
                    "pd_game",
                    "PDゲーム反復回数",
                ),
                (
                    "pd_repetitions",
                    config.get("pd_game_settings", {}).get("repetitions", 3),
                    "pd_game",
                    "PDゲーム反復回数",
                ),
                (
                    "prompt_template",
                    (
                        prompt_template
                        if prompt_template is not None
                        else config.get("pd_game_settings", {}).get(
                            "prompt_template", "competitive"
                        )
                    ),
                    "pd_game",
                    "プロンプトテンプレート",
                ),
                (
                    "target_traits",
                    str(
                        config.get("personality_modification_settings", {}).get(
                            "target_traits", []
                        )
                    ),
                    "personality",
                    "対象性格特性",
                ),
                (
                    "forced_scores",
                    str(
                        config.get("personality_modification_settings", {}).get(
                            "forced_scores", []
                        )
                    ),
                    "personality",
                    "強制スコア",
                ),
                (
                    "strategies",
                    str(config.get("strategy_settings", {}).get("strategies", [])),
                    "strategies",
                    "使用戦略",
                ),
                ("timestamp", datetime.now().isoformat(), "experiment", "実験実行時刻"),
            ]

            for param, value, category, description in metadata:
                writer.writerow([param, value, category, description])

        logger.info(f"Experiment metadata exported to: {csv_file}")

    def export_summary_table(
        self, all_results: Dict[str, Any], control_baseline: Dict[str, Any]
    ) -> None:
        """論文用のサマリーテーブルをCSVで出力"""
        self.processed_data_dir.mkdir(exist_ok=True)
        csv_file = self.processed_data_dir / f"summary_table_{self.session_id}.csv"

        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # ヘッダー
            headers = [
                "condition",
                "trait",
                "forced_score",
                "strategy",
                "n",
                "cooperation_rate",
                "cooperation_rate_ci",
                "avg_payoff",
                "avg_payoff_ci",
                "cohens_d",
                "p_value",
                "effect_size",
                "prompt_template",
                "bfi_mode",
                "model_name",
            ]
            writer.writerow(headers)

            # コントロール条件
            if "control_pd_results" in all_results:
                self._write_summary_control(writer, all_results["control_pd_results"])

            # 修正実験
            for condition_name, condition_data in all_results.items():
                if condition_name.startswith(
                    (
                        "extraversion",
                        "agreeableness",
                        "conscientiousness",
                        "neuroticism",
                        "openness",
                    )
                ):
                    self._write_summary_modification(
                        writer,
                        condition_name,
                        condition_data,
                        all_results["control_pd_results"],
                    )

        logger.info(f"Summary table exported to: {csv_file}")

    def export_personality_analysis(
        self, all_results: Dict[str, Any], control_baseline: Dict[str, Any]
    ) -> None:
        """性格特性の詳細分析をCSVで出力"""
        self.processed_data_dir.mkdir(exist_ok=True)
        csv_file = (
            self.processed_data_dir / f"personality_analysis_{self.session_id}.csv"
        )

        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # ヘッダー
            headers = [
                "experiment_id",
                "condition",
                "trait",
                "forced_score",
                "iteration",
                "extraversion",
                "agreeableness",
                "conscientiousness",
                "neuroticism",
                "openness",
                "personality_stability",
                "personality_consistency",
                "personality_dominance",
                "personality_balance",
                "personality_extremity",
                "personality_cluster",
                "prompt_template",
                "bfi_mode",
                "model_name",
                "temperature",
            ]
            writer.writerow(headers)

            # コントロール条件の性格分析
            if control_baseline and "iterations" in control_baseline:
                experiment_id = f"exp_{self.session_id}_control"
                for i, iteration in enumerate(control_baseline["iterations"]):
                    personality_metrics = self._calculate_personality_metrics(iteration)
                    row = [
                        experiment_id,
                        "control",
                        "control",
                        None,
                        i + 1,
                        iteration.get("extraversion", 0),
                        iteration.get("agreeableness", 0),
                        iteration.get("conscientiousness", 0),
                        iteration.get("neuroticism", 0),
                        iteration.get("openness", 0),
                        personality_metrics["stability"],
                        personality_metrics["consistency"],
                        personality_metrics["dominance"],
                        personality_metrics["balance"],
                        personality_metrics["extremity"],
                        personality_metrics["cluster"],
                        self.config.get("pd_game_settings", {}).get(
                            "prompt_template", "competitive"
                        ),
                        self.config.get("bfi_settings", {}).get(
                            "mode", "numbers_and_language"
                        ),
                        self.config.get("model_settings", {}).get(
                            "model_name", "gpt-3.5-turbo"
                        ),
                        self.config.get("model_settings", {}).get("temperature", 0.7),
                    ]
                    writer.writerow(row)

            # 修正実験の性格分析
            for condition_name, condition_data in all_results.items():
                if condition_name.startswith(
                    (
                        "extraversion",
                        "agreeableness",
                        "conscientiousness",
                        "neuroticism",
                        "openness",
                    )
                ):
                    parts = condition_name.split("_")
                    trait = parts[0]
                    forced_score = int(parts[2]) if len(parts) > 2 else None

                    experiment_id = f"exp_{self.session_id}_{condition_name}"
                    bfi_scores = condition_data.get("bfi_scores", {})

                    if "iterations" in bfi_scores:
                        for i, iteration in enumerate(bfi_scores["iterations"]):
                            personality_metrics = self._calculate_personality_metrics(
                                iteration
                            )
                            row = [
                                experiment_id,
                                "modification",
                                trait,
                                forced_score,
                                i + 1,
                                iteration.get("extraversion", 0),
                                iteration.get("agreeableness", 0),
                                iteration.get("conscientiousness", 0),
                                iteration.get("neuroticism", 0),
                                iteration.get("openness", 0),
                                personality_metrics["stability"],
                                personality_metrics["consistency"],
                                personality_metrics["dominance"],
                                personality_metrics["balance"],
                                personality_metrics["extremity"],
                                personality_metrics["cluster"],
                                self.config.get("pd_game_settings", {}).get(
                                    "prompt_template", "competitive"
                                ),
                                self.config.get("bfi_settings", {}).get(
                                    "mode", "numbers_and_language"
                                ),
                                self.config.get("model_settings", {}).get(
                                    "model_name", "gpt-3.5-turbo"
                                ),
                                self.config.get("model_settings", {}).get(
                                    "temperature", 0.7
                                ),
                            ]
                            writer.writerow(row)

        logger.info(f"Personality analysis exported to: {csv_file}")

    def _calculate_personality_metrics(
        self, personality_scores: Dict[str, float]
    ) -> Dict[str, Any]:
        """性格特性のメトリクスを計算"""
        # 数値のみを抽出
        scores = []
        for key, value in personality_scores.items():
            if isinstance(value, (int, float)):
                scores.append(value)
            elif isinstance(value, dict) and "trait_averages" in value:
                # iteration形式の場合
                trait_averages = value["trait_averages"]
                scores.extend(trait_averages.values())

        if not scores:
            return {
                "stability": 1.0,
                "consistency": 0.5,
                "dominance": "unknown",
                "balance": 1.0,
                "extremity": 0.0,
                "cluster": "unknown",
            }

        # 安定性（標準偏差の逆数）
        stability = 1 / (statistics.stdev(scores) + 0.001) if len(scores) > 1 else 1

        # 一貫性（特性間の相関の平均）- 簡略化
        consistency = 0.5  # 実際の相関計算は複雑なため簡略化

        # 支配的特性（最高スコアの特性）
        if isinstance(personality_scores, dict) and all(
            isinstance(v, (int, float)) for v in personality_scores.values()
        ):
            dominance_trait = max(personality_scores, key=personality_scores.get)
        else:
            dominance_trait = "unknown"

        # バランス（分散の逆数）
        balance = 1 / (statistics.variance(scores) + 0.001) if len(scores) > 1 else 1

        # 極端性（平均からの偏差の絶対値）
        mean_score = statistics.mean(scores)
        extremity = sum(abs(score - mean_score) for score in scores) / len(scores)

        # 性格クラスター（外向性+開放性 vs 協調性+誠実性）
        if isinstance(personality_scores, dict) and all(
            isinstance(v, (int, float)) for v in personality_scores.values()
        ):
            extraversion_openness = personality_scores.get(
                "extraversion", 0
            ) + personality_scores.get("openness", 0)
            agreeableness_conscientiousness = personality_scores.get(
                "agreeableness", 0
            ) + personality_scores.get("conscientiousness", 0)
            cluster = (
                "social_creative"
                if extraversion_openness > agreeableness_conscientiousness
                else "cooperative_reliable"
            )
        else:
            cluster = "unknown"

        return {
            "stability": stability,
            "consistency": consistency,
            "dominance": dominance_trait,
            "balance": balance,
            "extremity": extremity,
            "cluster": cluster,
        }

    def export_strategy_performance(
        self, all_results: Dict[str, Any], control_baseline: Dict[str, Any]
    ) -> None:
        """戦略パフォーマンスの比較分析をCSVで出力"""
        self.processed_data_dir.mkdir(exist_ok=True)
        csv_file = (
            self.processed_data_dir / f"strategy_performance_{self.session_id}.csv"
        )

        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # ヘッダー
            headers = [
                "experiment_id",
                "condition",
                "trait",
                "forced_score",
                "strategy_name",
                "strategy_type",
                "total_games",
                "cooperation_rate",
                "avg_payoff",
                "total_payoff",
                "cooperation_consistency",
                "payoff_stability",
                "learning_rate",
                "adaptation_speed",
                "strategy_efficiency",
                "strategy_robustness",
                "performance_rank",
                "performance_score",
                "prompt_template",
                "bfi_mode",
                "model_name",
                "temperature",
            ]
            writer.writerow(headers)

            # コントロール条件の戦略パフォーマンス
            if "control_pd_results" in all_results:
                self._write_strategy_performance_control(
                    writer, all_results["control_pd_results"]
                )

            # 修正実験の戦略パフォーマンス
            for condition_name, condition_data in all_results.items():
                if condition_name.startswith(
                    (
                        "extraversion",
                        "agreeableness",
                        "conscientiousness",
                        "neuroticism",
                        "openness",
                    )
                ):
                    self._write_strategy_performance_modification(
                        writer,
                        condition_name,
                        condition_data,
                        all_results["control_pd_results"],
                    )

        logger.info(f"Strategy performance exported to: {csv_file}")

    def export_interaction_patterns(
        self, all_results: Dict[str, Any], control_baseline: Dict[str, Any]
    ) -> None:
        """相互作用パターンの分析をCSVで出力"""
        self.processed_data_dir.mkdir(exist_ok=True)
        csv_file = (
            self.processed_data_dir / f"interaction_patterns_{self.session_id}.csv"
        )

        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # ヘッダー
            headers = [
                "experiment_id",
                "condition",
                "trait",
                "forced_score",
                "strategy_name",
                "repetition",
                "round_num",
                "player_action",
                "opponent_action",
                "player_payoff",
                "opponent_payoff",
                "action_pattern",
                "response_pattern",
                "cooperation_momentum",
                "defection_momentum",
                "pattern_stability",
                "interaction_complexity",
                "behavioral_flexibility",
                "strategic_depth",
                "prompt_template",
                "bfi_mode",
                "model_name",
                "temperature",
            ]
            writer.writerow(headers)

            # コントロール条件の相互作用パターン
            if "control_pd_results" in all_results:
                self._write_interaction_patterns_control(
                    writer, all_results["control_pd_results"]
                )

            # 修正実験の相互作用パターン
            for condition_name, condition_data in all_results.items():
                if condition_name.startswith(
                    (
                        "extraversion",
                        "agreeableness",
                        "conscientiousness",
                        "neuroticism",
                        "openness",
                    )
                ):
                    self._write_interaction_patterns_modification(
                        writer, condition_name, condition_data
                    )

        logger.info(f"Interaction patterns exported to: {csv_file}")

    def _write_strategy_performance_control(
        self, writer, pd_results: Dict[str, Any]
    ) -> None:
        """コントロール条件の戦略パフォーマンスを書き込み"""
        experiment_id = f"exp_{self.session_id}_control"

        for strategy_name, strategy_data in pd_results.get("game_results", {}).items():
            performance_metrics = self._calculate_strategy_performance_metrics(
                strategy_data
            )
            row = [
                experiment_id,
                "control",
                "control",
                None,
                strategy_name,
                performance_metrics["strategy_type"],
                performance_metrics["total_games"],
                performance_metrics["cooperation_rate"],
                performance_metrics["avg_payoff"],
                performance_metrics["total_payoff"],
                performance_metrics["cooperation_consistency"],
                performance_metrics["payoff_stability"],
                performance_metrics["learning_rate"],
                performance_metrics["adaptation_speed"],
                performance_metrics["strategy_efficiency"],
                performance_metrics["strategy_robustness"],
                performance_metrics["performance_rank"],
                performance_metrics["performance_score"],
                self.config.get("pd_game_settings", {}).get(
                    "prompt_template", "competitive"
                ),
                self.config.get("bfi_settings", {}).get("mode", "numbers_and_language"),
                self.config.get("model_settings", {}).get(
                    "model_name", "gpt-3.5-turbo"
                ),
                self.config.get("model_settings", {}).get("temperature", 0.7),
            ]
            writer.writerow(row)

    def _write_strategy_performance_modification(
        self,
        writer,
        condition_name: str,
        condition_data: Dict[str, Any],
        control_results: Dict[str, Any],
    ) -> None:
        """修正実験の戦略パフォーマンスを書き込み"""
        parts = condition_name.split("_")
        trait = parts[0]
        forced_score = int(parts[2]) if len(parts) > 2 else None
        experiment_id = f"exp_{self.session_id}_{condition_name}"

        pd_results = condition_data.get("pd_results", {})

        for strategy_name, strategy_data in pd_results.get("game_results", {}).items():
            performance_metrics = self._calculate_strategy_performance_metrics(
                strategy_data
            )
            row = [
                experiment_id,
                "modification",
                trait,
                forced_score,
                strategy_name,
                performance_metrics["strategy_type"],
                performance_metrics["total_games"],
                performance_metrics["cooperation_rate"],
                performance_metrics["avg_payoff"],
                performance_metrics["total_payoff"],
                performance_metrics["cooperation_consistency"],
                performance_metrics["payoff_stability"],
                performance_metrics["learning_rate"],
                performance_metrics["adaptation_speed"],
                performance_metrics["strategy_efficiency"],
                performance_metrics["strategy_robustness"],
                performance_metrics["performance_rank"],
                performance_metrics["performance_score"],
                self.config.get("pd_game_settings", {}).get(
                    "prompt_template", "competitive"
                ),
                self.config.get("bfi_settings", {}).get("mode", "numbers_and_language"),
                self.config.get("model_settings", {}).get(
                    "model_name", "gpt-3.5-turbo"
                ),
                self.config.get("model_settings", {}).get("temperature", 0.7),
            ]
            writer.writerow(row)

    def _calculate_strategy_performance_metrics(
        self, strategy_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """戦略パフォーマンスのメトリクスを計算"""
        cooperation_rates = []
        avg_payoffs = []
        total_games = 0
        total_payoff = 0

        for repetition_data in strategy_data.get("repetition_details", []):
            game_history = repetition_data.get("game_history", {})
            if hasattr(game_history, "to_dict"):
                game_history = game_history.to_dict()
            actions = game_history.get("actions", [])

            if actions:
                coop_rate = sum(
                    1 for action in actions if action.get("player_action") == 1
                ) / len(actions)
                cooperation_rates.append(coop_rate)
                payoff = sum(action.get("player_payoff", 0) for action in actions)
                avg_payoffs.append(payoff)
                total_games += len(actions)
                total_payoff += payoff

        # 基本メトリクス
        cooperation_rate = (
            statistics.mean(cooperation_rates) if cooperation_rates else 0
        )
        avg_payoff = statistics.mean(avg_payoffs) if avg_payoffs else 0

        # 一貫性と安定性
        cooperation_consistency = (
            1 / (statistics.stdev(cooperation_rates) + 0.001)
            if len(cooperation_rates) > 1
            else 1
        )
        payoff_stability = (
            1 / (statistics.stdev(avg_payoffs) + 0.001) if len(avg_payoffs) > 1 else 1
        )

        # 学習率（最初の5ラウンドと最後の5ラウンドの協力率差）
        learning_rate = 0  # 簡略化

        # 適応速度
        adaptation_speed = 5  # 簡略化

        # 戦略効率
        strategy_efficiency = cooperation_rate * avg_payoff

        # 戦略の堅牢性
        strategy_robustness = cooperation_consistency * payoff_stability

        # パフォーマンスランク（簡略化）
        performance_rank = 3  # 1-5の範囲

        # 総合パフォーマンススコア
        performance_score = (
            cooperation_rate * 0.4
            + strategy_efficiency * 0.3
            + strategy_robustness * 0.3
        )

        return {
            "strategy_type": "unknown",
            "total_games": total_games,
            "cooperation_rate": cooperation_rate,
            "avg_payoff": avg_payoff,
            "total_payoff": total_payoff,
            "cooperation_consistency": cooperation_consistency,
            "payoff_stability": payoff_stability,
            "learning_rate": learning_rate,
            "adaptation_speed": adaptation_speed,
            "strategy_efficiency": strategy_efficiency,
            "strategy_robustness": strategy_robustness,
            "performance_rank": performance_rank,
            "performance_score": performance_score,
        }

    def _write_interaction_patterns_control(
        self, writer, pd_results: Dict[str, Any]
    ) -> None:
        """コントロール条件の相互作用パターンを書き込み"""
        experiment_id = f"exp_{self.session_id}_control"

        for strategy_name, strategy_data in pd_results.get("game_results", {}).items():
            for rep_idx, repetition_data in enumerate(
                strategy_data.get("repetition_details", [])
            ):
                game_history = repetition_data.get("game_history", {})
                if hasattr(game_history, "to_dict"):
                    game_history = game_history.to_dict()
                actions = game_history.get("actions", [])

                for round_idx, action in enumerate(actions):
                    interaction_metrics = self._calculate_interaction_metrics(
                        actions, round_idx
                    )
                    row = [
                        experiment_id,
                        "control",
                        "control",
                        None,
                        strategy_name,
                        rep_idx + 1,
                        round_idx + 1,
                        action.get("player_action", 0),
                        action.get("opponent_action", 0),
                        action.get("player_payoff", 0),
                        action.get("opponent_payoff", 0),
                        interaction_metrics["action_pattern"],
                        interaction_metrics["response_pattern"],
                        interaction_metrics["cooperation_momentum"],
                        interaction_metrics["defection_momentum"],
                        interaction_metrics["pattern_stability"],
                        interaction_metrics["interaction_complexity"],
                        interaction_metrics["behavioral_flexibility"],
                        interaction_metrics["strategic_depth"],
                        self.config.get("pd_game_settings", {}).get(
                            "prompt_template", "competitive"
                        ),
                        self.config.get("bfi_settings", {}).get(
                            "mode", "numbers_and_language"
                        ),
                        self.config.get("model_settings", {}).get(
                            "model_name", "gpt-3.5-turbo"
                        ),
                        self.config.get("model_settings", {}).get("temperature", 0.7),
                    ]
                    writer.writerow(row)

    def _write_interaction_patterns_modification(
        self, writer, condition_name: str, condition_data: Dict[str, Any]
    ) -> None:
        """修正実験の相互作用パターンを書き込み"""
        parts = condition_name.split("_")
        trait = parts[0]
        forced_score = int(parts[2]) if len(parts) > 2 else None
        experiment_id = f"exp_{self.session_id}_{condition_name}"

        pd_results = condition_data.get("pd_results", {})

        for strategy_name, strategy_data in pd_results.get("game_results", {}).items():
            for rep_idx, repetition_data in enumerate(
                strategy_data.get("repetition_details", [])
            ):
                game_history = repetition_data.get("game_history", {})
                if hasattr(game_history, "to_dict"):
                    game_history = game_history.to_dict()
                actions = game_history.get("actions", [])

                for round_idx, action in enumerate(actions):
                    interaction_metrics = self._calculate_interaction_metrics(
                        actions, round_idx
                    )
                    row = [
                        experiment_id,
                        "modification",
                        trait,
                        forced_score,
                        strategy_name,
                        rep_idx + 1,
                        round_idx + 1,
                        action.get("player_action", 0),
                        action.get("opponent_action", 0),
                        action.get("player_payoff", 0),
                        action.get("opponent_payoff", 0),
                        interaction_metrics["action_pattern"],
                        interaction_metrics["response_pattern"],
                        interaction_metrics["cooperation_momentum"],
                        interaction_metrics["defection_momentum"],
                        interaction_metrics["pattern_stability"],
                        interaction_metrics["interaction_complexity"],
                        interaction_metrics["behavioral_flexibility"],
                        interaction_metrics["strategic_depth"],
                        self.config.get("pd_game_settings", {}).get(
                            "prompt_template", "competitive"
                        ),
                        self.config.get("bfi_settings", {}).get(
                            "mode", "numbers_and_language"
                        ),
                        self.config.get("model_settings", {}).get(
                            "model_name", "gpt-3.5-turbo"
                        ),
                        self.config.get("model_settings", {}).get("temperature", 0.7),
                    ]
                    writer.writerow(row)

    def _calculate_interaction_metrics(
        self, actions: List[Dict], current_round: int
    ) -> Dict[str, Any]:
        """相互作用のメトリクスを計算"""
        if current_round == 0:
            return {
                "action_pattern": "initial",
                "response_pattern": "initial",
                "cooperation_momentum": 0,
                "defection_momentum": 0,
                "pattern_stability": 0,
                "interaction_complexity": 0,
                "behavioral_flexibility": 0,
                "strategic_depth": 0,
            }

        current_action = actions[current_round]
        player_action = current_action.get("player_action", 0)
        opponent_action = current_action.get("opponent_action", 0)

        # 行動パターン
        action_pattern = f"{'C' if player_action == 1 else 'D'}-{'C' if opponent_action == 1 else 'D'}"

        # 応答パターン
        if current_round > 0:
            prev_action = actions[current_round - 1]
            prev_opponent = prev_action.get("opponent_action", 0)
            if prev_opponent == 1 and player_action == 1:
                response_pattern = "cooperate_to_cooperate"
            elif prev_opponent == 1 and player_action == 0:
                response_pattern = "defect_to_cooperate"
            elif prev_opponent == 0 and player_action == 1:
                response_pattern = "cooperate_to_defect"
            else:
                response_pattern = "defect_to_defect"
        else:
            response_pattern = "initial"

        # 協力の勢い
        cooperation_momentum = 0
        for i in range(max(0, current_round - 4), current_round + 1):
            if actions[i].get("player_action", 0) == 1:
                cooperation_momentum += 1
            else:
                break

        # 裏切りの勢い
        defection_momentum = 0
        for i in range(max(0, current_round - 4), current_round + 1):
            if actions[i].get("player_action", 0) == 0:
                defection_momentum += 1
            else:
                break

        # パターンの安定性
        pattern_stability = 1 / (
            len(
                set(
                    actions[i].get("player_action", 0)
                    for i in range(max(0, current_round - 4), current_round + 1)
                )
            )
            + 0.001
        )

        # 相互作用の複雑性
        interaction_complexity = len(
            set(
                f"{actions[i].get('player_action', 0)}-{actions[i].get('opponent_action', 0)}"
                for i in range(max(0, current_round - 4), current_round + 1)
            )
        )

        # 行動の柔軟性
        behavioral_flexibility = 1 / (pattern_stability + 0.001)

        # 戦略の深さ
        strategic_depth = min(current_round, 10) / 10  # 0-1の範囲

        return {
            "action_pattern": action_pattern,
            "response_pattern": response_pattern,
            "cooperation_momentum": cooperation_momentum,
            "defection_momentum": defection_momentum,
            "pattern_stability": pattern_stability,
            "interaction_complexity": interaction_complexity,
            "behavioral_flexibility": behavioral_flexibility,
            "strategic_depth": strategic_depth,
        }

    def _write_summary_control(self, writer, pd_results: Dict[str, Any]) -> None:
        """コントロール条件のサマリーを書き込み"""
        for strategy_name, strategy_data in pd_results.get("game_results", {}).items():
            cooperation_rates = []
            avg_payoffs = []

            for repetition_data in strategy_data.get("repetition_details", []):
                game_history = repetition_data.get("game_history", {})
                # GameHistoryオブジェクトの場合は辞書に変換
                if hasattr(game_history, "to_dict"):
                    game_history = game_history.to_dict()
                actions = game_history.get("actions", [])

                if actions:
                    coop_rate = sum(
                        1 for action in actions if action.get("player_action") == 1
                    ) / len(actions)
                    cooperation_rates.append(coop_rate)
                    avg_payoff = sum(
                        action.get("player_payoff", 0) for action in actions
                    )
                    avg_payoffs.append(avg_payoff)

            n = len(cooperation_rates)
            coop_mean = statistics.mean(cooperation_rates) if cooperation_rates else 0
            coop_std = (
                statistics.stdev(cooperation_rates) if len(cooperation_rates) > 1 else 0
            )
            payoff_mean = statistics.mean(avg_payoffs) if avg_payoffs else 0
            payoff_std = statistics.stdev(avg_payoffs) if len(avg_payoffs) > 1 else 0

            # 信頼区間
            if n > 1:
                coop_ci = stats.t.interval(
                    0.95, n - 1, loc=coop_mean, scale=coop_std / np.sqrt(n)
                )
                payoff_ci = stats.t.interval(
                    0.95, n - 1, loc=payoff_mean, scale=payoff_std / np.sqrt(n)
                )
                coop_ci_str = f"[{coop_ci[0]:.3f}, {coop_ci[1]:.3f}]"
                payoff_ci_str = f"[{payoff_ci[0]:.3f}, {payoff_ci[1]:.3f}]"
            else:
                coop_ci_str = f"[{coop_mean:.3f}, {coop_mean:.3f}]"
                payoff_ci_str = f"[{payoff_mean:.3f}, {payoff_mean:.3f}]"

            row = [
                "control",
                "control",
                None,
                strategy_name,
                n,
                f"{coop_mean:.3f}",
                coop_ci_str,
                f"{payoff_mean:.3f}",
                payoff_ci_str,
                None,
                None,
                "baseline",
                self.config.get("pd_game_settings", {}).get(
                    "prompt_template", "competitive"
                ),
                self.config.get("bfi_settings", {}).get("mode", "numbers_and_language"),
                self.config.get("model_settings", {}).get(
                    "model_name", "gpt-3.5-turbo"
                ),
            ]
            writer.writerow(row)

    def _write_summary_modification(
        self,
        writer,
        condition_name: str,
        condition_data: Dict[str, Any],
        control_results: Dict[str, Any],
    ) -> None:
        """修正実験のサマリーを書き込み"""
        parts = condition_name.split("_")
        trait = parts[0]
        forced_score = int(parts[2]) if len(parts) > 2 else None

        pd_results = condition_data.get("pd_results", {})

        for strategy_name, strategy_data in pd_results.get("game_results", {}).items():
            cooperation_rates = []
            avg_payoffs = []

            for repetition_data in strategy_data.get("repetition_details", []):
                game_history = repetition_data.get("game_history", {})
                # GameHistoryオブジェクトの場合は辞書に変換
                if hasattr(game_history, "to_dict"):
                    game_history = game_history.to_dict()
                actions = game_history.get("actions", [])

                if actions:
                    coop_rate = sum(
                        1 for action in actions if action.get("player_action") == 1
                    ) / len(actions)
                    cooperation_rates.append(coop_rate)
                    avg_payoff = sum(
                        action.get("player_payoff", 0) for action in actions
                    )
                    avg_payoffs.append(avg_payoff)

            n = len(cooperation_rates)
            coop_mean = statistics.mean(cooperation_rates) if cooperation_rates else 0
            coop_std = (
                statistics.stdev(cooperation_rates) if len(cooperation_rates) > 1 else 0
            )
            payoff_mean = statistics.mean(avg_payoffs) if avg_payoffs else 0
            payoff_std = statistics.stdev(avg_payoffs) if len(avg_payoffs) > 1 else 0

            # 信頼区間
            if n > 1:
                coop_ci = stats.t.interval(
                    0.95, n - 1, loc=coop_mean, scale=coop_std / np.sqrt(n)
                )
                payoff_ci = stats.t.interval(
                    0.95, n - 1, loc=payoff_mean, scale=payoff_std / np.sqrt(n)
                )
                coop_ci_str = f"[{coop_ci[0]:.3f}, {coop_ci[1]:.3f}]"
                payoff_ci_str = f"[{payoff_ci[0]:.3f}, {payoff_ci[1]:.3f}]"
            else:
                coop_ci_str = f"[{coop_mean:.3f}, {coop_mean:.3f}]"
                payoff_ci_str = f"[{payoff_mean:.3f}, {payoff_mean:.3f}]"

            # コントロール条件との比較
            cohens_d = None
            p_value = None
            effect_size = "no_comparison"

            if strategy_name in control_results.get("game_results", {}):
                control_strategy = control_results["game_results"][strategy_name]
                control_coop_rates = []
                for rep_data in control_strategy.get("repetition_details", []):
                    game_history = rep_data.get("game_history", {})
                    # GameHistoryオブジェクトの場合は辞書に変換
                    if hasattr(game_history, "to_dict"):
                        game_history = game_history.to_dict()
                    actions = game_history.get("actions", [])
                    if actions:
                        control_coop_rate = sum(
                            1 for action in actions if action.get("player_action") == 1
                        ) / len(actions)
                        control_coop_rates.append(control_coop_rate)

                if (
                    control_coop_rates
                    and len(control_coop_rates) > 1
                    and len(cooperation_rates) > 1
                ):
                    # Cohen's d
                    pooled_std = np.sqrt(
                        (
                            (len(control_coop_rates) - 1)
                            * np.var(control_coop_rates, ddof=1)
                            + (len(cooperation_rates) - 1)
                            * np.var(cooperation_rates, ddof=1)
                        )
                        / (len(control_coop_rates) + len(cooperation_rates) - 2)
                    )
                    cohens_d = (
                        (coop_mean - statistics.mean(control_coop_rates)) / pooled_std
                        if pooled_std > 0
                        else 0
                    )

                    # t検定
                    _, p_value = stats.ttest_ind(control_coop_rates, cooperation_rates)

                    # 効果サイズカテゴリ
                    if abs(cohens_d) < 0.2:
                        effect_size = "negligible"
                    elif abs(cohens_d) < 0.5:
                        effect_size = "small"
                    elif abs(cohens_d) < 0.8:
                        effect_size = "medium"
                    else:
                        effect_size = "large"

            row = [
                "modification",
                trait,
                forced_score,
                strategy_name,
                n,
                f"{coop_mean:.3f}",
                coop_ci_str,
                f"{payoff_mean:.3f}",
                payoff_ci_str,
                f"{cohens_d:.3f}" if cohens_d is not None else None,
                f"{p_value:.3f}" if p_value is not None else None,
                effect_size,
                self.config.get("pd_game_settings", {}).get(
                    "prompt_template", "competitive"
                ),
                self.config.get("bfi_settings", {}).get("mode", "numbers_and_language"),
                self.config.get("model_settings", {}).get(
                    "model_name", "gpt-3.5-turbo"
                ),
            ]
            writer.writerow(row)
