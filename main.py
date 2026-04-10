#!/usr/bin/env python3

import argparse  # コマンドライン引数を処理するライブラリ
import json  # 実験結果を保存するためのJSONファイル操作
import os  # 環境変数の操作
import numpy as np  # 数値計算ライブラリ（BFIスコア計算で使用）
from pathlib import Path  # パス操作ライブラリ
from datetime import datetime  # 実験実行時刻の記録用
import logging  # 実験の進行状況をファイルとコンソールに出力
from typing import List, Dict, Any
from contextlib import contextmanager

# プロジェクトルートを定義（__file__基準の絶対パス）
PROJECT_ROOT = Path(__file__).parent.resolve()

"""
【カスタムモジュール】
- bfi_analyzer: Big Five Inventoryの質問作成・回答分析
- pd_game: 囚人のジレンマゲームの実行
- model_client: OpenAI APIとの通信
- strategies: 対戦相手の戦略（TFT、GRIM等）
- analysis: 実験結果の分析・可視化
"""
from src.bfi_analyzer import BFIAnalyzer
from src.pd_game import PrisonersDilemmaGame
from src.model_client import ModelClient
from src.strategies import StrategyManager
from src.csv_exporter import CSVExporter
from src.prompt_logger import PromptLogger

# ログディレクトリの作成
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "research.log"),  # research.logファイルに出力する
        logging.StreamHandler(),  # コンソールに表示する
    ],
)
logger = logging.getLogger(__name__)

"""
loggingの参考：https://qiita.com/Broccolingual/items/9838443aa6838a867041
__name__について：https://note.nkmk.me/python-if-name-main/
"""

# デフォルト設定（config.jsonが不完全な場合に用いる）
DEFAULT_CONFIG = {
    "bfi_settings": {"iterations": 1, "modes": ["numbers_and_language"]},
    "pd_game_settings": {
        "iterations": 3,
        "repetitions": 1,
        "prompt_templates": ["competitive"],
    },
    "strategy_settings": {"strategies": ["ALLC", "ALLD", "RANDOM", "GRIM"]},
    "model_settings": {
        "reasoning_effort": "minimal",  # GPT-5の新しいパラメータ
        "verbosity": "low",  # GPT-5の新しいパラメータ
        "temperature": 0.7,  # 従来モデル用（後方互換性）
        "model_name": "gpt-3.5-turbo",
        "provider": "openai",
    },
}


class CustomJSONEncoder(json.JSONEncoder):
    """カスタムJSONエンコーダー"""

    # hasattrはオブジェクトが特定の属性を持っているかどうかをチェックする関数
    # isinstanceはオブジェクトが特定の型かどうかをチェックする関数
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
            # エラー時に詳細な情報を提供してプログラムを停止
            error_msg = (
                f"JSON変換エラー: {type(obj).__name__}型のオブジェクトはJSONに変換できません。\n"
                f"オブジェクト: {obj}\n"
                f"型: {type(obj)}\n"
                f"このエラーにより実験結果が正しく保存できないため、プログラムを停止します。"
            )
            logger.error(error_msg)
            raise TypeError(error_msg)


"""
to_dictについて：https://note.nkmk.me/python-pandas-to-dict/
__dict__について：https://qiita.com/Square_y/items/76d84be810ab0162239d
"""


