"""
プロンプトテンプレートモジュール
異なるフレーミングや指示スタイルでのプロンプト生成を管理
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum


class BFIMode(Enum):
    """BFIスコアの提示方法"""

    NUMBERS_ONLY = "numbers_only"  # 数値のみ [3.1, 4.5, 2.8, 1.9, 4.2]
    NATURAL_LANGUAGE_ONLY = "language_only"  # 自然言語記述のみ
    NUMBERS_AND_NATURAL = "numbers_and_language"  # 数値 + 自然言語記述（デフォルト）
    NUMBERS_WITH_BRIEF_DESCRIPTIONS = "numbers_with_brief_desc"  # 数値 + 簡潔な特性記述（一行形式）
    COMPREHENSIVE = "comprehensive"  # 配列形式 + Trait Interpretation + 個別特性記述（最も包括的）
    BIGFIVE_TERMS_EN = "bf_terms"  # BigFive理論の標準用語（英語）
    NO_PROMPT = "no_prompt"  # BFIプロンプトを全く与えない


@dataclass
class GameAction:
    """ゲームアクションデータ（履歴表示用・結果保存用）"""

    round_num: int
    player_action: int
    opponent_action: int
    player_payoff: float
    opponent_payoff: float
    player_reasoning: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PromptTemplate(ABC):
    """プロンプトテンプレートの基底クラス"""

    def __init__(
        self,
        name: str,
        description: str,
        bfi_mode: BFIMode = BFIMode.NUMBERS_AND_NATURAL,
    ):
        self.name = name
        self.description = description
        self.bfi_mode = bfi_mode

    @abstractmethod
    def generate_game_rules_prompt(self, iterations: int, payoff_matrix: Dict) -> str:
        """ゲームルールプロンプトを生成"""
        pass

    def generate_bfi_prompt(self, bfi_scores: Dict[str, float]) -> str:
        """BFI性格プロファイルプロンプトを生成（モード対応）"""
        if self.bfi_mode == BFIMode.NO_PROMPT:
            return ""
        elif self.bfi_mode == BFIMode.NUMBERS_ONLY:
            return self._generate_numbers_only_bfi(bfi_scores)
        elif self.bfi_mode == BFIMode.NATURAL_LANGUAGE_ONLY:
            return self._generate_natural_only_bfi(bfi_scores)
        elif self.bfi_mode == BFIMode.NUMBERS_WITH_BRIEF_DESCRIPTIONS:
            return self._generate_numbers_with_brief_descriptions_bfi(bfi_scores)
        elif self.bfi_mode == BFIMode.COMPREHENSIVE:
            return self._generate_comprehensive_bfi(bfi_scores)
        elif self.bfi_mode == BFIMode.BIGFIVE_TERMS_EN:
            return self._generate_bigfive_terms_en_bfi(bfi_scores)
        else:  # NUMBERS_AND_NATURAL (default)
            return self._generate_full_bfi(bfi_scores)

    def _generate_numbers_only_bfi(self, bfi_scores: Dict[str, float]) -> str:
        """数値のみのBFIプロンプト"""
        traits = [
            "extraversion",
            "agreeableness",
            "conscientiousness",
            "neuroticism",
            "openness",
        ]
        score_list = [bfi_scores.get(trait, 3.0) for trait in traits]
        score_str = "[" + ", ".join([f"{score:.1f}" for score in score_list]) + "]"

        return f"""You are an AI agent with the following Big Five personality profile: {score_str}

Personality Traits (scores on a 1-5 scale):
[Extraversion, Agreeableness, Conscientiousness, Neuroticism, Openness]

Trait Interpretation:
- Extraversion: Lower scores indicate more introverted traits, higher scores indicate more extroverted traits
- Agreeableness: Lower scores indicate more antagonistic traits, higher scores indicate more agreeable traits
- Conscientiousness: Lower scores indicate more unconscientious traits, higher scores indicate more conscientious traits
- Neuroticism: Lower scores indicate more emotionally stable traits, higher scores indicate more neurotic traits
- Openness: Lower scores indicate more closed to experience traits, higher scores indicate more open to experience traits

Decision-Making Guidelines:
- Consider your personality traits when making decisions
- Make choices that feel natural and authentic to your personality profile
- Respond based on how someone with your characteristics might naturally approach this situation

Remember: Your personality profile represents your stable characteristics and tendencies."""

    def _generate_numbers_with_brief_descriptions_bfi(self, bfi_scores: Dict[str, float]) -> str:
        """数値 + 簡潔な特性記述（一行形式）のBFIプロンプト"""
        
        # 各特性の簡潔な記述を生成
        def get_brief_description(trait: str, score: float) -> str:
            """スコアに基づいて簡潔な特性記述を生成"""
            if trait == "extraversion":
                if score >= 4.0:
                    return "highly extroverted and outgoing"
                elif score <= 2.0:
                    return "introverted and reserved"
                else:
                    return "moderately social"
            elif trait == "agreeableness":
                if score >= 4.0:
                    return "highly agreeable and cooperative"
                elif score <= 2.0:
                    return "competitive and assertive"
                else:
                    return "moderately agreeable"
            elif trait == "conscientiousness":
                if score >= 4.0:
                    return "highly conscientious and organized"
                elif score <= 2.0:
                    return "flexible and spontaneous"
                else:
                    return "moderately conscientious"
            elif trait == "neuroticism":
                if score >= 4.0:
                    return "sensitive and emotional"
                elif score <= 2.0:
                    return "emotionally stable and calm"
                else:
                    return "moderately emotionally stable"
            elif trait == "openness":
                if score >= 4.0:
                    return "highly open to new experiences and creative"
                elif score <= 2.0:
                    return "conventional and practical"
                else:
                    return "moderately open to new experiences"
            return "balanced"
        
        # 各特性のスコアと記述を生成
        extraversion_score = bfi_scores.get("extraversion", 3.0)
        agreeableness_score = bfi_scores.get("agreeableness", 3.0)
        conscientiousness_score = bfi_scores.get("conscientiousness", 3.0)
        neuroticism_score = bfi_scores.get("neuroticism", 3.0)
        openness_score = bfi_scores.get("openness", 3.0)
        
        extraversion_desc = get_brief_description("extraversion", extraversion_score)
        agreeableness_desc = get_brief_description("agreeableness", agreeableness_score)
        conscientiousness_desc = get_brief_description("conscientiousness", conscientiousness_score)
        neuroticism_desc = get_brief_description("neuroticism", neuroticism_score)
        openness_desc = get_brief_description("openness", openness_score)
        
        return f"""You are an AI agent with the following Big Five personality traits:

