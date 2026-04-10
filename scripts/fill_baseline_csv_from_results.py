#!/usr/bin/env python3

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, List, Tuple


def _normalize_strategy_name(s: str) -> str:
    s = s.strip()
    if s.lower().startswith("vs"):
        s = s[2:].strip()
    s = s.replace(" ", "")
    return s.upper()


def _extract_strategy_from_column(col: str) -> str:
    # e.g. "vs ALLC" -> "ALLC", "vsTFT" -> "TFT", "vs GRIM" -> "GRIM"
    col = col.strip()
    if col.lower().startswith("vs"):
        rest = col[2:].strip()
        if not rest:
            return ""
        return _normalize_strategy_name(rest)
    return _normalize_strategy_name(col)


def _find_control_pd_json(results_dir: Path) -> Path:
    candidates = sorted(results_dir.rglob("control_pd_games.json"))
    if not candidates:
        raise FileNotFoundError(
            f"control_pd_games.json が見つかりません: {results_dir}"
        )

    # Heuristic preference to match common layout.
    preferred_subpaths = [
        "BFIno_prompt_PDcompetitive/control_pd_games.json",
        "BFIno_prompt_PDneutral/control_pd_games.json",
    ]
    for rel in preferred_subpaths:
        p = results_dir / rel
        if p.exists():
            return p

    if len(candidates) == 1:
        return candidates[0]

    # If multiple exist, choose the shallowest path.
    candidates.sort(key=lambda p: (len(p.parts), str(p)))
    return candidates[0]


def _load_per_trial_coop_rates(pd_json_path: Path) -> Dict[str, List[float]]:
    with pd_json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    game_results = data.get("game_results", {})
    out: Dict[str, List[float]] = {}

    for strategy_name, payload in game_results.items():
        agg = payload.get("aggregated_analysis", {})
        acr = agg.get("average_cooperation_rate", {})
        values = acr.get("values")
        if not isinstance(values, list):
            continue
        # Values are already per-repetition cooperation rates for the LLM player.
        cleaned: List[float] = []
        for v in values:
            try:
                cleaned.append(float(v))
            except Exception:
                cleaned.append(float("nan"))
        out[_normalize_strategy_name(strategy_name)] = cleaned

    if not out:
        raise ValueError(
            f"協力率の配列が見つかりませんでした: {pd_json_path}"
        )

    return out


def _read_template_csv(template_path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
    # Excel等で保存されたCSVはUTF-8 BOM付きのことがあるため utf-8-sig を使用
    with template_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"CSVヘッダが読み取れません: {template_path}")
        rows = list(reader)
        return list(reader.fieldnames), rows


def _write_csv(path: Path, fieldnames: List[str], rows: List[Dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="results配下の control_pd_games.json から、テンプレCSV(trial × vs戦略)の各セルに協力率を埋めます。"
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        required=True,
        help="例: results/20251227_100957_BFI20_PDI10_PDR100_Mgpt35turbo",
    )
    parser.add_argument(
        "--template",
        type=Path,
        required=True,
        help="例: /Users/mizuki/Downloads/GPT-3.5-turbo-baseline.csv",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="出力先（省略時はテンプレ名に _filled を付けます）",
    )
    parser.add_argument(
        "--pd-json",
        type=Path,
        default=None,
        help="control_pd_games.json を明示指定（省略時は results-dir 配下から自動検出）",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=10,
        help="1ゲームのラウンド数（表示・検証用。協力率自体はJSONのvaluesをそのまま使用）",
    )
    args = parser.parse_args()

    results_dir: Path = args.results_dir
    template_path: Path = args.template
    out_path: Path
    if args.out is None:
        out_path = template_path.with_name(
            f"{template_path.stem}_filled{template_path.suffix}"
        )
    else:
        out_path = args.out

    pd_json_path = args.pd_json or _find_control_pd_json(results_dir)
    per_trial = _load_per_trial_coop_rates(pd_json_path)

    fieldnames, rows = _read_template_csv(template_path)
    if not fieldnames:
        raise ValueError("CSVの列が空です。")
    normalized_headers = [h.strip().lstrip("\ufeff") for h in fieldnames]
    if "trial" not in normalized_headers:
        raise ValueError("テンプレCSVに trial 列がありません。")

    # Identify which columns correspond to opponents.
    opponent_cols = [
        c for c in fieldnames if c.strip().lstrip("\ufeff") != "trial"
    ]
    col_to_strategy: Dict[str, str] = {
        col: _extract_strategy_from_column(col) for col in opponent_cols
    }

    # Fill per-trial cooperation rates.
    for idx, row in enumerate(rows):
        trial_i = idx  # 0-based index into repetition arrays
        for col, strat in col_to_strategy.items():
            if not strat:
                continue
            values = per_trial.get(strat)
            if not values:
                row[col] = ""
                continue
            if trial_i >= len(values):
                row[col] = ""
                continue
            v = values[trial_i]
            # Keep a consistent compact representation (0.0–1.0). Typical resolution is 0.1 with 10 rounds.
            if v != v:  # NaN check
                row[col] = ""
            else:
                row[col] = f"{v:.3f}".rstrip("0").rstrip(".")

    _write_csv(out_path, fieldnames, rows)

    print(f"template: {template_path}")
    print(f"pd_json : {pd_json_path}")
    print(f"out     : {out_path}")
    print(f"n_trials: {len(rows)} (rounds per game assumed {args.rounds})")
    print(f"strategies in json: {sorted(per_trial.keys())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