class PersonalityPDResearch:
    """実験のメインクラス"""

    def __init__(self, config: Dict[str, Any]):
        # config.jsonからオブジェクトを読み込む
        self.config = config

        # タイムスタンプと実験設定を含む出力ディレクトリを作成
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        bfi_iterations = self._get_setting(
            "bfi", "iterations", DEFAULT_CONFIG["bfi_settings"]["iterations"]
        )
        pd_iterations = self._get_setting(
            "pd_game", "iterations", DEFAULT_CONFIG["pd_game_settings"]["iterations"]
        )
        pd_repetitions = self._get_setting(
            "pd_game", "repetitions", DEFAULT_CONFIG["pd_game_settings"]["repetitions"]
        )
        model_name = self._get_setting(
            "model", "model_name", DEFAULT_CONFIG["model_settings"]["model_name"]
        )
        # ディレクトリの名前用に - . _ を削除し最大10文字に制限したモデル名を取得する
        model_short = self._get_model_short_name(model_name)

        # 出力ディレクトリの設定（プロジェクトルート基準）
        output_dir_setting = self._get_setting("experiment", "output_dir", "data")
        if Path(output_dir_setting).is_absolute():
            base_output_dir = Path(output_dir_setting)
        else:
            base_output_dir = PROJECT_ROOT / output_dir_setting

        self.base_output_dir = (
            base_output_dir
            / f"{timestamp}_BFI{bfi_iterations}_PDI{pd_iterations}_PDR{pd_repetitions}_M{model_short}"
        )

        self.base_output_dir.mkdir(parents=True, exist_ok=True)

        # プロンプトテンプレートごとのサブディレクトリは後で作成
        self.output_dir = self.base_output_dir

        logger.info(f"出力ディレクトリが作成されました: {self.output_dir}")

        # プロンプトロガーの初期化
        self.prompt_logger = PromptLogger(self.output_dir)

        # CSV出力の初期化
        self.csv_exporter = CSVExporter(self.output_dir, self.config)

        # 実験開始時間の記録
        self.start_time = datetime.now()

        # モデルクライアントの初期化
        # APIキーは環境変数またはconfig.jsonから取得
        api_key = self._get_setting("model", "api_key", "")
        if not api_key:
            api_key = os.getenv("OPENAI_API_KEY", "")

        self.model_client = ModelClient(
            model_name=self._get_setting(
                "model", "model_name", DEFAULT_CONFIG["model_settings"]["model_name"]
            ),
            api_key=api_key,
            provider=self._get_setting(
                "model", "provider", DEFAULT_CONFIG["model_settings"]["provider"]
            ),
            prompt_logger=self.prompt_logger,
        )

        # 各コンポーネントの初期化
        self.bfi_analyzer = BFIAnalyzer(self.model_client)

        # 戦略マネージャーの初期化
        self.strategy_manager = StrategyManager()

        # BFIベースラインの初期化
        self.control_bfi_baseline = None

        logger.info("実験の初期化が完了しました")

    def _get_setting(self, section: str, key: str, default: Any) -> Any:
        """実験設定を取得（config.json → DEFAULT_CONFIGの優先順位）"""
        section_config = self.config.get(f"{section}_settings", self.config)
        return section_config.get(key, self.config.get(key, default))

    def _get_model_short_name(self, model_name: str) -> str:
        """モデル名を短縮（出力ディレクトリ用）"""
        model_short = model_name.replace("-", "").replace(".", "").replace("_", "")
        return model_short[:10]  # 最大10文字に制限

    def run_control_condition(
        self, bfi_mode: str = "numbers_and_language"
    ) -> Dict[str, Any]:
        """コントロール条件の実行（ペルソナなしのLLMでBFI回答）"""
        try:
            logger.info("コントロール条件を実行")

            # BFI設定の取得
            bfi_iterations = self._get_setting(
                "bfi", "iterations", DEFAULT_CONFIG["bfi_settings"]["iterations"]
            )

            # BFI回答の取得
            bfi_scores = self.bfi_analyzer.get_bfi_scores(
                bfi_scores=None, bfi_mode=bfi_mode, iterations=bfi_iterations
            )

            # BFIベースラインとして保存
            self.control_bfi_baseline = bfi_scores
            logger.info(f"Control BFI baseline saved: {bfi_scores}")

            # 結果の保存
            control_results = {
                "condition": "control",
                "bfi_scores": bfi_scores,
                "bfi_iterations": bfi_iterations,
                "timestamp": datetime.now().isoformat(),
            }

            # JSONファイルへの保存
            try:
                with open(self.output_dir / "control_BFI.json", "w") as f:
                    json.dump(control_results, f, indent=2, cls=CustomJSONEncoder)
            except (TypeError, json.JSONDecodeError) as e:
                logger.error(f"コントロール条件の結果保存に失敗: {e}")
                logger.error(
                    "APIトークンの無駄遣いを防ぐため、プログラムを停止します。"
                )
                raise

            logger.info(f"Control BFI completed. BFI scores: {bfi_scores}")
            return control_results

        except Exception as e:
            logger.error(f"Failed to run control condition: {e}")
            raise

    def _aggregate_repetition_results(
        self, repetition_results: List[Dict], strategy_name: str
    ) -> Dict[str, Any]:
        """複数回の実行結果を統合して平均値と標準偏差を計算"""
        if not repetition_results:
            return {}

        logger.info(
            f"Aggregating {len(repetition_results)} repetitions for {strategy_name}"
        )

        # 各指標の値を集計
        cooperation_rates = []
        avg_payoffs = []
        total_payoffs = []

        for i, result in enumerate(repetition_results):
            game_history = result.get("game_history", {})

            # GameHistoryオブジェクトを辞書に変換
            if hasattr(game_history, "to_dict"):
                game_history_dict = game_history.to_dict()
            elif isinstance(game_history, dict):
                game_history_dict = game_history
            else:
                logger.warning(
                    f"Invalid game history type for {strategy_name} repetition {i+1}: {type(game_history)}"
                )
                cooperation_rates.append(float("nan"))
                avg_payoffs.append(float("nan"))
                total_payoffs.append(float("nan"))
                continue

            # より詳細なデータ構造チェック
            if (
                isinstance(game_history_dict, dict)
                and "actions" in game_history_dict
                and isinstance(game_history_dict["actions"], list)
                and len(game_history_dict["actions"]) > 0
            ):
                # 辞書形式のゲーム履歴を処理
                cooperation_rate = self._calculate_cooperation_rate(game_history_dict)
                avg_payoff = self._calculate_average_payoff(game_history_dict)
                total_payoff = game_history_dict.get("player_total_payoff", 0)

                cooperation_rates.append(cooperation_rate)
                avg_payoffs.append(avg_payoff)
                total_payoffs.append(total_payoff)
            else:
                # フォールバック - 無効なデータはNaNでマーク
                logger.warning(
                    f"Invalid game history for {strategy_name} repetition {i+1}: {game_history_dict}"
                )
                logger.warning(f"DEBUG: Invalid game history details:")
                logger.warning(f"  - is_dict: {isinstance(game_history_dict, dict)}")
                logger.warning(
                    f"  - has_actions: {'actions' in game_history_dict if isinstance(game_history_dict, dict) else False}"
                )
                logger.warning(
                    f"  - actions_is_list: {isinstance(game_history_dict.get('actions'), list) if isinstance(game_history_dict, dict) else False}"
                )
                logger.warning(
                    f"  - actions_length: {len(game_history_dict.get('actions', [])) if isinstance(game_history_dict, dict) else 0}"
                )
                cooperation_rates.append(float("nan"))
                avg_payoffs.append(float("nan"))
                total_payoffs.append(float("nan"))

        # デバッグ情報を追加
        logger.info(
            f"Processing {strategy_name}: {len(cooperation_rates)} cooperation rates, {len(avg_payoffs)} payoffs"
        )
        logger.info(f"Cooperation rates: {cooperation_rates}")
        logger.info(f"Average payoffs: {avg_payoffs}")

        # NaN値を除外して統計計算
        valid_coop_rates = [x for x in cooperation_rates if not np.isnan(x)]
        valid_avg_payoffs = [x for x in avg_payoffs if not np.isnan(x)]
        valid_total_payoffs = [x for x in total_payoffs if not np.isnan(x)]

        logger.info(f"Valid cooperation rates: {valid_coop_rates}")
        logger.info(f"Valid average payoffs: {valid_avg_payoffs}")

        # 基本統計値の計算（NaN値を除外）
        coop_mean = (
            float(np.mean(valid_coop_rates)) if valid_coop_rates else float("nan")
        )
        coop_std = float(
            np.std(valid_coop_rates, ddof=1) if len(valid_coop_rates) > 1 else 0
        )
        payoff_mean = (
            float(np.mean(valid_avg_payoffs)) if valid_avg_payoffs else float("nan")
        )
        payoff_std = float(
            np.std(valid_avg_payoffs, ddof=1) if len(valid_avg_payoffs) > 1 else 0
        )

        # 統計値の計算（NaN値を除外）
        total_payoff_mean = (
            float(np.mean(valid_total_payoffs)) if valid_total_payoffs else float("nan")
        )
        total_payoff_std = float(
            np.std(valid_total_payoffs, ddof=1) if len(valid_total_payoffs) > 1 else 0
        )

        aggregated_analysis = {
            "average_cooperation_rate": {
                "mean": coop_mean,
                "std": coop_std,
                "min": (
                    float(np.min(valid_coop_rates))
                    if valid_coop_rates
                    else float("nan")
                ),
                "max": (
                    float(np.max(valid_coop_rates))
                    if valid_coop_rates
                    else float("nan")
                ),
                "values": cooperation_rates,
            },
            "player_average_payoff": {
                "mean": payoff_mean,
                "std": payoff_std,
                "min": (
                    float(np.min(valid_avg_payoffs))
                    if valid_avg_payoffs
                    else float("nan")
                ),
                "max": (
                    float(np.max(valid_avg_payoffs))
                    if valid_avg_payoffs
                    else float("nan")
                ),
                "values": avg_payoffs,
            },
            "player_total_payoff": {
                "mean": total_payoff_mean,
                "std": total_payoff_std,
                "values": total_payoffs,
            },
            "repetitions": len(repetition_results),
            "strategy_name": strategy_name,
        }

        # 分析はanalysis.ipynbで実行するため、ここでは基本的な統計のみ

        # リアルタイム統計表示
        logger.info(f"  {strategy_name} Statistics:")
        logger.info(f"    Cooperation Rate: {coop_mean:.3f} (±{coop_std:.3f})")
        logger.info(f"    Average Payoff: {payoff_mean:.3f} (±{payoff_std:.3f})")

        return {
            "repetition_details": repetition_results,
            "aggregated_analysis": aggregated_analysis,
            "summary": {
                "avg_cooperation_rate": coop_mean,
                "cooperation_rate_std": coop_std,
                "avg_payoff": payoff_mean,
                "payoff_std": payoff_std,
                "cooperation_range": (
                    f"{np.min(valid_coop_rates):.3f}-{np.max(valid_coop_rates):.3f}"
                    if valid_coop_rates
                    else "NaN-NaN"
                ),
                "payoff_range": (
                    f"{np.min(valid_avg_payoffs):.3f}-{np.max(valid_avg_payoffs):.3f}"
                    if valid_avg_payoffs
                    else "NaN-NaN"
                ),
            },
        }

    def _calculate_cooperation_rate(self, game_history: Dict[str, Any]) -> float:
        """ゲーム履歴から協力率を計算"""
        actions = game_history.get("actions", [])
        if not actions:
            return float("nan")  # 無効データとしてマーク

        cooperate_count = sum(
            1 for action in actions if action.get("player_action") == 1
        )
        return cooperate_count / len(actions)

    def _calculate_average_payoff(self, game_history: Dict[str, Any]) -> float:
        """ゲーム履歴から1ゲームあたりの合計ペイオフを計算"""
        actions = game_history.get("actions", [])
        if not actions:
            return float("nan")  # 無効データとしてマーク

        # 1ゲーム（全ラウンド）の合計ペイオフを返す
        total_payoff = sum(action.get("player_payoff", 0) for action in actions)
        return total_payoff

    def run_pd_games_with_llm(
        self,
        bfi_scores: Dict[str, float] = None,
        bfi_mode: str = "numbers_and_language",
        condition_name: str = "control",
        save_json: bool = True,
    ) -> Dict[str, Any]:
        """LLMとハードコーディングされた戦略で囚人のジレンマゲームを実行（複数回反復対応）"""
        logger.info(f"Running PD games with LLM (condition: {condition_name})")

        # 選択された戦略を取得
        selected_strategies = self.strategy_manager.get_selected_strategies()
        if not selected_strategies:
            logger.warning("No strategies selected. Using default strategies.")
            selected_strategies = DEFAULT_CONFIG["strategy_settings"]["strategies"]

        # 繰り返し回数の取得
        repetitions = self._get_setting(
            "pd_game", "repetitions", DEFAULT_CONFIG["pd_game_settings"]["repetitions"]
        )
        pd_iterations = self._get_setting(
            "pd_game", "iterations", DEFAULT_CONFIG["pd_game_settings"]["iterations"]
        )

        # プロンプトテンプレートとBFIモードの取得
        prompt_template = self._get_setting("pd_game", "prompt_template", "competitive")
        # bfi_modeは引数で受け取った値を使用（設定ファイルからは取得しない）

        logger.info(f"Number of repetitions per strategy: {repetitions}")
        logger.info(f"Using prompt template: {prompt_template}, BFI mode: {bfi_mode}")

        game_results = {}

        for strategy_name in selected_strategies:
            logger.info(f"Playing against {strategy_name} ({repetitions} times)")

            # 複数回のゲーム実行
            repetition_results = []

            for rep in range(repetitions):
                logger.info(f"  Repetition {rep + 1}/{repetitions}")

                # 各repetitionで新しい戦略インスタンスを作成
                # （前のrepetitionの履歴が残らないようにするため）
                strategy = self.strategy_manager.create_strategy(strategy_name)

                # ゲームの実行
                collect_reasoning = self._get_setting(
                    "pd_game", "collect_reasoning", False
                )
                game = PrisonersDilemmaGame(
                    llm_client=self.model_client,
                    opponent_strategy=strategy,
                    iterations=pd_iterations,
                    bfi_scores=bfi_scores,
                    prompt_template=prompt_template,
                    bfi_mode=bfi_mode,
                    collect_reasoning=collect_reasoning,
                )

                game_history = game.play_game()

                # 結果の保存（分析はanalysis.ipynbで実行）
                repetition_results.append(
                    {
                        "repetition": rep + 1,
                        "game_history": game_history,
                    }
                )

            # 複数回の結果を統合
            aggregated_results = self._aggregate_repetition_results(
                repetition_results, strategy_name
            )

            game_results[strategy_name] = aggregated_results

        # 結果の保存
        pd_results = {
            "condition": condition_name,
            "bfi_scores": bfi_scores,
            "selected_strategies": selected_strategies,
            "repetitions": repetitions,
            "game_results": game_results,
            "timestamp": datetime.now().isoformat(),
        }

        # JSONファイルの保存（save_jsonがTrueの場合のみ）
        if save_json:
            try:
                with open(
                    self.output_dir / f"{condition_name}_pd_games.json", "w"
                ) as f:
                    json.dump(pd_results, f, indent=2, cls=CustomJSONEncoder)
            except (TypeError, json.JSONDecodeError) as e:
                logger.error(f"PDゲーム結果の保存に失敗: {e}")
                logger.error(
                    "APIトークンの無駄遣いを防ぐため、プログラムを停止します。"
                )
                raise

        logger.info(f"PD games completed for condition: {condition_name}")
        return pd_results

    def run_personality_modification_experiment(
        self, target_traits: List[str], forced_score: int
    ) -> Dict[str, Any]:
        """性格特性の修正実験を実行（PDゲームのみ）"""
        logger.info(
            f"Running personality modification experiment for {target_traits} with forced score {forced_score}"
        )

        # コントロール条件のBFIスコアがベースラインとして利用可能かチェック
        if self.control_bfi_baseline is None:
            logger.error(
                "Control BFI baseline not available. This should not happen as control condition is run first."
            )
            raise ValueError(
                "Control BFI baseline is required for personality modification experiments"
            )

        modification_results = {}

        for target_trait in target_traits:
            logger.info(f"Modifying {target_trait} to forced score {forced_score}")

            condition_name = f"{target_trait}_score_{forced_score}"

            # 強制スコア設定を使用（コントロール条件をベースラインとして使用）
            bfi_iterations = self._get_setting(
                "bfi", "iterations", DEFAULT_CONFIG["bfi_settings"]["iterations"]
            )

            bfi_scores = self.bfi_analyzer.generate_forced_bfi_profile(
                target_trait=target_trait,
                forced_score=float(forced_score),
                control_baseline=self.control_bfi_baseline,
                iterations=bfi_iterations,
            )

            # 修正されたBFIスコアでPDゲームを実行（個別JSON保存はスキップ）
            pd_results = self.run_pd_games_with_llm(
                bfi_scores=bfi_scores["final_averages"],
                condition_name=condition_name,
                save_json=False,
            )

            modification_results[condition_name] = {
                "target_trait": target_trait,
                "forced_score": forced_score,
                "bfi_scores": bfi_scores,
                "control_baseline": self.control_bfi_baseline,
                "pd_results": pd_results,
            }

        # 結果の保存
        traits_str = "_".join(target_traits)
        try:
            with open(
                self.output_dir
                / f"{traits_str}_score_{forced_score}_modification_experiment.json",
                "w",
            ) as f:
                json.dump(modification_results, f, indent=2, cls=CustomJSONEncoder)

            logger.info(
                f"Modification experiment results saved to {traits_str}_score_{forced_score}_modification_experiment.json"
            )

        except (TypeError, json.JSONDecodeError) as e:
            logger.error(f"性格修正実験結果の保存に失敗: {e}")
            logger.error("APIトークンの無駄遣いを防ぐため、プログラムを停止します。")
            raise

        logger.info(
            f"Personality modification experiment completed for {target_traits} with score {forced_score}"
        )
        return modification_results


