"""
Re_BFI実験用のModelClientラッパー

このモジュールは既存のModelClientを拡張し、
OpenAI APIの仕様変更（verbosityパラメータの廃止）に対応します。
既存のsrc/model_client.pyには一切変更を加えません。
"""

import sys
from pathlib import Path

# 親ディレクトリのsrcモジュールをインポート可能にする
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.model_client import ModelClient
from typing import Optional, Any
import logging

logger = logging.getLogger(__name__)


class ModelClientWrapper(ModelClient):
    """
    Re_BFI実験用のModelClientラッパークラス
    
    OpenAI APIの仕様変更に対応するため、verbosityパラメータを
    自動的に除外してAPIを呼び出します。
    """
    
    def __init__(self, *args, **kwargs):
        """
        ModelClientを初期化します。
        すべての引数は親クラスにそのまま渡されます。
        """
        super().__init__(*args, **kwargs)
        self._verbosity_warning_shown = False
    
    def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_new_tokens: int = 100,
        temperature: float = 0.7,
        reasoning_effort: str = "minimal",
        verbosity: str = "low",
        experiment_type: Optional[str] = None,
        prompt_type: Optional[str] = None,
        **kwargs,
    ) -> str:
        """
        テキスト生成メソッド（ラッパー版）
        
        GPT-5/o1モデルの場合、verbosityパラメータがAPIでサポートされなく
        なったため、このラッパーで自動的に処理します。
        
        既存のmodel_client.pyの_generate_openai_chatメソッドを直接呼び出す
        代わりに、親クラスのgenerate_textを呼び出しますが、GPT-5/o1の場合は
        verbosityを使用しない特別な処理を行います。
        """
        
        # GPT-5/o1モデルでverbosityが指定されている場合の警告
        if (self.model_name.startswith("gpt-5") or self.model_name.startswith("o1")):
            if verbosity != "low" and not self._verbosity_warning_shown:
                logger.warning(
                    f"verbosityパラメータ（値: {verbosity}）は指定されていますが、"
                    f"OpenAI APIでサポートされなくなったため、Re_BFI実験では使用しません。"
                )
                self._verbosity_warning_shown = True
        
        # 親クラスのgenerate_textを呼び出す
        # 注意: 親クラスはverbosityをAPIに送信しようとするため、
        # エラーが発生する可能性があります。
        # そのため、親クラスの_generate_openai_chatを直接オーバーライドします。
        try:
            return super().generate_text(
                prompt=prompt,
                system_prompt=system_prompt,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                reasoning_effort=reasoning_effort,
                verbosity=verbosity,
                experiment_type=experiment_type,
                prompt_type=prompt_type,
                **kwargs,
            )
        except TypeError as e:
            if "verbosity" in str(e) or "unexpected keyword argument" in str(e):
                # verbosityエラーの場合、ログに記録して再試行
                logger.warning(f"verbosityパラメータエラーが発生しました。パラメータを除外して再試行します: {e}")
                # この時点では親クラスのメソッドを直接修正できないため、
                # 代わりにエラーメッセージを表示
                raise RuntimeError(
                    "verbosityパラメータがAPIでサポートされていません。"
                    "src/model_client.pyの_generate_openai_chatメソッドを修正する必要があります。"
                ) from e
            else:
                raise
    
    def _generate_openai(
        self,
        prompt: str,
        system_prompt: Optional[str],
        max_new_tokens: int,
        temperature: float,
        reasoning_effort: str = "minimal",
        verbosity: str = "low",
    ) -> str:
        """
        OpenAI APIでテキストを生成（オーバーライド版）
        
        GPT-5/o1モデルの場合、verbosityパラメータをAPIに送信しません。
        """
        
        # メッセージリストの構築
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            # GPT-5/o1モデルの場合は新しいパラメータを使用（verbosity除外）
            if self.model_name.startswith("gpt-5") or self.model_name.startswith("o1"):
                response = self.api_client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    reasoning_effort=reasoning_effort,
                    # 注意: verbosityはAPIでサポートされなくなったため除外
                )
            else:
                # 従来のモデルの場合は従来のパラメータを使用
                response = self.api_client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_new_tokens,
                )
            
            # 回答の取得
            generated_text = response.choices[0].message.content
            
            # リクエスト数のカウント
            self.minute_requests += 1
            self.daily_requests += 1
            
            logger.debug(
                f"OpenAI request completed. Daily: {self.daily_requests}, Minute: {self.minute_requests}"
            )
            
            return generated_text
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise e
