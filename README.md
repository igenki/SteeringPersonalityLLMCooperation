# Overview

1. **BFI (Big Five Inventory) Measurement**  
   Conduct a 44-item personality assessment on an LLM without a persona to obtain baseline scores.

2. **Personality Manipulation**  
   Force specific Big Five traits (Extraversion, Agreeableness, Conscientiousness, Neuroticism, Openness) to high or low values.

3. **Prisoner’s Dilemma Game**  
   Let the manipulated LLM play against multiple strategies (e.g., TFT, GRIM, ALLC, ALLD) and measure cooperation rates and rewards.

4. **Output Results**  
   Save behavioral data for all rounds, BFI scores, and prompt logs in CSV/JSON format.

---

# Directory Structure

```text
.
├── main.py                  # Entry point for the experiment
├── config.json              # Experiment configuration file
├── requirements.txt         # Python dependencies
├── src/
│   ├── bfi_analyzer.py      # Sending BFI questions, parsing responses, computing scores
│   ├── model_client.py      # OpenAI / HuggingFace API client
│   ├── pd_game.py           # Execution of the Prisoner’s Dilemma game
│   ├── strategies.py        # Opponent strategies (TFT, GRIM, ALLC, etc.)
│   ├── prompt_templates.py  # Prompt generation for different BFI modes
│   ├── csv_exporter.py      # Exporting experiment results to CSV
│   └── prompt_logger.py     # Logging LLM input/output
├── Re_BFI/                  # Scripts for repeated BFI experiments
├── scripts/                 # Utility scripts
├── results/                 # Experiment results (not tracked by git)
└── logs/                    # Execution logs (auto-generated)
```

---

# Setup

## 1. Install Dependencies

```bash
pip install -r requirements.txt
```

## 2. Set API Key

Set your OpenAI API key using one of the following methods:

```bash
# Method A: Environment variable
export OPENAI_API_KEY="sk-..."

# Method B: Enter it in config.json under model_settings.api_key
```

## 3. Edit Experiment Configuration

Edit `config.json` to specify experiment parameters.

Example:

```json
{
  "model_settings": {
    "model_name": "gpt-3.5-turbo",
    "provider": "openai"
  },
  "bfi_settings": {
    "iterations": 2,
    "modes": ["numbers_and_language", "no_prompt"]
  },
  "pd_game_settings": {
    "iterations": 10,
    "repetitions": 3,
    "prompt_templates": ["competitive"],
    "collect_reasoning": true
  },
  "strategy_settings": {
    "strategies": ["ALLC", "ALLD", "TFT", "GRIM"]
  },
  "personality_modification_settings": {
    "target_traits": ["extraversion", "agreeableness"],
    "forced_scores": [1, 5]
  }
}
```

### Key Configuration Parameters

| Section | Key | Description |
|---|---|---|
| `model_settings` | `model_name` | Name of the LLM model to use |
| `bfi_settings` | `iterations` | Number of repetitions of the BFI questionnaire |
| `bfi_settings` | `modes` | BFI prompt modes (e.g., `numbers_and_language`, `no_prompt`) |
| `pd_game_settings` | `iterations` | Number of rounds per game |
| `pd_game_settings` | `repetitions` | Number of repetitions under the same condition |
| `strategy_settings` | `strategies` | List of opponent strategies |
| `personality_modification_settings` | `target_traits` | Target Big Five traits for manipulation |
| `personality_modification_settings` | `forced_scores` | Forced scores (1–5) |

---

# Execution

```bash
python main.py
```

To use a custom configuration file:

```bash
python main.py --config path/to/custom_config.json
```

---

# Output

Results are saved in the `data/` directory (configurable via `output_dir` in `config.json`) with the following structure:

```text
data/
└── 20260306_120000_BFI2_PDI10_PDR3_Mgpt35turbo/
    ├── control_BFI.json                         # Baseline BFI scores
    ├── BFInumbers_and_language_PDcompetitive/
    │   ├── control_pd_games.json                # PD game results (control condition)
    │   ├── agreeableness_score_1_modification_experiment.json
    │   ├── agreeableness_score_5_modification_experiment.json
    │   ├── ...
    │   └── prompt_logs/                         # Prompt input/output logs
    ├── BFIno_prompt_PDcompetitive/
    │   └── ...
    └── prompt_logs/                             # Aggregated prompt logs
```

---

# Available Strategies

| Name | Description |
|---|---|
| `TFT` | Tit for Tat — Mimics the opponent’s previous move |
| `STFT` | Suspicious TFT — Starts with defection, then mimics |
| `GRIM` | Defects forever after a single defection |
| `PAVLOV` | Win-Stay, Lose-Shift |
| `ALLC` | Always cooperate |
| `ALLD` | Always defect |
| `RANDOM` | Random (50% cooperation probability) |
| `UNFAIR_RANDOM` | Random (30% cooperation probability) |
| `FIXED_SEQUENCE` | Acts according to a fixed sequence |
| `GRADUAL` | Gradual retaliation |
| `SOFT_MAJORITY` | Majority of the last 3 moves |
| `HARD_MAJORITY` | Majority of the entire history |

---