def expand_full_options(config: Dict[str, Any]) -> Dict[str, Any]:
    """'full'オプションを実際の選択肢に展開"""
    config = config.copy()

    # BFI modesの"full"を展開
    if "bfi_settings" in config and "modes" in config["bfi_settings"]:
        modes = config["bfi_settings"]["modes"]
        if "full" in modes:
            # "full"を除いて、利用可能なすべてのモードを追加
            available_modes = config["bfi_settings"].get(
                "available_modes",
                [
                    "numbers_only",
                    "language_only",
                    "numbers_and_language",
                    "bf_terms",
                ],
            )
            # "full"を除いた利用可能なモード
            full_modes = [mode for mode in available_modes if mode != "full"]
            # "full"を除いて、full_modesを追加
            config["bfi_settings"]["modes"] = [
                mode for mode in modes if mode != "full"
            ] + full_modes

    # PD game prompt templatesの"full"を展開
    if (
        "pd_game_settings" in config
        and "prompt_templates" in config["pd_game_settings"]
    ):
        templates = config["pd_game_settings"]["prompt_templates"]
        if "full" in templates:
            available_templates = config["pd_game_settings"].get(
                "available_templates", ["competitive", "neutral"]
            )
            full_templates = [
                template for template in available_templates if template != "full"
            ]
            config["pd_game_settings"]["prompt_templates"] = [
                template for template in templates if template != "full"
            ] + full_templates

    # Strategiesの"full"を展開
    if "strategy_settings" in config and "strategies" in config["strategy_settings"]:
        strategies = config["strategy_settings"]["strategies"]
        if "full" in strategies:
            available_strategies = config["strategy_settings"].get(
                "available_strategies",
                [
                    "TFT",
                    "STFT",
                    "GRIM",
                    "PAVLOV",
                    "ALLC",
                    "ALLD",
                    "RANDOM",
                    "UNFAIR_RANDOM",
                    "FIXED_SEQUENCE",
                    "GRADUAL",
                    "SOFT_MAJORITY",
                    "HARD_MAJORITY",
                ],
            )
            full_strategies = [
                strategy for strategy in available_strategies if strategy != "full"
            ]
            config["strategy_settings"]["strategies"] = [
                strategy for strategy in strategies if strategy != "full"
            ] + full_strategies

    # Personality modification target traitsの"full"を展開
    if (
        "personality_modification_settings" in config
        and "target_traits" in config["personality_modification_settings"]
    ):
        traits = config["personality_modification_settings"]["target_traits"]
        if "full" in traits:
            available_traits = config["personality_modification_settings"].get(
                "available_traits",
                [
                    "extraversion",
                    "agreeableness",
                    "conscientiousness",
                    "neuroticism",
                    "openness",
                ],
            )
            full_traits = [trait for trait in available_traits if trait != "full"]
            config["personality_modification_settings"]["target_traits"] = [
                trait for trait in traits if trait != "full"
            ] + full_traits

    return config