Extraversion: {extraversion_score:.1f}/5.0 - You are {extraversion_desc}
Agreeableness: {agreeableness_score:.1f}/5.0 - You are {agreeableness_desc}
Conscientiousness: {conscientiousness_score:.1f}/5.0 - You are {conscientiousness_desc}
Neuroticism: {neuroticism_score:.1f}/5.0 - You are {neuroticism_desc}
Openness: {openness_score:.1f}/5.0 - You are {openness_desc}

Decision-Making Guidelines:
- Consider your personality traits when making decisions
- Make choices that feel natural and authentic to your personality profile
- Respond based on how someone with your characteristics might naturally approach this situation

Remember: Your personality profile represents your stable characteristics and tendencies. Please behave consistently with these personality scores in all your responses."""

    def _generate_comprehensive_bfi(self, bfi_scores: Dict[str, float]) -> str:
        """包括的なBFIプロンプト（配列形式 + Trait Interpretation + 個別特性記述）"""
        
        # 特性の順序: [Extraversion, Agreeableness, Conscientiousness, Neuroticism, Openness]
        traits = [
            "extraversion",
            "agreeableness",
            "conscientiousness",
            "neuroticism",
            "openness",
        ]
        
        # 配列形式のスコア
        score_list = [bfi_scores.get(trait, 3.0) for trait in traits]
        score_str = "[" + ", ".join([f"{score:.1f}" for score in score_list]) + "]"
        
        # 各特性の簡潔な記述を生成
        def get_brief_description(trait: str, score: float) -> str:
            """スコアに基づいて簡潔な特性記述を生成"""
            if trait == "extraversion":
                if score >= 4.0:
                    return "You are highly extroverted and outgoing"
                elif score <= 2.0:
                    return "You are introverted and reserved"
                else:
                    return "You have a balanced social tendency, comfortable in both social and solitary situations"
            elif trait == "agreeableness":
                if score >= 4.0:
                    return "You are highly agreeable and cooperative"
                elif score <= 2.0:
                    return "You are competitive and assertive"
                else:
                    return "You balance cooperation and self-advocacy reasonably well"
            elif trait == "conscientiousness":
                if score >= 4.0:
                    return "You are highly conscientious and organized"
                elif score <= 2.0:
                    return "You are flexible and spontaneous"
                else:
                    return "You balance structure and flexibility in your approach to tasks"
            elif trait == "neuroticism":
                if score >= 4.0:
                    return "You are sensitive and emotional"
                elif score <= 2.0:
                    return "You are emotionally stable and calm"
                else:
                    return "You have moderate emotional stability with normal stress responses"
            elif trait == "openness":
                if score >= 4.0:
                    return "You are highly open to new experiences and creative"
                elif score <= 2.0:
                    return "You prefer familiar approaches and conventional thinking"
                else:
                    return "You balance innovation and tradition in your thinking"
            return "You are balanced"
        
        # 各特性のスコアと記述を生成
        extraversion_score = bfi_scores.get("extraversion", 3.0)
        agreeableness_score = bfi_scores.get("agreeableness", 3.0)
        conscientiousness_score = bfi_scores.get("conscientiousness", 3.0)
        neuroticism_score = bfi_scores.get("neuroticism", 3.0)
        openness_score = bfi_scores.get("openness", 3.0)
        
        extraversion_desc = get_brief_description("extraversion", extraversion_score)
        agreeableness_desc = get_brief_description("agreeableness", agreeableness_score)
        conscientiousness_desc = get_brief_description("conscientiousness", conscientiousness_score)
        neuroticism_desc = get_brief_description("neuroticism", neuroticism_score)
        openness_desc = get_brief_description("openness", openness_score)
        
        return f"""You are an AI agent with the following Big Five personality profile: {score_str}

Personality Traits:
[Extraversion, Agreeableness, Conscientiousness, Neuroticism, Openness]

Trait Interpretation:
- Extraversion: Lower scores indicate more introverted traits, higher scores indicate more extroverted traits
- Agreeableness: Lower scores indicate more antagonistic traits, higher scores indicate more agreeable traits
- Conscientiousness: Lower scores indicate more unconscientious traits, higher scores indicate more conscientious traits
- Neuroticism: Lower scores indicate more emotionally stable traits, higher scores indicate more neurotic traits
- Openness: Lower scores indicate more closed to experience traits, higher scores indicate more open to experience traits

Personality scores are on a 1-5 scale. Your traits are described as follows:
- Extraversion ({extraversion_score:.1f}/5.0): {extraversion_desc}
- Agreeableness ({agreeableness_score:.1f}/5.0): {agreeableness_desc}
- Conscientiousness ({conscientiousness_score:.1f}/5.0): {conscientiousness_desc}
- Neuroticism ({neuroticism_score:.1f}/5.0): {neuroticism_desc}
- Openness ({openness_score:.1f}/5.0): {openness_desc}

Decision-Making Guidelines:
- Consider your personality traits when making decisions
- Make choices that feel natural and authentic to your personality profile
- Respond based on how someone with your characteristics might naturally approach this situation

