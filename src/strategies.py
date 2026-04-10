"""
戦略モジュール
nicer_than_humans_originのhard_coded_pd_strategies.pyとblind_pd_strategies.pyを参考にして作成
戦略選択機能を追加

【このファイルの役割】
このファイルは、囚人のジレンマゲームでAIと対戦する「対戦相手の戦略」を実装します。

"""

# 【ライブラリの説明】
import numpy as np  # 数値計算ライブラリ（確率計算用）
import logging  # ログ記録（実行状況の記録）
from typing import List, Dict, Any, Optional  # 型ヒント（変数の型を明示）
from dataclasses import dataclass  # データクラス（構造化されたデータを簡単に作る）

# ログ記録用のオブジェクトを作成（このファイル専用の記録係）
logger = logging.getLogger(__name__)


@dataclass
class StrategyConfig:
    """
    戦略設定のデータクラス

    【このクラスの役割】
    各戦略の基本情報（説明、カテゴリ、パラメータ）を管理します。
    """

    description: str  # 戦略の説明文
    category: str  # 戦略のカテゴリ（"basic", "advanced", "random", "majority"）
    parameters: Optional[Dict[str, Any]] = None  # 戦略のパラメータ（設定値）


class StrategyManager:
    """
    戦略管理クラス

    【このクラスの役割】
    利用可能な戦略を管理し、実験で使用する戦略を選択する機能を提供します。

    """

    def __init__(self):
        # 【初期化処理】
        self.strategies = self._initialize_strategies()  # 利用可能な戦略の一覧
        self.selected_strategies = []  # 実験で使用する戦略のリスト

    def _initialize_strategies(self) -> Dict[str, StrategyConfig]:
        """
        戦略の初期化

        【このメソッドの役割】
        利用可能な全ての戦略とその設定を定義します。

        """
        return {
            # 【基本戦略】- ゲーム理論で有名な基本的な戦略
            "TFT": StrategyConfig(
                description="Tit for Tat - 相手の前回の行動を真似する",
                category="basic",
            ),
            "STFT": StrategyConfig(
                description="Suspicious Tit for Tat - 最初に裏切り、その後相手の前回の行動を真似する",
                category="basic",
            ),
            "GRIM": StrategyConfig(
                description="Grim - 一度裏切られたら永遠に裏切る",
                category="basic",
            ),
            "PAVLOV": StrategyConfig(
                description="Win-Stay, Lose-Shift - 同じ結果なら協力、異なる結果なら裏切り",
                category="basic",
            ),
            "ALLC": StrategyConfig(
                description="Always Cooperate - 常に協力する",
                category="basic",
            ),
            "ALLD": StrategyConfig(
                description="Always Defect - 常に裏切る", category="basic"
            ),
            # 【ランダム戦略】- 確率的に行動を決定する戦略
            "RANDOM": StrategyConfig(
                description="Random - ランダムに行動する（協力確率50%）",
                category="random",
                parameters={"cooperation_probability": 0.5},  # 協力する確率
            ),
            "UNFAIR_RANDOM": StrategyConfig(
                description="Unfair Random - 不公平な確率でランダムに行動する（協力確率30%）",
                category="random",
                parameters={"cooperation_probability": 0.3},  # 協力する確率
            ),
            # 【高度な戦略】- 複雑なルールを持つ戦略
            "FIXED_SEQUENCE": StrategyConfig(
                description="Fixed Sequence - 固定シーケンスで行動する",
                category="advanced",
                parameters={"sequence": [1, 1, 0, 1, 0, 0]},  # 行動の固定パターン
            ),
            "GRADUAL": StrategyConfig(
                description="Gradual - 段階的に報復する",
                category="advanced",
            ),
            # 【多数決戦略】- 過去の行動の多数決で決定する戦略
            "SOFT_MAJORITY": StrategyConfig(
                description="Soft Majority - 過去3回の多数決",
                category="majority",
            ),
            "HARD_MAJORITY": StrategyConfig(
                description="Hard Majority - 全履歴の多数決",
                category="majority",
            ),
        }

    def select_strategies(self, strategy_names: List[str]):
        """
        戦略を選択

        【このメソッドの役割】
        実験で使用する戦略を選択します。
        """
        for name in strategy_names:
            if name not in self.strategies:
                raise ValueError(f"Unknown strategy: {name}")
        self.selected_strategies = strategy_names.copy()
        logger.info(f"Selected strategies: {self.selected_strategies}")

    def get_selected_strategies(self) -> List[str]:
        """
        選択された戦略を取得

        【このメソッドの役割】
        現在選択されている戦略のリストを返します。
        """
        return self.selected_strategies.copy()

    def create_strategy(self, strategy_name: str):
        """
        戦略インスタンスを作成

        【このメソッドの役割】
        戦略名から実際の戦略オブジェクトを作成します。
        """
        # 【戦略名とクラスの対応表】
        strategies = {
            "TFT": TitForTat,  # Tit for Tat戦略
            "STFT": SuspiciousTitForTat,  # Suspicious Tit for Tat戦略
            "GRIM": Grim,  # Grim戦略
            "PAVLOV": WinStayLoseShift,  # Win-Stay, Lose-Shift戦略
            "ALLC": AlwaysCooperate,  # 常に協力戦略
            "ALLD": AlwaysDefect,  # 常に裏切り戦略
            "RANDOM": RandomStrategy,  # ランダム戦略
            "UNFAIR_RANDOM": RandomStrategy,  # 不公平ランダム戦略（cooperation_probability で差別化）
            "FIXED_SEQUENCE": FixedSequence,  # 固定シーケンス戦略
            "GRADUAL": Gradual,  # Gradual戦略
            "SOFT_MAJORITY": SoftMajority,  # Soft Majority戦略
            "HARD_MAJORITY": HardMajority,  # Hard Majority戦略
        }

        if strategy_name not in strategies:
            raise ValueError(f"Unknown strategy: {strategy_name}")

        # 【パラメータがある場合は取得】
        # 戦略に設定値（パラメータ）がある場合は、それを使って戦略を作成
        config = self.strategies.get(strategy_name)
        if config and config.parameters:
            return strategies[strategy_name](
                **config.parameters
            )  # パラメータ付きで作成
        else:
            return strategies[strategy_name]()  # パラメータなしで作成