def load_config(config_path: str) -> Dict[str, Any]:
    """設定ファイルを読み込み"""
    # 設定ファイルのパスをプロジェクトルート基準に解決
    if Path(config_path).is_absolute():
        config_file_path = Path(config_path)
    else:
        config_file_path = PROJECT_ROOT / config_path

    if not config_file_path.exists():
        raise FileNotFoundError(
            f"設定ファイルが見つかりません: {config_file_path}\n"
            "実験を実行するには設定ファイルが必要です。\n"
            "config.jsonファイルを作成するか、--configオプションで正しいパスを指定してください。"
        )

    try:
        with open(config_file_path, "r") as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"設定ファイルのJSON形式が正しくありません: {config_file_path}\n"
            f"エラー詳細: {e}\n"
            "JSONの構文を確認してください。"
        )
    except Exception as e:
        raise RuntimeError(
            f"設定ファイルの読み込みに失敗しました: {config_file_path}\n"
            f"エラー詳細: {e}"
        )
    # "full"オプションを展開
    config = expand_full_options(config)

    # 必須項目の検証（不備があればここで停止）
    _validate_config(config)

    return config


# セクション名 → そのセクションで必須のキー一覧
_REQUIRED_KEYS: Dict[str, List[str]] = {
    "model_settings": ["model_name", "provider"],
    "bfi_settings": ["iterations", "modes"],
    "pd_game_settings": ["iterations", "repetitions", "prompt_templates"],
    "strategy_settings": ["strategies"],
    "personality_modification_settings": ["target_traits", "forced_scores"],
}


