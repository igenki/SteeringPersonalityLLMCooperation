"""
囚人のジレンマゲームモジュール
nicer_than_humans_originのtwo_players_pd.pyを参考にして作成

【このファイルの役割】
このファイルは、AIと対戦相手の戦略で「囚人のジレンマゲーム」を実行する機能を提供します。

"""

# 【ライブラリの説明】
import logging  # ログ記録（実行状況の記録）
from typing import List, Dict, Any, Optional  # 型ヒント（変数の型を明示）
from dataclasses import dataclass  # データクラス（構造化されたデータを簡単に作る）

# プロンプトテンプレート関連のインポート
from .prompt_templates import (
    get_prompt_template,  # プロンプトテンプレートを取得する関数
    GameAction,  # ゲームアクションデータクラス
)

# ログ記録用のオブジェクトを作成（このファイル専用の記録係）
logger = logging.getLogger(__name__)


@dataclass
class GameHistory:
    """
    ゲーム履歴のデータクラス

    【このクラスの役割】
    ゲーム全体の結果をまとめて記録します。


    """

    actions: List[GameAction]  # 各ラウンドの詳細な記録のリスト
    total_rounds: int  # ゲームの総ラウンド数
    player_total_payoff: float  # プレイヤーの合計得点
    opponent_total_payoff: float  # 対戦相手の合計得点
    overall_reasoning: Optional[str] = None  # ゲーム全体の行動理由

    def to_dict(self) -> Dict[str, Any]:
        """
        辞書形式に変換

        【このメソッドの役割】
        ゲーム履歴全体を辞書の形に変換して、保存や処理しやすくします。

        """
        return {
            "actions": [
                action.to_dict() for action in self.actions
            ],  # 各ラウンドの記録を辞書に変換
            "total_rounds": self.total_rounds,
            "player_total_payoff": self.player_total_payoff,
            "opponent_total_payoff": self.opponent_total_payoff,
            "overall_reasoning": self.overall_reasoning,
        }


