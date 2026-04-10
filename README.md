# Overview

1. **BFI (Big Five Inventory) Measurement** — Conduct a 44-item personality assessment on an LLM without a persona to obtain baseline scores  
2. **Personality Manipulation** — Force specific Big Five traits (Extraversion, Agreeableness, Conscientiousness, Neuroticism, Openness) to high or low values  
3. **Prisoner’s Dilemma Game** — Let the manipulated LLM play against multiple strategies (e.g., TFT, GRIM, ALLC, ALLD) and measure cooperation rates and rewards  
4. **Output Results** — Save behavioral data for all rounds, BFI scores, and prompt logs in CSV/JSON format  

# Directory Structure

```
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

# Setup

## 1. Install Dependencies

```
pip install -r requirements.txt
```

## 2. Set API Key

Set your OpenAI API key using one of the following methods:

```
# Method A: Environment variable
export OPENAI_API_KEY="sk-..."

# Method B: Enter it in config.json under model_settings.api_key
```

## 3. Edit Experiment Configuration

Edit `config.json` to specify experiment parameters.

# Execution

```
python main.py
```

# Output

Results are saved in the `data/` directory.

# Available Strategies

- TFT: Tit for Tat — Mimics the opponent’s previous move  
- STFT: Suspicious TFT — Starts with defection, then mimics  
- GRIM: Defects forever after one defection  
- PAVLOV: Win-Stay, Lose-Shift  
- ALLC: Always cooperate  
- ALLD: Always defect  
- RANDOM: Random (50%)  
- UNFAIR_RANDOM: Random (30%)  
- FIXED_SEQUENCE: Fixed sequence  
- GRADUAL: Gradual retaliation  
- SOFT_MAJORITY: Majority of last 3 moves  
- HARD_MAJORITY: Majority of entire history  

---