def _validate_config(config: Dict[str, Any]) -> None:
    """設定の必須項目を検証し、不備があれば実験開始前に停止する。"""
    errors: List[str] = []

    # 必須セクション・キーの存在チェック
    for section, keys in _REQUIRED_KEYS.items():
        if section not in config:
            errors.append(f"セクション '{section}' が config.json に存在しません。")
            continue
        for key in keys:
            if key not in config[section]:
                errors.append(f"'{section}.{key}' が config.json に存在しません。")

    # APIキーチェック（provider が openai の場合）
    provider = config.get("model_settings", {}).get("provider", "openai")
    api_key = (config.get("model_settings", {}).get("api_key") or "").strip()
    env_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if provider == "openai" and not api_key and not env_key:
        errors.append(
            "OpenAI APIキーが未設定です。model_settings.api_key または "
            "環境変数 OPENAI_API_KEY を設定してください。"
        )

    if errors:
        raise ValueError(
            "config.json に不備があるため実験を開始できません:\n"
            + "\n".join(f"  - {e}" for e in errors)
        )


def _parse_arguments() -> argparse.Namespace:
    """コマンドライン引数の解析"""
    parser = argparse.ArgumentParser(description="Personality and PD Research")
    parser.add_argument(
        "--config", type=str, default="config.json", help="Configuration file path"
    )
    return parser.parse_args()


