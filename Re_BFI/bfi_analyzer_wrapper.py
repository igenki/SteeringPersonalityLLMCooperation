"""
Re_BFI実験用のBFIAnalyzerラッパー

このモジュールは既存のBFIAnalyzerを拡張し、
prompt_templates.pyの新しいプロンプトフォーマットを使用します。
既存のsrc/bfi_analyzer.pyには一切変更を加えません。
"""

import sys
from pathlib import Path
from typing import Dict, Optional

# 親ディレクトリのsrcモジュールをインポート可能にする
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.bfi_analyzer import BFIAnalyzer
import logging

logger = logging.getLogger(__name__)


class BFIAnalyzerWrapper(BFIAnalyzer):
    """
    Re_BFI実験用のBFIAnalyzerラッパークラス
    
    prompt_templates.pyの_generate_comprehensive_bfiと同じプロンプトフォーマットを使用します。
    これにより、配列形式 + Trait Interpretation + 個別特性記述の包括的なプロンプトが生成されます。
    """
    
    def _construct_bfi_score_prompt(
        self, bfi_scores: Optional[Dict[str, float]]
    ) -> str:
        """
        BFIスコアベースのペルソナプロンプトを構築（包括的フォーマット）
        
        src/prompt_templates.pyの_generate_comprehensive_bfiメソッドと同じフォーマットを使用し、
        配列形式の数値 + Trait Interpretation + 個別の特性記述を提供します。
        """
        # bfi_scoresがNoneの場合はデフォルト値を使用
        if bfi_scores is None:
            return ""  # システムプロンプトなし
        
        # prompt_templates.pyと同じ順序: [Extraversion, Agreeableness, Conscientiousness, Neuroticism, Openness]
        traits = [
            "extraversion",
            "agreeableness",
            "conscientiousness",
            "neuroticism",
            "openness",
        ]
        
        # すべての特性のスコアが定義されているかチェック
        missing_traits = [trait for trait in traits if trait not in bfi_scores]
        if missing_traits:
            error_msg = (
                f"不完全なペルソナ設定: 以下の特性のスコアが未定義です: {missing_traits}\n"
                f"定義されているスコア: {list(bfi_scores.keys())}\n"
                f"このエラーにより、実験結果を正しく得ることができないのでプログラムを停止します。"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # 配列形式のスコア
        traits = [
            "extraversion",
            "agreeableness",
            "conscientiousness",
            "neuroticism",
            "openness",
        ]
        score_list = [bfi_scores.get(trait, 3.0) for trait in traits]
        score_str = "[" + ", ".join([f"{score:.1f}" for score in score_list]) + "]"
        
        # 各特性の詳細な記述を生成
        def get_brief_description(trait: str, score: float) -> str:
            """スコアに基づいて特性記述を生成"""
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
        
        # prompt_templates.pyのCOMPREHENSIVEモードと同じフォーマットのプロンプトを構築
        prompt = f"""You are an AI agent with the following Big Five personality profile: {score_str}

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
        
        return prompt