class PrisonersDilemmaGame:
    """
    囚人のジレンマゲームクラス

    【このクラスの役割】
    AIと対戦相手の戦略で囚人のジレンマゲームを実行し、結果を記録します。


    """

    def __init__(
        self,
        llm_client,  # AIとの通信を担当するオブジェクト
        opponent_strategy,  # 対戦相手の戦略（TFT、GRIM等）
        iterations: int = 10,  # ゲームのラウンド数
        bfi_scores: Optional[Dict[str, float]] = None,  # AIの性格設定
        prompt_template: str = "competitive",  # 使用するプロンプトテンプレート
        bfi_mode: str = "numbers_and_language",  # BFIモード
        collect_reasoning: bool = False,  # 行動理由を収集するかどうか
    ):
        # 【基本設定の保存】
        self.llm_client = llm_client  # AIとの通信を担当するオブジェクト
        self.opponent_strategy = opponent_strategy  # 対戦相手の戦略
        self.iterations = iterations  # ゲームのラウンド数
        self.bfi_scores = bfi_scores  # AIの性格設定（あれば）
        self.bfi_mode = bfi_mode  # BFIモード
        self.collect_reasoning = collect_reasoning  # 行動理由を収集するかどうか

        # 対戦相手の戦略名を取得
        self.strategy_name = (
            opponent_strategy.name
            if hasattr(opponent_strategy, "name")
            else str(opponent_strategy)
        )

        # 【プロンプトテンプレートの初期化】
        # AIにゲームの説明をするためのテンプレートを取得
        self.prompt_template = get_prompt_template(prompt_template, bfi_mode)

        # 【囚人のジレンマの報酬設定】
        # Axelrod's tournament payoff（有名なゲーム理論の設定）
        # 各行動の組み合わせに対する報酬を定義
        self.payoff_matrix = {
            (1, 1): (3, 3),  # 両方が協力：両方とも3点
            (1, 0): (0, 5),  # プレイヤー協力、相手裏切り：プレイヤー0点、相手5点
            (0, 1): (5, 0),  # プレイヤー裏切り、相手協力：プレイヤー5点、相手0点
            (0, 0): (1, 1),  # 両方が裏切り：両方とも1点
        }

        # 【ゲーム記録用のリスト】
        self.game_history = []  # 各ラウンドの詳細記録
        self.player_actions = []  # プレイヤー（AI）の行動履歴
        self.opponent_actions = []  # 対戦相手の行動履歴

    def _get_payoff(self, player_action: int, opponent_action: int) -> tuple:
        """
        報酬の取得

        【このメソッドの役割】
        プレイヤーと対戦相手の行動に基づいて、それぞれの報酬を計算します。

        """
        return self.payoff_matrix[(player_action, opponent_action)]

    def _generate_llm_action(self, round_num: int) -> int:
        """
        LLMのアクションを生成（プロンプトテンプレート使用）

        【このメソッドの役割】
        AIにゲームの状況を説明して、「協力するか裏切るか」を決めてもらいます。

        """

        # 【プロンプトテンプレートを使用して完全なプロンプトを生成】
        # AIに送る質問文を作成（ゲームの説明、現在の状況、判断を求める）
        user_prompt = self.prompt_template.generate_full_prompt(
            bfi_scores=self.bfi_scores,  # AIの性格設定
            iterations=self.iterations,  # 総ラウンド数
            payoff_matrix=self.payoff_matrix,  # 報酬表
            game_history=self.game_history,  # これまでのゲーム履歴
            current_round=round_num,  # 現在のラウンド番号
        )

        try:
            # 【AIに質問を送信】
            # 入力プロンプトと出力レスポンスは自動的にprompt_loggerに記録される
            response = self.llm_client.generate_text(
                prompt=user_prompt,  # 作成した質問文
                system_prompt="",  # システムプロンプトは既にユーザープロンプトに含まれている
                max_new_tokens=5,  # 最大文字数（「協力」か「裏切り」の短い回答を期待）
                temperature=0.7,  # 創造性レベル
                experiment_type=(
                    "control_pd"  # コントロール条件のゲーム
                    if not hasattr(self, "target_traits") or not self.target_traits
                    else "modification"  # 性格修正実験のゲーム
                ),
                prompt_type="game_decision",  # プロンプトの種類
                prompt_template=(
                    self.prompt_template.template_name
                    if hasattr(self.prompt_template, "template_name")
                    else "competitive"
                ),
                strategy=self.strategy_name,  # 対戦相手の戦略名
                round_number=round_num,  # ラウンド番号
                bfi_mode=self.bfi_mode,  # BFIモード
            )

            # 【AIの回答を処理】
            response = response.strip().upper()  # 余分な空白を削除し、大文字に変換

            # 【より堅牢な応答解析】
            # AIの回答から「協力」か「裏切り」かを判断
            if any(word in response for word in ["COOPERATE", "COOPER", "COOP", "1"]):
                return 1  # 協力
            elif any(word in response for word in ["DEFECT", "DEFE", "DEF", "0"]):
                return 0  # 裏切り
            else:
                # 【エラー処理】
                # 理解できない回答の場合の処理
                short_response = (
                    response[:100] + "..." if len(response) > 100 else response
                )
                logger.warning(
                    f'Could not parse action from response: {short_response}. Defaulting to "Cooperate".'
                )
                return 1  # デフォルトで「協力」

        except Exception as e:
            # 【エラー処理】
            # AIとの通信で問題が起きた場合
            logger.error(f"Error generating LLM action: {e}")
            return 1  # デフォルトで「協力」

    def _generate_overall_reasoning(self) -> str:
        """
        LLMのゲーム全体の行動理由を生成

        【このメソッドの役割】
        AIにゲーム全体の状況を説明して、行動の理由を説明してもらいます。
        """
        # 【プロンプトテンプレートを使用して行動理由プロンプトを生成】
        user_prompt = self.prompt_template.generate_reasoning_prompt(
            bfi_scores=self.bfi_scores,
            iterations=self.iterations,
            payoff_matrix=self.payoff_matrix,
            game_history=self.game_history,
        )

        try:
            # 【AIに質問を送信】
            # 入力プロンプトと出力レスポンスは自動的にprompt_loggerに記録される
            response = self.llm_client.generate_text(
                prompt=user_prompt,
                system_prompt="",
                max_new_tokens=500,  # ゲーム全体の理由説明なので長めに設定
                temperature=0.7,
                experiment_type=(
                    "control_pd"
                    if not hasattr(self, "target_traits") or not self.target_traits
                    else "modification"
                ),
                prompt_type="overall_reasoning",
                prompt_template=(
                    self.prompt_template.template_name
                    if hasattr(self.prompt_template, "template_name")
                    else "competitive"
                ),
                strategy=self.strategy_name,
                round_number=self.iterations,  # ゲーム終了時
                bfi_mode=self.bfi_mode,  # BFIモード
            )

            return response.strip()

        except Exception as e:
            logger.error(f"Error generating overall reasoning: {e}")
            return "No reasoning provided due to error"

    def _get_opponent_action(self, round_num: int) -> int:
        """
        対戦相手のアクションを取得

        【このメソッドの役割】
        対戦相手の戦略（TFT、GRIM等）に基づいて、次の行動を決定します。
        """
        try:
            # 対戦相手の戦略に「play」メソッドがあるかチェック
            if hasattr(self.opponent_strategy, "play"):
                return self.opponent_strategy.play()  # 戦略に従って行動を決定
            else:
                # 戦略に「play」メソッドがない場合のエラー処理
                logger.error(
                    f"Opponent strategy {self.opponent_strategy} does not have play method"
                )
                return 1  # デフォルトで「協力」
        except Exception as e:
            # 戦略の実行で問題が起きた場合のエラー処理
            logger.error(f"Error getting opponent action: {e}")
            return 1  # デフォルトで「協力」

    def play_game(self) -> GameHistory:
        """
        ゲームを実行

        【このメソッドの役割】
        設定された回数だけゲームを繰り返し、結果を記録します。

        """
        logger.info(f"Starting Prisoner's Dilemma game with {self.iterations} rounds")

        # 【合計得点の初期化】
        player_total_payoff = 0  # プレイヤー（AI）の合計得点
        opponent_total_payoff = 0  # 対戦相手の合計得点

        # 【各ラウンドの実行】
        for round_num in range(1, self.iterations + 1):
            logger.debug(f"Playing round {round_num}")

            # 【LLMのアクションを取得】
            # AIにゲームの状況を説明して、行動を決めてもらう
            player_action = self._generate_llm_action(round_num)
            self.player_actions.append(player_action)  # 行動履歴に追加

            # 【対戦相手のアクションを取得】
            # 対戦相手の戦略に従って行動を決定
            opponent_action = self._get_opponent_action(round_num)
            self.opponent_actions.append(opponent_action)  # 行動履歴に追加

            # 【報酬を計算】
            # 2人の行動に基づいて、それぞれの得点を計算
            player_payoff, opponent_payoff = self._get_payoff(
                player_action, opponent_action
            )
            player_total_payoff += player_payoff  # 合計得点に加算
            opponent_total_payoff += opponent_payoff  # 合計得点に加算

            # 【ゲームアクションを記録】
            # このラウンドの詳細な記録を作成
            game_action = GameAction(
                round_num=round_num,
                player_action=player_action,
                opponent_action=opponent_action,
                player_payoff=player_payoff,
                opponent_payoff=opponent_payoff,
                player_reasoning=None,  # ラウンド別の理由は収集しない
            )
            self.game_history.append(game_action)  # ゲーム履歴に追加

            # 【戦略の履歴を更新】
            # 対戦相手の戦略に、プレイヤーの行動を教える
            # （TFT戦略など、過去の行動を参考にする戦略のため）
            if hasattr(self.opponent_strategy, "update_history"):
                self.opponent_strategy.update_history(player_action)

            # 【デバッグ用のログ出力】
            logger.debug(
                f"Round {round_num}: Player {'Cooperate' if player_action == 1 else 'Defect'}, "
                f"Opponent {'Cooperate' if opponent_action == 1 else 'Defect'}"
            )

        # 【ゲーム全体の行動理由を取得（オプション）】
        overall_reasoning = None
        if self.collect_reasoning:
            overall_reasoning = self._generate_overall_reasoning()

        # 【ゲーム履歴を作成】
        # ゲーム全体の結果をまとめる
        game_history = GameHistory(
            actions=self.game_history,  # 各ラウンドの詳細記録
            total_rounds=self.iterations,  # 総ラウンド数
            player_total_payoff=player_total_payoff,  # プレイヤーの合計得点
            opponent_total_payoff=opponent_total_payoff,  # 対戦相手の合計得点
            overall_reasoning=overall_reasoning,  # ゲーム全体の行動理由
        )

        # 【ゲーム完了のログ出力】
        logger.info(
            f"Game completed. Player total payoff: {player_total_payoff}, "
            f"Opponent total payoff: {opponent_total_payoff}"
        )

        return game_history  # ゲーム履歴を返す