def _setup_strategies(research: PersonalityPDResearch, config: Dict[str, Any]):
    """戦略設定の処理"""
    strategy_settings = config.get("strategy_settings", {})

    strategies = strategy_settings.get("strategies", [])
    if strategies:
        research.strategy_manager.select_strategies(strategies)
        logger.info(f"Selected strategies from config: {strategies}")
    else:
        logger.warning("No strategies specified in config. Using default strategies.")
        default_strategies = DEFAULT_CONFIG["strategy_settings"]["strategies"]
        research.strategy_manager.select_strategies(default_strategies)
        logger.info(f"Using default strategies: {default_strategies}")


def _get_experiment_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """実験設定の取得"""
    bfi_settings = config.get("bfi_settings", {})
    pd_game_settings = config.get("pd_game_settings", {})
    personality_settings = config.get("personality_modification_settings", {})

    return {
        "bfi_modes": bfi_settings.get("modes", ["numbers_and_language"]),
        "prompt_templates": pd_game_settings.get("prompt_templates", ["competitive"]),
        "target_traits": personality_settings.get(
            "target_traits", ["extraversion", "agreeableness"]
        ),
        "forced_scores": personality_settings.get("forced_scores", [1, 5]),
    }


@contextmanager
def _temporary_config_update(
    research: PersonalityPDResearch, bfi_mode: str, prompt_template: str
):
    """設定の一時的変更をコンテキストマネージャーで管理"""
    # 元の設定を保存
    original_config = {
        "bfi_mode": research.config.get("bfi_settings", {}).get(
            "mode", "numbers_and_language"
        ),
        "prompt_template": research.config.get("pd_game_settings", {}).get(
            "prompt_template", "competitive"
        ),
        "prompt_templates": research.config.get("pd_game_settings", {}).get(
            "prompt_templates", ["competitive"]
        ),
    }

    try:
        # 設定を更新
        if "bfi_settings" not in research.config:
            research.config["bfi_settings"] = {}
        if "pd_game_settings" not in research.config:
            research.config["pd_game_settings"] = {}

        research.config["bfi_settings"]["mode"] = bfi_mode
        research.config["pd_game_settings"]["prompt_template"] = prompt_template
        research.config["pd_game_settings"]["prompt_templates"] = [prompt_template]

        yield research

    finally:
        # 設定を元に戻す
        research.config["bfi_settings"]["mode"] = original_config["bfi_mode"]
        research.config["pd_game_settings"]["prompt_template"] = original_config[
            "prompt_template"
        ]
        research.config["pd_game_settings"]["prompt_templates"] = original_config[
            "prompt_templates"
        ]


