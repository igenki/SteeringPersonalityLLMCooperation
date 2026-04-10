"""
モデルクライアントモジュール
nicer_than_humans_originのmodel_client.pyを参考にして作成

【このファイルの役割】
このファイルは、ChatGPTやHuggingFaceなどのAIモデルと通信するための
「通訳者」のような役割を果たします。
"""

# 【ライブラリの説明】
import time  # 時間に関する処理（待機時間の計算など）
import warnings  # 警告メッセージを表示するためのライブラリ
import logging  # プログラムの実行状況を記録するためのライブラリ
from typing import Optional  # 型ヒント（変数の型を明示するための機能）

# OpenAI SDK の致命的エラークラス（未インストール環境でも動くようにフォールバック）
try:
    from openai import AuthenticationError, NotFoundError, PermissionDeniedError

    _FATAL_OPENAI_ERRORS = (AuthenticationError, NotFoundError, PermissionDeniedError)
except ImportError:
    _FATAL_OPENAI_ERRORS = ()

# ログ記録用のオブジェクトを作成（このファイル専用の記録係）
logger = logging.getLogger(__name__)


class ModelClient:
    """
    LLMモデルクライアントクラス

    【クラスの役割】
    このクラスは、ChatGPTやHuggingFaceなどのAIモデルと
    安全に通信するための「窓口」の役割を果たします。
    """

    def __init__(
        self,
        model_name: str,  # 使用するAIモデルの名前（例: "gpt-3.5-turbo"）
        api_key: str,  # AIサービスにアクセスするための「鍵」
        provider: str = "openai",  # AIサービスの提供者（"openai" または "huggingface"）
        prompt_logger=None,  # 会話の記録を担当するオブジェクト
    ):
        # 【初期化処理】新しいModelClientを作る時に実行される処理

        # 基本設定の保存
        self.model_name = model_name  # 使用するAIモデル名を覚えておく
        self.api_key = api_key  # APIキー（AIサービスへの「鍵」）を保存
        self.provider = provider  # どのAIサービスを使うかを記録
        self.prompt_logger = prompt_logger  # 会話記録係を設定

        # 【レート制限の設定】
        # AIサービスには「1分間に何回まで質問できるか」という制限があります
        # これを守らないと、サービスが一時的に利用できなくなります
        self.minute_requests = 0  # 現在の1分間のリクエスト数
        self.minute_requests_limit = 9000  # 1分間の最大リクエスト数
        self.daily_requests = 0  # 現在の1日のリクエスト数
        self.daily_requests_limit = 14300000  # 1日の最大リクエスト数
        self.buffer_size = 100  # 安全マージン（制限に近づかないようにする余裕）

        # 【プロバイダーの初期化】
        # どのAIサービスを使うかによって、接続方法が異なります

        if provider == "openai":
            # OpenAI（ChatGPTの会社）のサービスを使う場合
            try:
                from openai import OpenAI  # OpenAIのライブラリを読み込み

                # OpenAIのクライアント（接続用のオブジェクト）を作成
                self.api_client = OpenAI(api_key=api_key)
            except ImportError:
                # ライブラリがインストールされていない場合のエラー処理
                raise ImportError(
                    "OpenAI library not installed. Please install with: pip install openai"
                )
        elif provider == "huggingface":
            # HuggingFace（オープンソースのAIモデルを提供するサービス）を使う場合
            try:
                from huggingface_hub import (
                    InferenceClient,
                )  # HuggingFaceのライブラリを読み込み

                # HuggingFaceのクライアントを作成
                self.api_client = InferenceClient(model=model_name, token=api_key)
                # キャッシュ（一時的な保存）を無効にする設定
                self.api_client.headers["x-use-cache"] = "0"
            except ImportError:
                # ライブラリがインストールされていない場合のエラー処理
                raise ImportError(
                    "HuggingFace library not installed. Please install with: pip install huggingface_hub"
                )
        else:
            # サポートされていないプロバイダーの場合のエラー処理
            raise ValueError(f"Unsupported provider: {provider}")

    def generate_text(
        self,
        prompt: str,  # ユーザーからの質問や指示
        system_prompt: Optional[str] = None,  # AIの役割を決める「設定」メッセージ
        max_new_tokens: int = 100,  # AIが生成する最大文字数（GPT-5では使用されない）
        temperature: float = 0.7,  # AIの創造性レベル（GPT-5では使用されない）
        reasoning_effort: str = "minimal",  # GPT-5の新しいパラメータ
        verbosity: str = "low",  # GPT-5の新しいパラメータ
        experiment_type: Optional[
            str
        ] = None,  # 実験の種類（BFI、ゲームなど）- ログ保存に必要
        prompt_type: Optional[str] = None,  # プロンプトの種類 - ログ保存に必要
        **kwargs,  # その他の設定オプション
    ) -> str:
        """
        テキスト生成メソッド

        【このメソッドの役割】
        AIに質問を送って、回答を受け取る「メイン機能」です。
        """

        # 【レート制限のチェック】
        # 制限を超えていないか確認してから質問を送る
        self._check_rate_limits()

        # 【プロンプトログの記録】
        # 何を質問したかを記録しておく（研究のため）
        full_prompt = prompt
        if system_prompt:
            # システムプロンプトがある場合は、質問と一緒に記録
            full_prompt = f"System: {system_prompt}\n\nUser: {prompt}"

        # ログ記録係がいて、実験の種類が分かっている場合のみ記録
        if self.prompt_logger and experiment_type and prompt_type:
            self.prompt_logger.log_prompt(
                experiment_type=experiment_type,  # 実験の種類（例: "bfi"）
                prompt_type=prompt_type,  # プロンプトの種類（例: "question"）
                input_prompt=full_prompt,  # LLMへの入力プロンプト
                model_name=self.model_name,  # 使用したAIモデル名
                reasoning_effort=reasoning_effort,  # GPT-5の推論深度
                verbosity=verbosity,  # GPT-5の詳細度
                temperature=temperature,  # 従来のパラメータ（後方互換性）
                max_tokens=max_new_tokens,  # 従来のパラメータ（後方互換性）
                **kwargs,  # その他の設定
            )
        elif self.prompt_logger and (not experiment_type or not prompt_type):
            # 軽量な警告（デバッグレベル）
            logger.debug(
                f"Logging skipped: experiment_type={experiment_type}, prompt_type={prompt_type}"
            )

        # 【実際のAIとの通信処理】
        try:
            # どのAIサービスを使うかによって処理を分ける
            if self.provider == "openai":
                # OpenAI（ChatGPT）を使う場合
                response = self._generate_openai(
                    prompt,
                    system_prompt,
                    max_new_tokens,
                    temperature,
                    reasoning_effort,
                    verbosity,
                )
            elif self.provider == "huggingface":
                # HuggingFaceを使う場合
                response = self._generate_huggingface(
                    prompt, system_prompt, max_new_tokens, temperature
                )
            else:
                # サポートされていないサービスの場合
                raise ValueError(f"Unsupported provider: {self.provider}")

            # 【レスポンスの記録】
            # AIからの回答も記録しておく（研究のため）
            if self.prompt_logger and experiment_type and prompt_type:
                # 最後に記録した質問に、AIの回答を追加
                if self.prompt_logger.logs:
                    self.prompt_logger.logs[-1].output_response = response
            elif self.prompt_logger and (not experiment_type or not prompt_type):
                # 軽量な警告（デバッグレベル）
                logger.debug(
                    f"Response logging skipped: experiment_type={experiment_type}, prompt_type={prompt_type}"
                )

            return response  # AIの回答を返す

        except (*_FATAL_OPENAI_ERRORS, ValueError) as e:
            # 認証エラー・モデル不在・権限不足など、復旧不可能なエラーは即停止
            logger.error(f"致命的エラー（実験を続行できません）: {e}")
            raise
        except Exception as e:
            # 一時的なネットワーク障害等は従来通り空文字返却で続行
            logger.error(f"Error in text generation: {e}")
            warnings.warn(f"Error in text generation: {e}. Returning empty string.")
            return ""

    def _generate_openai(
        self,
        prompt: str,  # ユーザーの質問
        system_prompt: Optional[str],  # AIの役割設定
        max_new_tokens: int,  # 最大文字数
        temperature: float,  # 創造性レベル
        reasoning_effort: str = "minimal",  # GPT-5の新しいパラメータ
        verbosity: str = "low",  # GPT-5の新しいパラメータ
    ) -> str:
        """
        OpenAI APIを使用したテキスト生成

        【このメソッドの役割】
        ChatGPTに実際に質問を送って、回答を受け取る処理です。

        """

        # 【会話の準備】
        # ChatGPTは会話形式で質問を受け取ります
        messages = []
        if system_prompt:
            # AIの役割を設定するメッセージを追加
            messages.append({"role": "system", "content": system_prompt})
        # ユーザーの質問を追加
        messages.append({"role": "user", "content": prompt})

        try:
            # 【実際にChatGPTに質問を送る】
            # GPT-5の場合は新しいパラメータを使用
            if self.model_name.startswith("gpt-5"):
                response = self.api_client.chat.completions.create(
                    model=self.model_name,  # 使用するモデル（例: "gpt-5"）
                    messages=messages,  # 会話履歴
                    reasoning_effort=reasoning_effort,  # GPT-5の推論深度
                    verbosity=verbosity,  # GPT-5の詳細度
                )
            else:
                # 従来のモデルの場合は従来のパラメータを使用
                response = self.api_client.chat.completions.create(
                    model=self.model_name,  # 使用するモデル（例: "gpt-3.5-turbo"）
                    messages=messages,  # 会話履歴
                    temperature=temperature,  # 創造性レベル
                    max_tokens=max_new_tokens,  # 最大文字数
                )

            # 【回答の取得】
            # ChatGPTからの回答を取得
            generated_text = response.choices[0].message.content

            # 【リクエスト数のカウント】
            # 制限管理のために、リクエスト数を増やす
            self.minute_requests += 1  # 1分間のカウントを増やす
            self.daily_requests += 1  # 1日のカウントを増やす

            # デバッグ用のログ（開発者が確認するための記録）
            logger.debug(
                f"OpenAI request completed. Daily: {self.daily_requests}, Minute: {self.minute_requests}"
            )

            return generated_text  # ChatGPTの回答を返す

        except Exception as e:
            # 【エラー処理】
            # ChatGPTとの通信で問題が起きた場合
            logger.error(f"OpenAI API error: {e}")
            raise e  # エラーを上に伝える

    def _generate_huggingface(
        self,
        prompt: str,  # ユーザーの質問
        system_prompt: Optional[str],  # AIの役割設定
        max_new_tokens: int,  # 最大文字数
        temperature: float,  # 創造性レベル
    ) -> str:
        """
        HuggingFace APIを使用したテキスト生成

        【このメソッドの役割】
        HuggingFaceのAIモデルに質問を送って、回答を受け取る処理です。
        """

        # 【プロンプトの結合】
        # HuggingFaceは会話形式ではなく、一つのテキストとして送ります
        full_prompt = prompt
        if system_prompt:
            # システムプロンプトとユーザープロンプトを結合
            full_prompt = f"{system_prompt}\n\n{prompt}"

        # 【リトライ処理】
        # HuggingFaceは時々混雑しているので、失敗したら再試行します
        generated = False
        while not generated:
            try:
                # 【実際にHuggingFaceに質問を送る】
                generated_text = self.api_client.text_generation(
                    full_prompt, max_new_tokens=max_new_tokens, temperature=temperature
                )
                generated = True  # 成功したのでループを終了
                return generated_text  # HuggingFaceの回答を返す

            except Exception as e:
                # 【エラー処理】
                if "HfHubHTTPError" in str(e) or "OverloadedError" in str(e):
                    # サーバーが混雑している場合の処理
                    logger.warning(
                        "Model is overloaded. Waiting 300 seconds and retrying."
                    )
                    time.sleep(300)  # 5分待ってから再試行
                else:
                    # その他のエラーの場合
                    logger.error(f"HuggingFace API error: {e}")
                    raise e  # エラーを上に伝える

    def _check_rate_limits(self):
        """
        レート制限のチェック

        【このメソッドの役割】
        AIサービスには「1分間に何回まで質問できるか」という制限があります。
        この制限を超えないように、必要に応じて待機します。
        """
        # OpenAI以外のサービスでは制限チェックは不要
        if self.provider != "openai":
            return

        # 【日次制限のチェック】
        # 1日の制限に近づいているかチェック
        if self.daily_requests > (self.daily_requests_limit - self.buffer_size):
            # 現在の時刻を取得
            current_time = time.time()
            local_time = time.localtime(current_time)

            # 次の深夜0時を計算
            next_midnight = time.struct_time(
                (
                    local_time.tm_year,  # 年
                    local_time.tm_mon,  # 月
                    local_time.tm_mday + 1,  # 日（次の日）
                    0,  # 時（0時）
                    0,  # 分（0分）
                    0,  # 秒（0秒）
                    local_time.tm_wday,  # 曜日
                    local_time.tm_yday + 1,  # 年内通算日
                    local_time.tm_isdst,  # 夏時間フラグ
                )
            )
            next_midnight_seconds = time.mktime(next_midnight)
            seconds_until_midnight = (next_midnight_seconds - current_time) + 60

            # 制限に達したので、次の日まで待機
            logger.info(
                f"Daily requests limit reached. Sleeping for {seconds_until_midnight} seconds."
            )
            time.sleep(seconds_until_midnight)
            # カウンターをリセット
            self.daily_requests = 0
            self.minute_requests = 0

        # 【分次制限のチェック】
        # 1分間の制限に近づいているかチェック
        if self.minute_requests > (self.minute_requests_limit - self.buffer_size):
            # 制限に達したので、1分待機
            logger.info("Minute requests limit reached. Sleeping for 60 seconds.")
            time.sleep(60)
            # 1分間のカウンターをリセット
            self.minute_requests = 0