class Strategy:
    """
    戦略の基底クラス

    【このクラスの役割】
    全ての戦略の基本となるクラスです。共通の機能を提供します。

    【大学一年生向けの説明】
    このクラスは、戦略の「基本設計図」のようなものです。
    全ての戦略が持つべき基本的な機能（名前、履歴管理など）を定義します。
    """

    def __init__(self, name: str):
        # 【初期化処理】
        self.name = name  # 戦略の名前
        self.history = []  # 相手の行動履歴

    def play(self) -> int:
        """
        アクションを決定（0 = Defect, 1 = Cooperate）

        【このメソッドの役割】
        戦略に基づいて次の行動を決定します。

        【大学一年生向けの説明】
        このメソッドは、戦略の「核心部分」です。
        各戦略が独自のルールで「協力するか裏切るか」を決めます。
        """
        raise NotImplementedError  # 子クラスで実装する必要がある

    def update_history(self, action: int):
        """
        履歴を更新

        【このメソッドの役割】
        相手の行動を履歴に記録します。

        【大学一年生向けの説明】
        このメソッドは、相手が何をしたかを「記録」する機能です。
        多くの戦略が過去の行動を参考にするため、この記録が重要です。
        """
        self.history.append(action)


class TitForTat(Strategy):
    """
    Tit for Tat戦略

    【この戦略の特徴】
    最も有名な戦略の一つ。相手の前回の行動を真似します。

    【大学一年生向けの説明】
    - 最初は協力から始める
    - その後は相手の前回の行動を真似する
    - 「目には目を、歯には歯を」の戦略
    - 協力的な相手には協力し、裏切る相手には裏切る
    """

    def __init__(self):
        super().__init__("TitForTat")

    def play(self) -> int:
        """
        アクションを決定

        【戦略のルール】
        1. 最初のラウンドは協力
        2. その後は相手の前回の行動を真似
        """
        if not self.history:
            return 1  # 最初は協力
        return self.history[-1]  # 前回の相手の行動を真似


class SuspiciousTitForTat(Strategy):
    """
    Suspicious Tit for Tat戦略

    【この戦略の特徴】
    TFTの「疑い深い」バージョン。最初に裏切りから始めます。

    【大学一年生向けの説明】
    - 最初は裏切りから始める（相手を試す）
    - その後は相手の前回の行動を真似する
    - TFTよりも「疑い深い」性格
    - 相手が協力的なら協力に戻る
    """

    def __init__(self):
        super().__init__("SuspiciousTitForTat")

    def play(self) -> int:
        """
        アクションを決定

        【戦略のルール】
        1. 最初のラウンドは裏切り
        2. その後は相手の前回の行動を真似
        """
        if not self.history:
            return 0  # 最初は裏切り
        return self.history[-1]  # 前回の相手の行動を真似


class Grim(Strategy):
    """
    Grim戦略（一度裏切られたら永遠に裏切る）

    【この戦略の特徴】
    「冷酷な」戦略。一度裏切られたら永遠に裏切り続けます。

    【大学一年生向けの説明】
    - 最初は協力から始める
    - 相手が一度でも裏切ったら、永遠に裏切り続ける
    - 「許さない」性格の戦略
    - 相手に「裏切ったら終わり」という警告を与える
    """

    def __init__(self):
        super().__init__("Grim")
        self.triggered = False  # 裏切りが発生したかどうかのフラグ

    def play(self) -> int:
        """
        アクションを決定

        【戦略のルール】
        1. 最初は協力
        2. 相手が一度でも裏切ったら、永遠に裏切り続ける
        """
        if not self.history:
            return 1  # 最初は協力

        # 相手が一度でも裏切ったら永遠に裏切る
        if 0 in self.history:  # 履歴に裏切り（0）があるかチェック
            self.triggered = True

        return (
            0 if self.triggered else 1
        )  # 裏切りが発生していれば裏切り、そうでなければ協力