def _run_template_experiment(
    research: PersonalityPDResearch,
    bfi_mode: str,
    prompt_template: str,
    experiment_config: Dict[str, Any],
    master_prompt_logger: PromptLogger,
):
    """
    プロンプトテンプレートごとの実験実行

    【この関数の役割】
    特定のBFIモードとプロンプトテンプレートの組み合わせで実験を実行します。

    【実行内容】
    1. コントロール条件でのPDゲーム
       - BFIモードに応じて、BFIスコアあり/なしでゲームを実行
       - 複数の戦略（TFT、GRIM等）と対戦

    2. 性格特性操作実験（BFIプロンプトありの場合のみ）
       - 各性格特性（外向性、協調性等）を1点または5点に強制設定
       - 操作後の性格スコアで再度BFI質問に回答
       - 操作後の性格スコアでPDゲームを実行

    3. CSV出力
       - この条件での実験結果をCSV形式で出力
       - 論文用の分析データとして使用されます

    【注意】
    - `no_prompt`モードでは性格修正実験は実行されません（コントロール条件のみ）
    - 各条件での結果はタイムスタンプ付きのディレクトリに保存されます
    """
    logger.info(
        f"Running experiments with BFI mode: {bfi_mode}, Prompt template: {prompt_template}"
    )

    with _temporary_config_update(research, bfi_mode, prompt_template):
        # プロンプトテンプレートごとのサブディレクトリを作成
        template_output_dir = (
            research.base_output_dir / f"BFI{bfi_mode}_PD{prompt_template}"
        )
        template_output_dir.mkdir(exist_ok=True)
        research.output_dir = template_output_dir

        # プロンプトロガーとCSV出力を更新
        template_prompt_logger = PromptLogger(template_output_dir)
        research.prompt_logger = template_prompt_logger
        research.model_client.prompt_logger = (
            template_prompt_logger  # ModelClientのプロンプトロガーも更新
        )
        research.csv_exporter = CSVExporter(template_output_dir, research.config)

        # プロンプトテンプレート固有のセッションIDを設定
        research.csv_exporter.session_id = (
            f"{research.csv_exporter.session_id}_{prompt_template}"
        )

        # 2-1. コントロール条件でのPDゲーム
        logger.info(
            f"Step 2-1: Running control PD games with {prompt_template} template"
        )

        # BFIモードに応じてBFIスコアを決定
        if bfi_mode == "no_prompt":
            # BFIプロンプトなしの場合：BFIスコアなしでPDゲーム
            control_pd_results = research.run_pd_games_with_llm(
                bfi_scores=None,
                bfi_mode=bfi_mode,
                condition_name="control",
            )
            modification_results = {}  # 性格修正実験は実行しない
        else:
            # BFIプロンプトありの場合：BFIスコアありでPDゲーム
            control_pd_results = research.run_pd_games_with_llm(
                bfi_scores=(
                    research.control_bfi_baseline["final_averages"]
                    if research.control_bfi_baseline
                    else None
                ),
                bfi_mode=bfi_mode,
                condition_name="control",
            )

            # 2-2. 性格特性修正実験を実行（BFIプロンプトありの場合のみ）
            logger.info(
                f"Step 2-2: Running personality modification experiments with {prompt_template} template"
            )
            modification_results = {}
            for forced_score in experiment_config["forced_scores"]:
                for trait in experiment_config["target_traits"]:
                    logger.info(
                        f"Running modification experiment: {trait} = {forced_score}"
                    )
                    result = research.run_personality_modification_experiment(
                        [trait], forced_score
                    )
                    # 結果を格納（CSV出力用の形式に変換）
                    condition_name = f"{trait}_score_{forced_score}"
                    modification_results[condition_name] = result[condition_name]

        # 3. このプロンプトテンプレートの結果をCSV出力
        logger.info(f"Step 3: Exporting CSV results for {prompt_template} template")

        # このテンプレートのプロンプトログを統合プロンプトロガーにマージ
        master_prompt_logger.merge_logs(template_prompt_logger)

        # 全生データのCSV出力（分析用）
        research.csv_exporter.export_all_raw_data(
            {"control_pd_results": control_pd_results, **modification_results},
            research.control_bfi_baseline,
            master_prompt_logger,
            research.start_time,
            error_logs=None,
        )