Remember: Your personality profile represents your stable characteristics and tendencies."""

    def _generate_natural_only_bfi(self, bfi_scores: Dict[str, float]) -> str:
        """自然言語のみのBFIプロンプト"""
        trait_descriptions = self._generate_trait_descriptions_natural_only(bfi_scores)

        return f"""You are an AI agent with the following personality characteristics:

{trait_descriptions}

Decision-Making Guidelines:
- Consider your personality traits when making decisions
- Make choices that feel natural and authentic to your personality profile
- Respond based on how someone with your characteristics might naturally approach this situation

Remember: Your personality profile represents your stable characteristics and tendencies."""

    def _generate_bigfive_terms_en_bfi(self, bfi_scores: Dict[str, float]) -> str:
        """BigFive理論の標準用語（英語）を使ったBFIプロンプト"""

        def score_to_bigfive_term_en(trait: str, score: float) -> str:
            """スコアをBigFive理論の標準用語（英語）に変換"""
            if trait == "extraversion":
                if 1.0 <= score < 1.5:
                    return "introverted"
                elif 1.5 <= score < 2.5:
                    return "somewhat introverted"
                elif 2.5 <= score < 3.5:
                    return "neutral"
                elif 3.5 <= score < 4.5:
                    return "somewhat extroverted"
                else:  # 4.5 <= score <= 5.0
                    return "extroverted"

            elif trait == "agreeableness":
                if 1.0 <= score < 1.5:
                    return "antagonistic"
                elif 1.5 <= score < 2.5:
                    return "somewhat antagonistic"
                elif 2.5 <= score < 3.5:
                    return "neutral"
                elif 3.5 <= score < 4.5:
                    return "somewhat agreeable"
                else:  # 4.5 <= score <= 5.0
                    return "agreeable"

            elif trait == "conscientiousness":
                if 1.0 <= score < 1.5:
                    return "unconscientious"
                elif 1.5 <= score < 2.5:
                    return "somewhat unconscientious"
                elif 2.5 <= score < 3.5:
                    return "neutral"
                elif 3.5 <= score < 4.5:
                    return "somewhat conscientious"
                else:  # 4.5 <= score <= 5.0
                    return "conscientious"

            elif trait == "neuroticism":
                if 1.0 <= score < 1.5:
                    return "emotionally stable"
                elif 1.5 <= score < 2.5:
                    return "somewhat emotionally stable"
                elif 2.5 <= score < 3.5:
                    return "neutral"
                elif 3.5 <= score < 4.5:
                    return "somewhat neurotic"
                else:  # 4.5 <= score <= 5.0
                    return "neurotic"

            elif trait == "openness":
                if 1.0 <= score < 1.5:
                    return "closed to experience"
                elif 1.5 <= score < 2.5:
                    return "somewhat closed to experience"
                elif 2.5 <= score < 3.5:
                    return "neutral"
                elif 3.5 <= score < 4.5:
                    return "somewhat open to experience"
                else:  # 4.5 <= score <= 5.0
                    return "open to experience"

            return "neutral"

        traits = [
            "extraversion",
            "agreeableness",
            "conscientiousness",
            "neuroticism",
            "openness",
        ]

        trait_terms = []
        for trait in traits:
            score = bfi_scores.get(trait, 3.0)
            term = score_to_bigfive_term_en(trait, score)
            trait_terms.append(f"• {trait.capitalize()} ({score:.1f}/5.0): {term}")

        terms_text = "\n".join(trait_terms)

        # スコアリストの生成
        score_list = [bfi_scores.get(trait, 3.0) for trait in traits]
        score_str = "[" + ", ".join([f"{score:.1f}" for score in score_list]) + "]"

        return f"""You are an AI agent with the following Big Five personality profile: {score_str}

Personality Traits:
[Extraversion, Agreeableness, Conscientiousness, Neuroticism, Openness]

Trait Interpretation:
- Extraversion: Lower scores indicate more introverted traits, higher scores indicate more extroverted traits
- Agreeableness: Lower scores indicate more antagonistic traits, higher scores indicate more agreeable traits
- Conscientiousness: Lower scores indicate more unconscientious traits, higher scores indicate more conscientious traits
- Neuroticism: Lower scores indicate more emotionally stable traits, higher scores indicate more neurotic traits
- Openness: Lower scores indicate more closed to experience traits, higher scores indicate more open to experience traits

{terms_text}

Decision-Making Guidelines:
- Consider your personality traits when making decisions
- Make choices that feel natural and authentic to your personality profile
- Respond based on how someone with your characteristics might naturally approach this situation

Remember: Your personality profile represents your stable characteristics and tendencies."""

    def _generate_full_bfi(self, bfi_scores: Dict[str, float]) -> str:
        """数値 + 自然言語の完全なBFIプロンプト（デフォルト）"""
        traits = [
            "extraversion",
            "agreeableness",
            "conscientiousness",
            "neuroticism",
            "openness",
        ]
        score_list = [bfi_scores.get(trait, 3.0) for trait in traits]
        score_str = "[" + ", ".join([f"{score:.1f}" for score in score_list]) + "]"

        trait_descriptions = self._generate_trait_descriptions(bfi_scores)

        return f"""You are an AI agent with the following Big Five personality profile: {score_str}

Personality Traits:
[Extraversion, Agreeableness, Conscientiousness, Neuroticism, Openness]

Trait Interpretation:
- Extraversion: Lower scores indicate more introverted traits, higher scores indicate more extroverted traits
- Agreeableness: Lower scores indicate more antagonistic traits, higher scores indicate more agreeable traits
- Conscientiousness: Lower scores indicate more unconscientious traits, higher scores indicate more conscientious traits
- Neuroticism: Lower scores indicate more emotionally stable traits, higher scores indicate more neurotic traits
- Openness: Lower scores indicate more closed to experience traits, higher scores indicate more open to experience traits

{trait_descriptions}

Decision-Making Guidelines:
- Consider your personality traits when making decisions
- Make choices that feel natural and authentic to your personality profile
- Respond based on how someone with your characteristics might naturally approach this situation