class WinStayLoseShift(Strategy):
    """Win-Stay, Lose-Shift戦略（Pavlov）"""

    def __init__(self):
        super().__init__("WinStayLoseShift")

    def play(self) -> int:
        if len(self.history) < 2:
            return 1  # 最初は協力

        # 前回の結果を確認
        last_my_action = self.history[-2] if len(self.history) >= 2 else 1
        last_opponent_action = self.history[-1]

        # 同じ結果なら協力、異なる結果なら裏切り
        if last_my_action == last_opponent_action:
            return 1  # 協力
        else:
            return 0  # 裏切り


class AlwaysCooperate(Strategy):
    """
    常に協力する戦略

    【この戦略の特徴】
    最も単純な戦略。常に協力し続けます。

    【大学一年生向けの説明】
    - 常に協力する
    - 相手が何をしても協力し続ける
    - 「善人」の戦略
    - 協力的な相手には良い結果をもたらすが、裏切る相手には不利
    """

    def __init__(self):
        super().__init__("AlwaysCooperate")

    def play(self) -> int:
        """
        アクションを決定

        【戦略のルール】
        常に協力（1）を返す
        """
        return 1


class AlwaysDefect(Strategy):
    """
    常に裏切る戦略

    【この戦略の特徴】
    最も攻撃的な戦略。常に裏切り続けます。

    【大学一年生向けの説明】
    - 常に裏切る
    - 相手が何をしても裏切り続ける
    - 「悪人」の戦略
    - 短期的には得をするが、長期的には不利になることが多い
    """

    def __init__(self):
        super().__init__("AlwaysDefect")

    def play(self) -> int:
        """
        アクションを決定

        【戦略のルール】
        常に裏切り（0）を返す
        """
        return 0


class RandomStrategy(Strategy):
    """
    ランダム戦略

    【この戦略の特徴】
    確率的に行動を決定する戦略。デフォルトは50%の確率で協力。

    【大学一年生向けの説明】
    - ランダムに行動を決める
    - デフォルトは50%の確率で協力、50%の確率で裏切り
    - 予測不可能な行動を取る
    - 相手にとって「読みにくい」戦略
    """

    def __init__(self, cooperation_probability: float = 0.5):
        super().__init__("RandomStrategy")
        self.cooperation_probability = cooperation_probability  # 協力する確率
        self.rng = np.random.default_rng()  # 乱数生成器

    def play(self) -> int:
        """
        アクションを決定

        【戦略のルール】
        設定された確率に基づいてランダムに行動を決定
        """
        return self.rng.choice(
            [0, 1], p=[1 - self.cooperation_probability, self.cooperation_probability]
        )  # 裏切りの確率、協力の確率



class FixedSequence(Strategy):
    """固定シーケンス戦略"""

    def __init__(self, sequence: List[int]):
        super().__init__("FixedSequence")
        self.sequence = sequence.copy()
        self.current_index = 0

    def play(self) -> int:
        if self.current_index >= len(self.sequence):
            # シーケンスが終わったら最後の行動を繰り返す
            return self.sequence[-1]

        action = self.sequence[self.current_index]
        self.current_index += 1
        return action


class Gradual(Strategy):
    """Gradual戦略"""

    def __init__(self):
        super().__init__("Gradual")
        self.defection_count = 0
        self.phase = 0

    def play(self) -> int:
        if not self.history:
            return 1  # 最初は協力

        # 相手の裏切り回数をカウント
        if self.history[-1] == 0:
            self.defection_count += 1

        # フェーズに基づいて行動を決定
        if self.defection_count == 0:
            return 1  # 協力
        elif self.defection_count == 1:
            return 0  # 裏切り
        elif self.defection_count == 2:
            return 0  # 裏切り
        elif self.defection_count == 3:
            return 0  # 裏切り
        elif self.defection_count == 4:
            return 0  # 裏切り
        elif self.defection_count == 5:
            return 0  # 裏切り
        else:
            # 6回目以降は2回協力してから2回裏切る
            phase = (self.defection_count - 6) % 4
            if phase < 2:
                return 1  # 協力
            else:
                return 0  # 裏切り


class SoftMajority(Strategy):
    """Soft Majority戦略"""

    def __init__(self):
        super().__init__("SoftMajority")

    def play(self) -> int:
        if len(self.history) < 3:
            return 1  # 最初は協力

        # 過去3回の相手の行動の多数決
        recent_actions = self.history[-3:]
        cooperation_count = sum(recent_actions)

        if cooperation_count >= 2:
            return 1  # 協力
        else:
            return 0  # 裏切り


class HardMajority(Strategy):
    """Hard Majority戦略"""

    def __init__(self):
        super().__init__("HardMajority")

    def play(self) -> int:
        if not self.history:
            return 1  # 最初は協力

        # 全履歴の相手の行動の多数決
        cooperation_count = sum(self.history)
        total_actions = len(self.history)

        if cooperation_count > total_actions / 2:
            return 1  # 協力
        else:
            return 0  # 裏切り
