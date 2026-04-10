"""
プロンプトログ機能
LLMに送信されるプロンプトを記録・保存する
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class PromptLog:
    """プロンプトログのデータ構造"""

    timestamp: str
    experiment_type: str  # "control_bfi", "control_pd", "modification", etc.
    bfi_mode: Optional[str]
    prompt_template: Optional[str]
    target_traits: Optional[List[str]]
    forced_score: Optional[float]
    strategy: Optional[str]
    round_number: Optional[int]
    prompt_type: str  # "bfi_question", "game_decision", "game_rules", etc.
    input_prompt: str  # LLMへの入力プロンプト
    output_response: Optional[str] = None  # LLMからの出力レスポンス
    model_name: Optional[str] = None
    reasoning_effort: Optional[str] = None  # GPT-5の新しいパラメータ
    verbosity: Optional[str] = None  # GPT-5の新しいパラメータ
    temperature: Optional[float] = None  # 従来のパラメータ（後方互換性）
    max_tokens: Optional[int] = None  # 従来のパラメータ（後方互換性）


class PromptLogger:
    """プロンプトログを管理するクラス"""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.logs: List[PromptLog] = []
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        # ログディレクトリを作成
        self.log_dir = output_dir / "prompt_logs"
        self.log_dir.mkdir(exist_ok=True)

        logger.info(f"PromptLogger initialized with session ID: {self.session_id}")

    def log_prompt(
        self,
        experiment_type: str,
        prompt_type: str,
        input_prompt: str,
        bfi_mode: Optional[str] = None,
        prompt_template: Optional[str] = None,
        target_traits: Optional[List[str]] = None,
        forced_score: Optional[float] = None,
        strategy: Optional[str] = None,
        round_number: Optional[int] = None,
        output_response: Optional[str] = None,
        model_name: Optional[str] = None,
        reasoning_effort: Optional[str] = None,  # GPT-5の新しいパラメータ
        verbosity: Optional[str] = None,  # GPT-5の新しいパラメータ
        temperature: Optional[float] = None,  # 従来のパラメータ（後方互換性）
        max_tokens: Optional[int] = None,  # 従来のパラメータ（後方互換性）
    ):
        """プロンプトをログに記録"""

        log_entry = PromptLog(
            timestamp=datetime.now().isoformat(),
            experiment_type=experiment_type,
            bfi_mode=bfi_mode,
            prompt_template=prompt_template,
            target_traits=target_traits,
            forced_score=forced_score,
            strategy=strategy,
            round_number=round_number,
            prompt_type=prompt_type,
            input_prompt=input_prompt,
            output_response=output_response,
            model_name=model_name,
            reasoning_effort=reasoning_effort,  # GPT-5の新しいパラメータ
            verbosity=verbosity,  # GPT-5の新しいパラメータ
            temperature=temperature,  # 従来のパラメータ（後方互換性）
            max_tokens=max_tokens,  # 従来のパラメータ（後方互換性）
        )

        self.logs.append(log_entry)

        # リアルタイムログ出力
        logger.info(f"[PROMPT LOG] {experiment_type} - {prompt_type}")
        logger.debug(f"Input Prompt: {input_prompt[:200]}...")
        if output_response:
            logger.debug(f"Output Response: {output_response[:200]}...")

    def get_logs_by_type(self, experiment_type: str) -> List[PromptLog]:
        """特定の実験タイプのログを取得"""
        return [log for log in self.logs if log.experiment_type == experiment_type]

    def get_logs_by_prompt_type(self, prompt_type: str) -> List[PromptLog]:
        """特定のプロンプトタイプのログを取得"""
        return [log for log in self.logs if log.prompt_type == prompt_type]

    def merge_logs(self, other_logger: "PromptLogger"):
        """他のプロンプトロガーのログを統合"""
        if other_logger and other_logger.logs:
            self.logs.extend(other_logger.logs)
            logger.info(f"Merged {len(other_logger.logs)} logs from other logger")

    def save_logs(self, filename: Optional[str] = None):
        """ログをファイルに保存"""
        if not filename:
            filename = f"prompt_logs_{self.session_id}.json"

        log_file = self.log_dir / filename

        # ログを辞書形式に変換
        logs_data = [asdict(log) for log in self.logs]

        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(logs_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Prompt logs saved to: {log_file}")
        return log_file

    def print_summary(self):
        """ログのサマリーを表示"""
        if not self.logs:
            print("No prompt logs recorded.")
            return

        print(f"\n=== Prompt Log Summary (Session: {self.session_id}) ===")
        print(f"Total prompts logged: {len(self.logs)}")

        # 実験タイプ別の集計
        experiment_counts = {}
        prompt_type_counts = {}

        for log in self.logs:
            experiment_counts[log.experiment_type] = (
                experiment_counts.get(log.experiment_type, 0) + 1
            )
            prompt_type_counts[log.prompt_type] = (
                prompt_type_counts.get(log.prompt_type, 0) + 1
            )

        print("\nBy experiment type:")
        for exp_type, count in experiment_counts.items():
            print(f"  {exp_type}: {count}")

        print("\nBy prompt type:")
        for prompt_type, count in prompt_type_counts.items():
            print(f"  {prompt_type}: {count}")

        print(f"\nLogs saved to: {self.log_dir}")