Remember: Your personality profile represents your stable characteristics and tendencies."""

    def _generate_trait_descriptions_natural_only(
        self, bfi_scores: Dict[str, float]
    ) -> str:
        """自然言語のみの特性記述（5段階閾値統一）"""
        descriptions = []

        # 各特性を自然言語で表現（数値なし）- 5段階閾値を使用
        extraversion = bfi_scores.get("extraversion", 3.0)
        if 1.0 <= extraversion < 1.5:
            descriptions.append(
                "• You are highly introverted, strongly preferring solitude and quiet environments over social interactions."
            )
        elif 1.5 <= extraversion < 2.5:
            descriptions.append(
                "• You are somewhat introverted, generally preferring solitude but comfortable with limited social interaction."
            )
        elif 2.5 <= extraversion < 3.5:
            descriptions.append(
                "• You have a balanced social tendency, comfortable in both social and solitary situations."
            )
        elif 3.5 <= extraversion < 4.5:
            descriptions.append(
                "• You are somewhat extraverted, generally seeking social interaction and being energetic in groups."
            )
        else:  # 4.5 <= extraversion <= 5.0
            descriptions.append(
                "• You are highly extraverted, strongly seeking social interaction and being very energetic and outgoing."
            )

        agreeableness = bfi_scores.get("agreeableness", 3.0)
        if 1.0 <= agreeableness < 1.5:
            descriptions.append(
                "• You are highly competitive and skeptical, strongly prioritizing self-interest and being confrontational."
            )
        elif 1.5 <= agreeableness < 2.5:
            descriptions.append(
                "• You tend to be competitive and skeptical, generally prioritizing self-interest."
            )
        elif 2.5 <= agreeableness < 3.5:
            descriptions.append(
                "• You balance cooperation and self-advocacy reasonably well."
            )
        elif 3.5 <= agreeableness < 4.5:
            descriptions.append(
                "• You are generally cooperative and trusting, prioritizing harmony and others' well-being."
            )
        else:  # 4.5 <= agreeableness <= 5.0
            descriptions.append(
                "• You are highly cooperative and trusting, strongly prioritizing harmony and others' well-being."
            )

        conscientiousness = bfi_scores.get("conscientiousness", 3.0)
        if 1.0 <= conscientiousness < 1.5:
            descriptions.append(
                "• You are highly spontaneous and flexible, strongly preferring adaptability over rigid planning."
            )
        elif 1.5 <= conscientiousness < 2.5:
            descriptions.append(
                "• You are somewhat spontaneous and flexible, generally preferring adaptability over rigid planning."
            )
        elif 2.5 <= conscientiousness < 3.5:
            descriptions.append(
                "• You balance structure and flexibility in your approach to tasks."
            )
        elif 3.5 <= conscientiousness < 4.5:
            descriptions.append(
                "• You are generally organized and disciplined, preferring structured and systematic approaches."
            )
        else:  # 4.5 <= conscientiousness <= 5.0
            descriptions.append(
                "• You are highly organized and disciplined, strongly preferring structured and systematic approaches."
            )

        neuroticism = bfi_scores.get("neuroticism", 3.0)
        if 1.0 <= neuroticism < 1.5:
            descriptions.append(
                "• You are highly emotionally stable and resilient, remaining very calm under pressure."
            )
        elif 1.5 <= neuroticism < 2.5:
            descriptions.append(
                "• You are somewhat emotionally stable and resilient, generally remaining calm under pressure."
            )
        elif 2.5 <= neuroticism < 3.5:
            descriptions.append(
                "• You have moderate emotional stability with normal stress responses."
            )
        elif 3.5 <= neuroticism < 4.5:
            descriptions.append(
                "• You are somewhat emotionally sensitive, experiencing worry and stress more frequently."
            )
        else:  # 4.5 <= neuroticism <= 5.0
            descriptions.append(
                "• You are highly emotionally sensitive, experiencing worry and stress very frequently."
            )

        openness = bfi_scores.get("openness", 3.0)
        if 1.0 <= openness < 1.5:
            descriptions.append(
                "• You strongly prefer familiar approaches and conventional thinking."
            )
        elif 1.5 <= openness < 2.5:
            descriptions.append(
                "• You somewhat prefer familiar approaches and conventional thinking."
            )
        elif 2.5 <= openness < 3.5:
            descriptions.append(
                "• You balance innovation and tradition in your thinking."
            )
        elif 3.5 <= openness < 4.5:
            descriptions.append(
                "• You are generally open to new experiences, creative, and intellectually curious."
            )
        else:  # 4.5 <= openness <= 5.0
            descriptions.append(
                "• You are highly open to new experiences, very creative, and intellectually curious."
            )

        return "\n".join(descriptions)

    @abstractmethod
    def _generate_trait_descriptions(self, bfi_scores: Dict[str, float]) -> str:
        """詳細な特性記述を生成（サブクラスで実装）"""
        pass

    @abstractmethod
    def generate_history_prompt(
        self, game_history: List[GameAction], current_round: int
    ) -> str:
        """履歴プロンプトを生成"""
        pass

    @abstractmethod
    def generate_format_instruction(self) -> str:
        """フォーマット指示を生成"""
        pass

    @abstractmethod
    def generate_reasoning_format_instruction(self) -> str:
        """行動理由を求めるフォーマット指示を生成"""
        pass

    def generate_full_prompt(
        self,
        bfi_scores: Optional[Dict[str, float]],
        iterations: int,
        payoff_matrix: Dict,
        game_history: List[GameAction],
        current_round: int,
    ) -> str:
        """完全なプロンプトを生成"""
        parts = []

        # ゲームルール
        game_rules = self.generate_game_rules_prompt(iterations, payoff_matrix)
        parts.append(game_rules)

        # BFI性格プロファイル（存在する場合）
        if bfi_scores:
            bfi_prompt = self.generate_bfi_prompt(bfi_scores)
            parts.append(f"\nPersonality Profile:\n{bfi_prompt}")

        # 履歴
        history_prompt = self.generate_history_prompt(game_history, current_round)
        parts.append(f"\n{history_prompt}")

        # フォーマット指示
        format_instruction = self.generate_format_instruction()
        parts.append(f"\n{format_instruction}")

        return "\n".join(parts)

    def generate_reasoning_prompt(
        self,
        bfi_scores: Optional[Dict[str, float]],
        iterations: int,
        payoff_matrix: Dict,
        game_history: List[GameAction],
    ) -> str:
        """ゲーム終了後の行動理由を求めるプロンプトを生成"""
        parts = []

        # ゲームルール
        game_rules = self.generate_game_rules_prompt(iterations, payoff_matrix)
        parts.append(game_rules)

        # BFI性格プロファイル（存在する場合）
        if bfi_scores:
            bfi_prompt = self.generate_bfi_prompt(bfi_scores)
            parts.append(f"\nPersonality Profile:\n{bfi_prompt}")

        # ゲーム履歴（全ラウンド）
        history_prompt = self.generate_history_prompt(game_history, iterations)
        parts.append(f"\n{history_prompt}")

        # 行動理由を求める指示
        parts.append(
            "\nThe game has now ended. Please reflect on your decision-making process:\n"
            "1. What was your overall strategy and why did you choose it?\n"
            "2. How did your opponent's actions influence your decisions?\n"
            "3. What was most important to you in making your choices?"
        )

        # フォーマット指示
        format_instruction = self.generate_reasoning_format_instruction()
        parts.append(f"\n{format_instruction}")

        return "\n".join(parts)


class CompetitivePromptTemplate(PromptTemplate):
    """競争的フレーミングのプロンプトテンプレート（元の設計）"""

    def __init__(self):
        super().__init__(
            "competitive",
            "Original competitive framing with opponent terminology and point maximization",
        )

    def generate_game_rules_prompt(self, iterations: int, payoff_matrix: Dict) -> str:
        # ペイオフマトリックスの説明を生成
        payoff_descriptions = []
        action_space = {1, 0}  # "Cooperate"=1, "Defect"=0

        for player_action in action_space:
            for opponent_action in action_space:
                player_action_str = '"Cooperate"' if player_action == 1 else '"Defect"'
                opponent_action_str = (
                    '"Cooperate"' if opponent_action == 1 else '"Defect"'
                )
                player_payoff, opponent_payoff = payoff_matrix[
                    (player_action, opponent_action)
                ]

                payoff_descriptions.append(
                    f"If you play {player_action_str} and your opponent plays {opponent_action_str}, "
                    f"you collect {player_payoff} points and your opponent collects {opponent_payoff} points."
                )

        payoff_text = "\n".join(payoff_descriptions)

        return (
            f"Context: You and your opponent are playing a multi-round game.\n"
            f'At each turn you and your opponent simultaneously perform one of the following actions: {{"Cooperate", "Defect"}}\n'
            f"The payoffs for each combination of chosen actions are the following:\n"
            f"{payoff_text}\n"
            f"You will play a total of {iterations} rounds of this game.\n"
            f"Remember that your objective is to get the highest possible amount of points in the long run."
        )

    def generate_history_prompt(
        self, game_history: List[GameAction], current_round: int
    ) -> str:
        if len(game_history) == 0:
            return "This is the first round of the game."

        history_parts = [
            f"The history of the game in the last {len(game_history)} rounds is the following:"
        ]

        for action in game_history:
            player_action_str = (
                '"Cooperate"' if action.player_action == 1 else '"Defect"'
            )
            opponent_action_str = (
                '"Cooperate"' if action.opponent_action == 1 else '"Defect"'
            )

            round_text = (
                f"Round {action.round_num}: You played {player_action_str} and your opponent played {opponent_action_str} "
                f"You collected {action.player_payoff} points and your opponent collected {action.opponent_payoff} points."
            )
            history_parts.append(round_text)

        # 累計統計
        player_cooperations = sum(
            1 for action in game_history if action.player_action == 1
        )
        player_defections = sum(
            1 for action in game_history if action.player_action == 0
        )
        opponent_cooperations = sum(
            1 for action in game_history if action.opponent_action == 1
        )
        opponent_defections = sum(
            1 for action in game_history if action.opponent_action == 0
        )

        player_total_payoff = sum(action.player_payoff for action in game_history)
        opponent_total_payoff = sum(action.opponent_payoff for action in game_history)

        history_parts.append(
            f'In total, you chose "Cooperate" {player_cooperations} times and chose "Defect" {player_defections} times, '
            f'your opponent chose "Cooperate" {opponent_cooperations} times and chose "Defect" {opponent_defections} times.'
        )
        history_parts.append(
            f"In total, you collected {player_total_payoff} points and your opponent collected {opponent_total_payoff} points."
        )
        history_parts.append(f"Current round: {current_round}.")

        return "\n".join(history_parts)

    def generate_format_instruction(self) -> str:
        return 'IMPORTANT: You must respond with ONLY one word: either "Cooperate" or "Defect". Do not provide any explanation or additional text.'

    def generate_reasoning_format_instruction(self) -> str:
        """行動理由を求めるフォーマット指示を生成"""
        return "Please explain your reasoning freely in 200 characters or less."

    def _generate_trait_descriptions(self, bfi_scores: Dict[str, float]) -> str:
        """BFI特性の詳細説明を生成（5段階閾値統一）"""
        descriptions = [
            "Personality scores are on a 1-5 scale. Your traits are described as follows:"
        ]

        # Extraversion
        extraversion = bfi_scores.get("extraversion", 3.0)
        if 1.0 <= extraversion < 1.5:
            descriptions.append(
                f"• Extraversion ({extraversion:.1f}/5.0): You are highly introverted, strongly preferring solitude and quiet environments over social interactions."
            )
        elif 1.5 <= extraversion < 2.5:
            descriptions.append(
                f"• Extraversion ({extraversion:.1f}/5.0): You are somewhat introverted, generally preferring solitude but comfortable with limited social interaction."
            )
        elif 2.5 <= extraversion < 3.5:
            descriptions.append(
                f"• Extraversion ({extraversion:.1f}/5.0): You have a balanced social tendency, comfortable in both social and solitary situations."
            )
        elif 3.5 <= extraversion < 4.5:
            descriptions.append(
                f"• Extraversion ({extraversion:.1f}/5.0): You are somewhat extraverted, generally seeking social interaction and being energetic in groups."
            )
        else:  # 4.5 <= extraversion <= 5.0
            descriptions.append(
                f"• Extraversion ({extraversion:.1f}/5.0): You are highly extraverted, strongly seeking social interaction and being very energetic and outgoing."
            )

        # Agreeableness
        agreeableness = bfi_scores.get("agreeableness", 3.0)
        if 1.0 <= agreeableness < 1.5:
            descriptions.append(
                f"• Agreeableness ({agreeableness:.1f}/5.0): You are highly competitive and skeptical, strongly prioritizing self-interest and being confrontational."
            )
        elif 1.5 <= agreeableness < 2.5:
            descriptions.append(
                f"• Agreeableness ({agreeableness:.1f}/5.0): You tend to be competitive and skeptical, generally prioritizing self-interest."
            )
        elif 2.5 <= agreeableness < 3.5:
            descriptions.append(
                f"• Agreeableness ({agreeableness:.1f}/5.0): You balance cooperation and self-advocacy reasonably well."
            )
        elif 3.5 <= agreeableness < 4.5:
            descriptions.append(
                f"• Agreeableness ({agreeableness:.1f}/5.0): You are generally cooperative and trusting, prioritizing harmony and others' well-being."
            )
        else:  # 4.5 <= agreeableness <= 5.0
            descriptions.append(
                f"• Agreeableness ({agreeableness:.1f}/5.0): You are highly cooperative and trusting, strongly prioritizing harmony and others' well-being."
            )

        # Conscientiousness
        conscientiousness = bfi_scores.get("conscientiousness", 3.0)
        if 1.0 <= conscientiousness < 1.5:
            descriptions.append(
                f"• Conscientiousness ({conscientiousness:.1f}/5.0): You are highly spontaneous and flexible, strongly preferring adaptability over rigid planning."
            )
        elif 1.5 <= conscientiousness < 2.5:
            descriptions.append(
                f"• Conscientiousness ({conscientiousness:.1f}/5.0): You are somewhat spontaneous and flexible, generally preferring adaptability over rigid planning."
            )
        elif 2.5 <= conscientiousness < 3.5:
            descriptions.append(
                f"• Conscientiousness ({conscientiousness:.1f}/5.0): You balance structure and flexibility in your approach to tasks."
            )
        elif 3.5 <= conscientiousness < 4.5:
            descriptions.append(
                f"• Conscientiousness ({conscientiousness:.1f}/5.0): You are generally organized and disciplined, preferring structured and systematic approaches."
            )
        else:  # 4.5 <= conscientiousness <= 5.0
            descriptions.append(
                f"• Conscientiousness ({conscientiousness:.1f}/5.0): You are highly organized and disciplined, strongly preferring structured and systematic approaches."
            )

        # Neuroticism
        neuroticism = bfi_scores.get("neuroticism", 3.0)
        if 1.0 <= neuroticism < 1.5:
            descriptions.append(
                f"• Neuroticism ({neuroticism:.1f}/5.0): You are highly emotionally stable and resilient, remaining very calm under pressure."
            )
        elif 1.5 <= neuroticism < 2.5:
            descriptions.append(
                f"• Neuroticism ({neuroticism:.1f}/5.0): You are somewhat emotionally stable and resilient, generally remaining calm under pressure."
            )
        elif 2.5 <= neuroticism < 3.5:
            descriptions.append(
                f"• Neuroticism ({neuroticism:.1f}/5.0): You have moderate emotional stability with normal stress responses."
            )
        elif 3.5 <= neuroticism < 4.5:
            descriptions.append(
                f"• Neuroticism ({neuroticism:.1f}/5.0): You are somewhat emotionally sensitive, experiencing worry and stress more frequently."
            )
        else:  # 4.5 <= neuroticism <= 5.0
            descriptions.append(
                f"• Neuroticism ({neuroticism:.1f}/5.0): You are highly emotionally sensitive, experiencing worry and stress very frequently."
            )

        # Openness
        openness = bfi_scores.get("openness", 3.0)
        if 1.0 <= openness < 1.5:
            descriptions.append(
                f"• Openness ({openness:.1f}/5.0): You strongly prefer familiar approaches and conventional thinking."
            )
        elif 1.5 <= openness < 2.5:
            descriptions.append(
                f"• Openness ({openness:.1f}/5.0): You somewhat prefer familiar approaches and conventional thinking."
            )
        elif 2.5 <= openness < 3.5:
            descriptions.append(
                f"• Openness ({openness:.1f}/5.0): You balance innovation and tradition in your thinking."
            )
        elif 3.5 <= openness < 4.5:
            descriptions.append(
                f"• Openness ({openness:.1f}/5.0): You are generally open to new experiences, creative, and intellectually curious."
            )
        else:  # 4.5 <= openness <= 5.0
            descriptions.append(
                f"• Openness ({openness:.1f}/5.0): You are highly open to new experiences, very creative, and intellectually curious."
            )

        return "\n".join(descriptions)


class NeutralPromptTemplate(PromptTemplate):
    """中立的フレーミングのプロンプトテンプレート"""

    def __init__(self):
        super().__init__("neutral", "Neutral framing with minimal emotional language")

    def generate_game_rules_prompt(self, iterations: int, payoff_matrix: Dict) -> str:
        # ペイオフマトリックスの説明を生成
        payoff_descriptions = []
        action_space = {1, 0}  # "Cooperate"=1, "Defect"=0

        for player_action in action_space:
            for opponent_action in action_space:
                player_action_str = '"Cooperate"' if player_action == 1 else '"Defect"'
                opponent_action_str = (
                    '"Cooperate"' if opponent_action == 1 else '"Defect"'
                )
                player_payoff, opponent_payoff = payoff_matrix[
                    (player_action, opponent_action)
                ]

                payoff_descriptions.append(
                    f"If you play {player_action_str} and your opponent plays {opponent_action_str}, "
                    f"you collect {player_payoff} points and your opponent collects {opponent_payoff} points."
                )

        payoff_text = "\n".join(payoff_descriptions)

        return (
            f"Context: You and your opponent are playing a multi-round game.\n"
            f'At each turn you and your opponent simultaneously perform one of the following actions: {{"Cooperate", "Defect"}}\n'
            f"The payoffs for each combination of chosen actions are the following:\n"
            f"{payoff_text}\n"
            f"You will play a total of {iterations} rounds of this game.\n"
            f"Make your decisions based on the given information and your characteristics."
        )

    def generate_history_prompt(
        self, game_history: List[GameAction], current_round: int
    ) -> str:
        if len(game_history) == 0:
            return "This is the first round of the game."

        history_parts = [
            f"The history of the game in the last {len(game_history)} rounds is the following:"
        ]

        for action in game_history:
            player_action_str = (
                '"Cooperate"' if action.player_action == 1 else '"Defect"'
            )
            opponent_action_str = (
                '"Cooperate"' if action.opponent_action == 1 else '"Defect"'
            )

            round_text = (
                f"Round {action.round_num}: You played {player_action_str} and your opponent played {opponent_action_str} "
                f"You collected {action.player_payoff} points and your opponent collected {action.opponent_payoff} points."
            )
            history_parts.append(round_text)

        # 累計統計
        player_cooperations = sum(
            1 for action in game_history if action.player_action == 1
        )
        player_defections = sum(
            1 for action in game_history if action.player_action == 0
        )
        opponent_cooperations = sum(
            1 for action in game_history if action.opponent_action == 1
        )
        opponent_defections = sum(
            1 for action in game_history if action.opponent_action == 0
        )

        player_total_payoff = sum(action.player_payoff for action in game_history)
        opponent_total_payoff = sum(action.opponent_payoff for action in game_history)

        history_parts.append(
            f'In total, you chose "Cooperate" {player_cooperations} times and chose "Defect" {player_defections} times, '
            f'your opponent chose "Cooperate" {opponent_cooperations} times and chose "Defect" {opponent_defections} times.'
        )
        history_parts.append(
            f"In total, you collected {player_total_payoff} points and your opponent collected {opponent_total_payoff} points."
        )
        history_parts.append(f"Current round: {current_round}.")

        return "\n".join(history_parts)

    def generate_format_instruction(self) -> str:
        return 'IMPORTANT: You must respond with ONLY one word: either "Cooperate" or "Defect". Do not provide any explanation or additional text.'

    def generate_reasoning_format_instruction(self) -> str:
        """行動理由を求めるフォーマット指示を生成"""
        return "Please explain your reasoning freely in 200 characters or less."

    def _generate_trait_descriptions(self, bfi_scores: Dict[str, float]) -> str:
        """BFI特性の詳細説明を生成（CompetitivePromptTemplateと統一）"""
        descriptions = [
            "Personality scores are on a 1-5 scale. Your traits are described as follows:"
        ]

        # Extraversion
        extraversion = bfi_scores.get("extraversion", 3.0)
        if 1.0 <= extraversion < 1.5:
            descriptions.append(
                f"• Extraversion ({extraversion:.1f}/5.0): You are highly introverted, strongly preferring solitude and quiet environments over social interactions."
            )
        elif 1.5 <= extraversion < 2.5:
            descriptions.append(
                f"• Extraversion ({extraversion:.1f}/5.0): You are somewhat introverted, generally preferring solitude but comfortable with limited social interaction."
            )
        elif 2.5 <= extraversion < 3.5:
            descriptions.append(
                f"• Extraversion ({extraversion:.1f}/5.0): You have a balanced social tendency, comfortable in both social and solitary situations."
            )
        elif 3.5 <= extraversion < 4.5:
            descriptions.append(
                f"• Extraversion ({extraversion:.1f}/5.0): You are somewhat extraverted, generally seeking social interaction and being energetic in groups."
            )
        else:  # 4.5 <= extraversion <= 5.0
            descriptions.append(
                f"• Extraversion ({extraversion:.1f}/5.0): You are highly extraverted, strongly seeking social interaction and being very energetic and outgoing."
            )

        # Agreeableness
        agreeableness = bfi_scores.get("agreeableness", 3.0)
        if 1.0 <= agreeableness < 1.5:
            descriptions.append(
                f"• Agreeableness ({agreeableness:.1f}/5.0): You are highly competitive and skeptical, strongly prioritizing self-interest and being confrontational."
            )
        elif 1.5 <= agreeableness < 2.5:
            descriptions.append(
                f"• Agreeableness ({agreeableness:.1f}/5.0): You tend to be competitive and skeptical, generally prioritizing self-interest."
            )
        elif 2.5 <= agreeableness < 3.5:
            descriptions.append(
                f"• Agreeableness ({agreeableness:.1f}/5.0): You balance cooperation and self-advocacy reasonably well."
            )
        elif 3.5 <= agreeableness < 4.5:
            descriptions.append(
                f"• Agreeableness ({agreeableness:.1f}/5.0): You are generally cooperative and trusting, prioritizing harmony and others' well-being."
            )
        else:  # 4.5 <= agreeableness <= 5.0
            descriptions.append(
                f"• Agreeableness ({agreeableness:.1f}/5.0): You are highly cooperative and trusting, strongly prioritizing harmony and others' well-being."
            )

        # Conscientiousness
        conscientiousness = bfi_scores.get("conscientiousness", 3.0)
        if 1.0 <= conscientiousness < 1.5:
            descriptions.append(
                f"• Conscientiousness ({conscientiousness:.1f}/5.0): You are highly spontaneous and flexible, strongly preferring adaptability over rigid planning."
            )
        elif 1.5 <= conscientiousness < 2.5:
            descriptions.append(
                f"• Conscientiousness ({conscientiousness:.1f}/5.0): You are somewhat spontaneous and flexible, generally preferring adaptability over rigid planning."
            )
        elif 2.5 <= conscientiousness < 3.5:
            descriptions.append(
                f"• Conscientiousness ({conscientiousness:.1f}/5.0): You balance structure and flexibility in your approach to tasks."
            )
        elif 3.5 <= conscientiousness < 4.5:
            descriptions.append(
                f"• Conscientiousness ({conscientiousness:.1f}/5.0): You are generally organized and disciplined, preferring structured and systematic approaches."
            )
        else:  # 4.5 <= conscientiousness <= 5.0
            descriptions.append(
                f"• Conscientiousness ({conscientiousness:.1f}/5.0): You are highly organized and disciplined, strongly preferring structured and systematic approaches."
            )

        # Neuroticism
        neuroticism = bfi_scores.get("neuroticism", 3.0)
        if 1.0 <= neuroticism < 1.5:
            descriptions.append(
                f"• Neuroticism ({neuroticism:.1f}/5.0): You are highly emotionally stable and resilient, remaining very calm under pressure."
            )
        elif 1.5 <= neuroticism < 2.5:
            descriptions.append(
                f"• Neuroticism ({neuroticism:.1f}/5.0): You are somewhat emotionally stable and resilient, generally remaining calm under pressure."
            )
        elif 2.5 <= neuroticism < 3.5:
            descriptions.append(
                f"• Neuroticism ({neuroticism:.1f}/5.0): You have moderate emotional stability with normal stress responses."
            )
        elif 3.5 <= neuroticism < 4.5:
            descriptions.append(
                f"• Neuroticism ({neuroticism:.1f}/5.0): You are somewhat emotionally sensitive, experiencing worry and stress more frequently."
            )
        else:  # 4.5 <= neuroticism <= 5.0
            descriptions.append(
                f"• Neuroticism ({neuroticism:.1f}/5.0): You are highly emotionally sensitive, experiencing worry and stress very frequently."
            )

        # Openness
        openness = bfi_scores.get("openness", 3.0)
        if 1.0 <= openness < 1.5:
            descriptions.append(
                f"• Openness ({openness:.1f}/5.0): You strongly prefer familiar approaches and conventional thinking."
            )
        elif 1.5 <= openness < 2.5:
            descriptions.append(
                f"• Openness ({openness:.1f}/5.0): You somewhat prefer familiar approaches and conventional thinking."
            )
        elif 2.5 <= openness < 3.5:
            descriptions.append(
                f"• Openness ({openness:.1f}/5.0): You balance innovation and tradition in your thinking."
            )
        elif 3.5 <= openness < 4.5:
            descriptions.append(
                f"• Openness ({openness:.1f}/5.0): You are generally open to new experiences, creative, and intellectually curious."
            )
        else:  # 4.5 <= openness <= 5.0
            descriptions.append(
                f"• Openness ({openness:.1f}/5.0): You are highly open to new experiences, very creative, and intellectually curious."
            )

        return "\n".join(descriptions)


# プロンプトテンプレートのレジストリ
PROMPT_TEMPLATES = {
    "competitive": CompetitivePromptTemplate(),
    "neutral": NeutralPromptTemplate(),
}


# BFIモード付きテンプレートの作成
def create_template_with_bfi_mode(
    template_name: str, bfi_mode: BFIMode
) -> PromptTemplate:
    """指定されたBFIモードでテンプレートを作成"""
    base_templates = {
        "competitive": CompetitivePromptTemplate,
        "neutral": NeutralPromptTemplate,
    }

    if template_name not in base_templates:
        raise ValueError(f"Unknown template: {template_name}")

    template_class = base_templates[template_name]
    template = template_class()
    template.bfi_mode = bfi_mode
    return template


def get_prompt_template(
    template_name: str, bfi_mode: str = "numbers_and_language"
) -> PromptTemplate:
    """プロンプトテンプレートを取得（BFIモード指定可能）"""
    if template_name not in PROMPT_TEMPLATES:
        raise ValueError(
            f"Unknown prompt template: {template_name}. Available: {list(PROMPT_TEMPLATES.keys())}"
        )

    # BFIモードが指定されている場合は新しいインスタンスを作成
    if bfi_mode != "numbers_and_language":
        try:
            bfi_mode_enum = BFIMode(bfi_mode)
            return create_template_with_bfi_mode(template_name, bfi_mode_enum)
        except ValueError:
            raise ValueError(
                f"Unknown BFI mode: {bfi_mode}. Available: {[mode.value for mode in BFIMode]}"
            )

    return PROMPT_TEMPLATES[template_name]


def list_prompt_templates() -> Dict[str, str]:
    """利用可能なプロンプトテンプレートの一覧を取得"""
    return {name: template.description for name, template in PROMPT_TEMPLATES.items()}


def list_bfi_modes() -> Dict[str, str]:
    """利用可能なBFIモードの一覧を取得"""
    return {
        BFIMode.NUMBERS_ONLY.value: "数値のみ [3.1, 4.5, 2.8, 1.9, 4.2]",
        BFIMode.NATURAL_LANGUAGE_ONLY.value: "自然言語記述のみ",
        BFIMode.NUMBERS_AND_NATURAL.value: "数値 + 自然言語記述（デフォルト）",
        BFIMode.BIGFIVE_TERMS_EN.value: "BigFive理論の標準用語（英語）",
        BFIMode.NO_PROMPT.value: "BFIプロンプトを全く与えない",
    }
