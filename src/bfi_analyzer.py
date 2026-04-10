"""
Big Five Inventory (BFI) 分析モジュール
PersonaLLM_originのrun_bfi.pyを参考にして作成

【このモジュールの役割】
LLMにBig Five Inventoryの44問の質問を投げ、回答を解析して5つの性格特性スコアを計算します。

【主要な機能】
1. BFI質問の読み込み：PersonaLLM研究と同じ44問の質問を読み込みます
2. LLMへの質問送信：LLMにBFI質問を送信し、回答を取得します
3. 回答の解析：LLMの回答から数値を抽出し、各性格特性のスコアを計算します
4. スコアの集計：複数回の質問に対する回答を集計し、平均スコアを算出します

【使用例】
    analyzer = BFIAnalyzer(model_client)
    bfi_scores = analyzer.get_bfi_scores(bfi_scores=None, bfi_mode="numbers_and_language", iterations=5)
"""

# 【ライブラリの説明】
import re  # 正規表現（文字列から数字を抽出するため）
from typing import List, Dict, Any, Optional  # 型ヒント（変数の型を明示）
import logging  # ログ記録（実行状況の記録）

# ログ記録用のオブジェクトを作成（このファイル専用の記録係）
logger = logging.getLogger(__name__)


class BFIAnalyzer:
    """Big Five Inventory 分析クラス"""

    def __init__(self, model_client):

        self.model_client = model_client
        self.bfi_questions = (
            self._load_bfi_questions()
        )  # 性格診断の質問リストを読み込み

    def _load_bfi_questions(self) -> List[Dict[str, str]]:
        """BFI質問項目の読み込み（先行研究PersonaLLM_originに基づく44問）"""
        # PersonaLLM_origin/prompts/bfi_prompt.txtの44問を完全に同じ順序で使用
        # 注意: PersonaLLM_originでは特性別にグループ化されていない

        # 質問順番の定義（PersonaLLM_originと完全に同じ順序）
        question_letters = [
            "a",
            "b",
            "c",
            "d",
            "e",
            "f",
            "g",
            "h",
            "i",
            "j",
            "k",
            "l",
            "m",
            "n",
            "o",
            "p",
            "q",
            "r",
            "s",
            "t",
            "u",
            "v",
            "w",
            "x",
            "y",
            "z",
            "aa",
            "ab",
            "ac",
            "ad",
            "ae",
            "af",
            "ag",
            "ah",
            "ai",
            "aj",
            "ak",
            "al",
            "am",
            "an",
            "ao",
            "ap",
            "aq",
            "ar",
        ]

        # 質問データの定義（PersonaLLM_originと完全に同じ順序）
        question_data_list = [
            {"trait": "extraversion", "question": "Talks a lot", "reverse": False},
            {
                "trait": "agreeableness",
                "question": "Notices other people's weak points",
                "reverse": True,
            },
            {
                "trait": "conscientiousness",
                "question": "Does things carefully and completely",
                "reverse": False,
            },
            {"trait": "neuroticism", "question": "Is sad, depressed", "reverse": False},
            {
                "trait": "openness",
                "question": "Is original, comes up with new ideas",
                "reverse": False,
            },
            {
                "trait": "extraversion",
                "question": "Keeps their thoughts to themselves",
                "reverse": True,
            },
            {
                "trait": "agreeableness",
                "question": "Is helpful and not selfish with others",
                "reverse": False,
            },
            {
                "trait": "conscientiousness",
                "question": "Can be kind of careless",
                "reverse": True,
            },
            {
                "trait": "neuroticism",
                "question": "Is relaxed, handles stress well",
                "reverse": True,
            },
            {
                "trait": "openness",
                "question": "Is curious about lots of different things",
                "reverse": False,
            },
            {
                "trait": "extraversion",
                "question": "Has a lot of energy",
                "reverse": False,
            },
            {
                "trait": "agreeableness",
                "question": "Starts arguments with others",
                "reverse": True,
            },
            {
                "trait": "conscientiousness",
                "question": "Is a good, hard worker",
                "reverse": False,
            },
            {
                "trait": "neuroticism",
                "question": "Can be tense; not always easy going",
                "reverse": False,
            },
            {"trait": "openness", "question": "Clever; thinks a lot", "reverse": False},
            {
                "trait": "extraversion",
                "question": "Makes things exciting",
                "reverse": False,
            },
            {
                "trait": "agreeableness",
                "question": "Forgives others easily",
                "reverse": False,
            },
            {
                "trait": "conscientiousness",
                "question": "Isn't very organized",
                "reverse": True,
            },
            {"trait": "neuroticism", "question": "Worries a lot", "reverse": False},
            {
                "trait": "openness",
                "question": "Has a good, active imagination",
                "reverse": False,
            },
            {"trait": "extraversion", "question": "Tends to be quiet", "reverse": True},
            {
                "trait": "agreeableness",
                "question": "Usually trusts people",
                "reverse": False,
            },
            {
                "trait": "conscientiousness",
                "question": "Tends to be lazy",
                "reverse": True,
            },
            {
                "trait": "neuroticism",
                "question": "Doesn't get upset easily; steady",
                "reverse": True,
            },
            {
                "trait": "openness",
                "question": "Is creative and inventive",
                "reverse": False,
            },
            {
                "trait": "extraversion",
                "question": "Has a good, strong personality",
                "reverse": False,
            },
            {
                "trait": "agreeableness",
                "question": "Can be cold and distant with others",
                "reverse": True,
            },
            {
                "trait": "conscientiousness",
                "question": "Keeps working until things are done",
                "reverse": False,
            },
            {"trait": "neuroticism", "question": "Can be moody", "reverse": False},
            {
                "trait": "openness",
                "question": "Likes artistic and creative experiences",
                "reverse": False,
            },
            {"trait": "extraversion", "question": "Is kind of shy", "reverse": True},
            {
                "trait": "agreeableness",
                "question": "Kind and considerate to almost everyone",
                "reverse": False,
            },
            {
                "trait": "conscientiousness",
                "question": "Does things quickly and carefully",
                "reverse": False,
            },
            {
                "trait": "neuroticism",
                "question": "Stays calm in difficult situations",
                "reverse": True,
            },
            {
                "trait": "openness",
                "question": "Likes work that is the same every time",
                "reverse": True,
            },
            {
                "trait": "extraversion",
                "question": "Is outgoing; likes to be with people",
                "reverse": False,
            },
            {
                "trait": "agreeableness",
                "question": "Is sometimes rude to others",
                "reverse": True,
            },
            {
                "trait": "conscientiousness",
                "question": "Makes plans and sticks to them",
                "reverse": False,
            },
            {
                "trait": "neuroticism",
                "question": "Get nervous easily",
                "reverse": False,
            },
            {
                "trait": "openness",
                "question": "Likes to think and play with ideas",
                "reverse": False,
            },
            {
                "trait": "openness",
                "question": "Doesn't like artistic things (plays, music)",
                "reverse": True,
            },
            {
                "trait": "agreeableness",
                "question": "Likes to cooperate; goes along with others",
                "reverse": False,
            },
            {
                "trait": "conscientiousness",
                "question": "Has trouble paying attention",
                "reverse": True,
            },
            {
                "trait": "openness",
                "question": "Knows a lot about art, music and books",
                "reverse": False,
            },
        ]

        # 質問データにletterフィールドを追加
        questions = []
        for i, data in enumerate(question_data_list):
            question = data.copy()
            question["letter"] = question_letters[i]
            questions.append(question)
        return questions  # 質問リストを返す

    def _construct_bfi_score_prompt(
        self, bfi_scores: Optional[Dict[str, float]]
    ) -> str:
        """BFIスコアベースのペルソナプロンプトを構築"""
        # bfi_scoresがNoneの場合はデフォルト値を使用
        if bfi_scores is None:
            return ""  # システムプロンプトなし

        traits = [
            "openness",  # 開放性 (O)
            "conscientiousness",  # 誠実性 (C)
            "extraversion",  # 外向性 (E)
            "agreeableness",  # 協調性 (A)
            "neuroticism",  # 神経症傾向 (N)
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

        # 各特性のスコアを取得
        score_list = [bfi_scores[trait] for trait in traits]
        # スコアを文字列形式に変換（例: "[4.2, 3.8, 4.5, 2.1, 3.9]"）
        score_str = "[" + ", ".join([f"{score:.1f}" for score in score_list]) + "]"

        # TODO(REVIEW):AIへの性格設定プロンプトを作成
        prompt = f"""You have the following Big Five personality scores: {score_str}

These scores represent:
[Openness, Conscientiousness, Extraversion, Agreeableness, Neuroticism]

Each score is on a scale from 1.0 to 5.0, where:
- 1.0 = Very low level of that trait
- 3.0 = Average level of that trait  
- 5.0 = Very high level of that trait

Please respond and behave consistently with these personality scores in all your interactions."""

        return prompt  # 作成したプロンプトを返す

    def _generate_bfi_response_batch(
        self,
        bfi_scores: Optional[Dict[str, float]],
        bfi_mode: str = "numbers_and_language",
        max_retries: int = 3,
    ) -> Dict[str, int]:
        """BFI質問に対する回答を生成"""
        # 【システムプロンプトの設定】
        if bfi_scores is not None:
            # 性格設定がある場合は、その設定をAIに伝える
            system_prompt = self._construct_bfi_score_prompt(bfi_scores)
        else:
            # 性格設定がない場合は、PersonaLLM_originと同様のシステムプロンプトを使用
            system_prompt = "You are a chatbot who is taking a personality assessment."

        # 【ユーザープロンプトの作成】
        # PersonaLLM_originのbfi_prompt.txtに基づく形式（全質問を一度に提示）
        questions_text = ""
        for question_data in self.bfi_questions:
            letter = question_data["letter"]  # 定義済みのletterフィールドを使用
            questions_text += f"({letter}) {question_data['question']}\n"

        user_prompt = f"""Here are a number of characteristics that may or may not apply to you. For example, do you agree that you are someone who likes to spend time with others? Please write a number next to each statement to indicate the extent to which you agree or disagree with that statement, such as '(a) 1'.

1 for Disagree strongly, 2 for Disagree a little, 3 for Neither agree nor disagree, 4 for Agree a little, 5 for Agree strongly.

{questions_text.strip()}

Please respond with the format: (a) 1\n(b) 2\n(c) 3\n... for all questions."""

        # 回答が適切なものを得るまでmax_retries回ループ
        for attempt in range(max_retries):
            try:
                # 【AIに質問を送信】
                # 入力プロンプトと出力レスポンスは自動的にprompt_loggerに記録される
                response = self.model_client.generate_text(
                    prompt=user_prompt,  # 質問内容
                    system_prompt=system_prompt,  # 性格設定
                    max_new_tokens=2000,  # 全44問の回答のため十分な文字数を確保
                    temperature=0.7,  # Temperatureは0.7で固定
                    experiment_type=(
                        "control_bfi" if bfi_scores is None else "modification"
                    ),  # 実験の種類
                    prompt_type="bfi_question",  # プロンプトの種類
                    bfi_mode=bfi_mode,  # BFIモード（動的に指定）
                )

                # 【回答から全スコアを抽出】
                # PersonaLLM_origin形式の回答を解析: (a) 1\n(b) 2\n...
                scores = {}
                lines = response.strip().split("\n")

                for line in lines:
                    # (a) 1 の形式を解析
                    match = re.match(r"\(([a-z]+)\)\s*([1-5])", line.strip())
                    if match:
                        letter = match.group(1)
                        score = int(match.group(2))
                        scores[letter] = score

                # 全44問の回答が得られたかチェック
                if len(scores) == len(self.bfi_questions):
                    # リバース項目の処理を適用
                    final_scores = {}
                    for question_data in self.bfi_questions:
                        letter = question_data[
                            "letter"
                        ]  # 定義済みのletterフィールドを使用
                        score = scores.get(letter, 3)  # デフォルトは3
                        if question_data["reverse"]:
                            score = 6 - score  # 逆転項目の処理
                        final_scores[letter] = score
                    return final_scores
                else:
                    # 回答が不完全な場合
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries}: Incomplete response. Got {len(scores)}/44 answers: {response}"
                    )
                    if attempt < max_retries - 1:
                        logger.info("Retrying BFI batch questions")
                        continue

            except Exception as e:
                # 【エラー処理】
                # AIとの通信で問題が起きた場合
                logger.error(
                    f"Attempt {attempt + 1}/{max_retries}: Error generating BFI response: {e}"
                )
                if attempt < max_retries - 1:
                    logger.info("Retrying BFI batch questions")
                    continue

        # 【最大試行回数に達した場合】
        logger.error(
            f"回答が{max_retries}回試行しても適切ではありません。よってプログラムを停止します。"
        )
        raise ValueError(
            f"回答が{max_retries}回試行しても適切ではありません。よってプログラムを停止します。"
        )

    def get_bfi_scores(
        self,
        bfi_scores: Optional[Dict[str, float]] = None,
        bfi_mode: str = "numbers_and_language",
        iterations: int = 1,
    ) -> Dict[str, Any]:
        """BFIスコアを取得"""
        logger.info(f"BFIスコアを取得しています: {bfi_scores}")

        all_scores = []  # 全イテレーションの結果を保存するリスト

        # より正確な結果を得るために、同じ質問を複数回実行
        for iteration in range(iterations):
            logger.info(f"BFI iteration {iteration + 1}/{iterations}")

            # 【バッチ処理で全44問の回答を一度に取得】
            batch_scores = self._generate_bfi_response_batch(
                bfi_scores, bfi_mode, max_retries=3
            )

            # 各性格要素のスコアを保存する辞書
            scores = {
                "openness": [],  # 開放性のスコア (O)
                "conscientiousness": [],  # 誠実性のスコア (C)
                "extraversion": [],  # 外向性のスコア (E)
                "agreeableness": [],  # 協調性のスコア (A)
                "neuroticism": [],  # 神経症傾向のスコア (N)
            }

            # 【バッチで取得したスコアを特性別に分類】
            for question_data in self.bfi_questions:
                trait = question_data["trait"]  # どの性格要素を測る質問か
                letter = question_data["letter"]  # 質問のラベル

                # バッチで取得したスコアを使用
                score = batch_scores.get(letter, 3)  # デフォルトは3
                scores[trait].append(score)  # 取得したスコアを保存

            # 各特性の平均スコアを計算
            trait_averages = {}
            for trait, trait_scores in scores.items():
                # その特性の全質問の平均を計算
                trait_averages[trait] = sum(trait_scores) / len(trait_scores)

            # このイテレーションの結果を保存
            all_scores.append(
                {
                    "iteration": iteration + 1,  # イテレーション番号
                    "raw_scores": scores,  # 生のスコア（各質問の回答）
                    "trait_averages": trait_averages,  # 各特性の平均スコア
                }
            )

        # 【全イテレーションの平均を計算】
        # 複数回実行した結果の最終的な平均を計算
        final_averages = {}
        for trait in [
            "openness",  # (O)
            "conscientiousness",  # (C)
            "extraversion",  # (E)
            "agreeableness",  # (A)
            "neuroticism",  # (N)
        ]:
            # 全イテレーションのその特性のスコアを取得
            trait_scores = [score["trait_averages"][trait] for score in all_scores]
            # 最終的な平均を計算
            final_averages[trait] = sum(trait_scores) / len(trait_scores)

        # 【結果を返す】
        return {
            "bfi_scores": bfi_scores,  # 入力された性格設定
            "iterations": all_scores,  # 各イテレーションの詳細結果
            "final_averages": final_averages,  # 最終的な平均スコア
            "total_iterations": iterations,  # 実行回数
        }

    def generate_forced_bfi_profile(
        self,
        target_trait: str,
        forced_score: float,
        control_baseline: Dict[str, Any],
        iterations: int = 1,
    ) -> Dict[str, Any]:
        """特定の性格特性に直接BFIスコアを設定"""
        logger.info(f"Setting forced BFI scores: {target_trait} = {forced_score}")

        # コントロール条件のBFIスコアをベースラインとして使用
        if "final_averages" in control_baseline:
            forced_scores = control_baseline["final_averages"].copy()
        else:
            forced_scores = control_baseline.copy()

        # 対象特性のスコアを強制的に設定
        forced_scores[target_trait] = forced_score

        # BFI質問は実行しないため、iterationsは無視して1回分だけ処理
        logger.info(f"Forced BFI score set: {target_trait} = {forced_score}")

        return {
            "iterations": [forced_scores.copy()],  # 1回分だけ
            "final_averages": forced_scores,
            "target_trait": target_trait,
            "forced_score": forced_score,
            "total_iterations": 1,  # 常に1
        }