def main():
    """
    メイン関数

    【実験の実行フロー】
    この関数は以下の順序で実験を実行します：

    1. 初期化フェーズ
       - コマンドライン引数の解析
       - 設定ファイル（config.json）の読み込み
       - 実験オブジェクト（PersonalityPDResearch）の初期化
       - 戦略の設定

    2. コントロール条件の実行
       - ペルソナなしのLLMにBFI質問を回答させ、ベースラインの性格スコアを測定
       - この結果は全実験で共通のベースラインとして使用されます

    3. 実験設定の取得
       - config.jsonからBFIモード、プロンプトテンプレート、対象性格特性などを取得

    4. 各条件での実験実行
       - 各BFIモードとプロンプトテンプレートの組み合わせで以下を実行：
         a) コントロール条件でのPDゲーム
         b) 性格特性修正実験（各特性を1点または5点に設定してゲーム）
       - 結果はCSV形式で出力されます

    5. 結果の統合と保存
       - すべてのプロンプトログを統合して保存
       - 実験完了の通知
    """
    # コマンドライン引数の解析（設定ファイルのパスなど）
    args = _parse_arguments()

    # 設定ファイルの読み込み（config.jsonまたはカスタムファイル）
    config = load_config(args.config)

    # 実験オブジェクトの初期化（モデルクライアント、BFI分析器などを準備）
    research = PersonalityPDResearch(config)

    # 戦略の設定（config.jsonまたはコマンドライン引数から戦略を選択）
    _setup_strategies(research, config)

    # 実験の実行（設定に基づいて自動実行）
    logger.info("Starting comprehensive experiment based on config settings")

    # Step 1: コントロール条件でのBFIスコア算出（全実験を通して1回のみ）
    # ペルソナなしのLLMにBFI質問を回答させ、ベースラインの性格スコアを測定
    # この結果は後続の実験で使用されます
    logger.info("Step 1: Running control condition (BFI baseline) - 全実験共通")
    control_results = research.run_control_condition(bfi_mode="numbers_and_language")

    # Step 2: 実験設定の取得
    # config.jsonからBFIモード、プロンプトテンプレート、対象性格特性、強制スコアなどを取得
    experiment_config = _get_experiment_config(config)

    logger.info(f"Step 2: Running experiments with multiple prompt templates")
    logger.info(f"  BFI modes: {experiment_config['bfi_modes']}")
    logger.info(f"  Prompt templates: {experiment_config['prompt_templates']}")
    logger.info(f"  Target traits: {experiment_config['target_traits']}")
    logger.info(f"  Forced scores: {experiment_config['forced_scores']}")

    # 統合プロンプトロガー（全てのテンプレートのログを統合）
    # すべての実験条件でのLLMとのやり取りを1つのログファイルにまとめます
    master_prompt_logger = PromptLogger(research.base_output_dir)
    master_prompt_logger.merge_logs(research.prompt_logger)

    # Step 3: 各BFIモードとプロンプトテンプレートの組み合わせで実験
    # 例: numbers_and_language × competitive, numbers_and_language × neutral など
    # 各組み合わせについて、コントロール条件と性格修正実験を実行します
    for bfi_mode in experiment_config["bfi_modes"]:
        for prompt_template in experiment_config["prompt_templates"]:
            _run_template_experiment(
                research,
                bfi_mode,
                prompt_template,
                experiment_config,
                master_prompt_logger,
            )

    logger.info("All experiments completed successfully")

    # 統合プロンプトログの保存とサマリー表示
    # すべての実験条件でのLLMとのやり取りを保存し、統計情報を表示します
    master_prompt_logger.save_logs()
    master_prompt_logger.print_summary()


if __name__ == "__main__":
    main()
