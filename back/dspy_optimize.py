"""
DSPy Prompt Optimization for Agentic Trader (Simulation 2)

Replaces the informed algo with an LLM trader. Uses existing decision logs
to optimize the system prompt via DSPy's MIPROv2 optimizer.

Usage:
    # 1. Load existing logs and analyze baseline performance
    python dspy_optimize.py analyze

    # 2. Run optimization (requires OPENROUTER_API_KEY env var)
    python dspy_optimize.py optimize --template buyer_20_default --num-trials 20

    # 3. Deploy optimized prompt back to agentic_prompts.yaml
    python dspy_optimize.py deploy --template buyer_20_default

    # 4. Compare LLM vs informed algo from logged data
    python dspy_optimize.py compare --session SESSION_ID
"""

import argparse
import json
import os
import sys
import glob
import statistics
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

import dspy
import yaml


# ============================================================================
# paths
# ============================================================================

BACK_DIR = Path(__file__).parent
LOGS_DIR = BACK_DIR / "logs" / "agentic"
CONFIG_PATH = BACK_DIR / "config" / "agentic_prompts.yaml"
OPTIMIZED_DIR = BACK_DIR / "dspy_optimized"


# ============================================================================
# 1. data loading — convert decision logs to DSPy examples
# ============================================================================

@dataclass
class TradingEpisode:
    """One market run for one trader."""
    market_id: str
    trader_id: str
    goal: int
    decisions: list = field(default_factory=list)
    terminal_reward: float = 0.0
    terminal_vwap: float = 0.0
    goal_progress: int = 0
    goal_complete: bool = False


def load_episodes(session_filter: str = None, min_decisions: int = 3) -> list[TradingEpisode]:
    """Load trading episodes from agentic log files.

    Args:
        session_filter: Only load logs matching this session prefix (e.g. 'SESSION_1770056396')
        min_decisions: Skip episodes with fewer than this many decisions
    """
    episodes = []
    pattern = f"{session_filter}*.json" if session_filter else "*.json"

    for filepath in sorted(LOGS_DIR.glob(pattern)):
        if filepath.name == "unknown.json":
            continue

        try:
            with open(filepath) as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            continue

        market_id = data.get("market_id", filepath.stem)

        for trader_id, trader_data in data.get("traders", {}).items():
            decisions = trader_data.get("decision_log", [])
            if len(decisions) < min_decisions:
                continue

            goal = trader_data.get("goal", 0)

            # Extract terminal metrics from last decision
            last = decisions[-1] if decisions else {}
            terminal_reward = last.get("current_reward", 0.0)
            terminal_vwap = last.get("current_vwap", 0.0)
            goal_progress = int(last.get("goal_progress", 0))

            perf = trader_data.get("performance", {})
            goal_complete = perf.get("goal_complete", abs(goal_progress) >= abs(goal) if goal != 0 else False)

            episodes.append(TradingEpisode(
                market_id=market_id,
                trader_id=trader_id,
                goal=goal,
                decisions=decisions,
                terminal_reward=terminal_reward,
                terminal_vwap=terminal_vwap,
                goal_progress=goal_progress,
                goal_complete=goal_complete,
            ))

    return episodes


def episodes_to_dspy_examples(episodes: list[TradingEpisode]) -> list[dspy.Example]:
    """Convert episodes into DSPy training examples.

    Each example is a single decision step with a reconstructed market state
    string, plus the outcome (reward delta, whether the action was successful).
    The example fields match the TradingAction signature inputs exactly.
    """
    examples = []

    for ep in episodes:
        for i, decision in enumerate(ep.decisions):
            args = decision.get("args", {})
            result = decision.get("result", {})

            # Skip failed LLM calls
            if not decision.get("action"):
                continue

            prev_reward = ep.decisions[i - 1].get("current_reward", 0.0) if i > 0 else 0.0
            reward_delta = decision.get("current_reward", 0.0) - prev_reward

            goal_progress = int(decision.get("goal_progress", 0))
            vwap = decision.get("current_vwap", 0.0)
            reward = decision.get("current_reward", 0.0)
            goal_size = abs(ep.goal)
            remaining = max(0, goal_size - abs(goal_progress))

            # Reconstruct a compact market state from logged data
            market_state = (
                f"VWAP: {vwap:.2f} | Reward: {reward:.2f} | "
                f"Completed: {abs(goal_progress)}/{goal_size} | Remaining: {remaining} | "
                f"Last action: {ep.decisions[i-1].get('action', 'none') if i > 0 else 'none'}"
            )

            ex = dspy.Example(
                market_state=market_state,
                goal=str(ep.goal),
                goal_progress=str(goal_progress),
                action=decision["action"],
                price=str(args.get("price", "")),
                reasoning=args.get("reasoning", ""),
                success=str(result.get("success", False)),
                reward=f"{reward:.2f}",
                reward_delta=f"{reward_delta:.2f}",
            ).with_inputs("market_state", "goal", "goal_progress")

            examples.append(ex)

    return examples


# ============================================================================
# 2. DSPy signature and module
# ============================================================================

class TradingAction(dspy.Signature):
    """Given a market state, decide the best trading action to maximize reward.

    You are a trading agent in a limit order book market. You can place
    1-share limit orders, cancel existing orders, or hold. Your goal is
    to complete your share target at the best possible VWAP (volume-weighted
    average price).
    """
    # Inputs
    market_state: str = dspy.InputField(
        desc="Full market state: order book, time remaining, goal progress, VWAP, resources, pending orders"
    )
    goal: str = dspy.InputField(
        desc="Trading goal: positive = buy N shares, negative = sell N shares"
    )
    goal_progress: str = dspy.InputField(
        desc="Shares completed so far toward goal"
    )

    # Outputs
    action: str = dspy.OutputField(
        desc="One of: place_order, cancel_order, hold"
    )
    price: str = dspy.OutputField(
        desc="Limit price if placing an order, order_id if cancelling, empty if holding"
    )
    reasoning: str = dspy.OutputField(
        desc="Brief explanation of why this action maximizes reward"
    )


class TradingAgent(dspy.Module):
    """DSPy module that wraps the trading decision with chain-of-thought."""

    def __init__(self):
        super().__init__()
        self.decide = dspy.ChainOfThought(TradingAction)

    def forward(self, market_state: str, goal: str, goal_progress: str) -> dspy.Prediction:
        return self.decide(
            market_state=market_state,
            goal=goal,
            goal_progress=goal_progress,
        )


# ============================================================================
# 3. metric function
# ============================================================================

def trading_metric(example: dspy.Example, prediction: dspy.Prediction, trace=None) -> float:
    """Score a trading decision.

    Scoring criteria:
    - Action validity (is it a real action?)
    - Price reasonableness (is it a valid integer?)
    - Reward direction (did the decision improve reward?)
    """
    score = 0.0

    # Valid action
    action = getattr(prediction, "action", "").strip().lower()
    if action in ("place_order", "cancel_order", "hold"):
        score += 0.3

    # Price is a valid integer for place_order
    if action == "place_order":
        try:
            p = int(getattr(prediction, "price", "0"))
            if 80 <= p <= 120:  # reasonable range around default_price=100
                score += 0.3
        except (ValueError, TypeError):
            pass
    elif action in ("cancel_order", "hold"):
        score += 0.3  # no price needed

    # Has reasoning
    reasoning = getattr(prediction, "reasoning", "")
    if len(reasoning) > 10:
        score += 0.1

    # Match the ground-truth reward direction
    try:
        reward_delta = float(example.reward_delta)
        if reward_delta > 0:
            score += 0.3  # this was a good decision in the logs
        elif reward_delta == 0:
            score += 0.1
    except (ValueError, AttributeError):
        pass

    return score


# ============================================================================
# 4. optimization
# ============================================================================

def run_optimization(
    template_name: str,
    num_trials: int = 20,
    model: str = "openrouter/anthropic/claude-haiku-4.5",
):
    """Run DSPy MIPROv2 optimization on collected trading episodes."""

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY environment variable not set")
        sys.exit(1)

    # Configure DSPy LM
    lm = dspy.LM(
        model=model,
        api_key=api_key,
        api_base="https://openrouter.ai/api/v1",
        temperature=0.3,
        max_tokens=500,
    )
    dspy.configure(lm=lm)

    # Load data
    print(f"Loading episodes from {LOGS_DIR}...")
    episodes = load_episodes()

    # Filter to matching goal direction
    templates = yaml.safe_load(open(CONFIG_PATH))["templates"]
    template = templates.get(template_name)
    if not template:
        print(f"ERROR: Template '{template_name}' not found in {CONFIG_PATH}")
        sys.exit(1)

    goal = template["goal"]
    matching = [ep for ep in episodes if ep.goal == goal]
    print(f"Found {len(matching)} episodes with goal={goal} (template: {template_name})")

    if len(matching) < 5:
        print(f"WARNING: Only {len(matching)} episodes. Need at least 5 for optimization.")
        print("Run more headless simulations first: POST /admin/run_headless_batch?num_markets=20")
        if len(matching) == 0:
            sys.exit(1)

    # Convert to DSPy examples
    examples = episodes_to_dspy_examples(matching)
    print(f"Converted to {len(examples)} training examples (individual decisions)")

    # Split train/val
    split = max(1, int(len(examples) * 0.8))
    train_set = examples[:split]
    val_set = examples[split:] if split < len(examples) else examples[:max(1, len(examples) // 5)]

    print(f"Train: {len(train_set)}, Val: {len(val_set)}")

    # Create module
    agent = TradingAgent()

    # Run optimizer
    # DSPy 3.x uses auto="light"|"medium"|"heavy" instead of num_trials
    auto_level = "light" if num_trials <= 10 else "medium" if num_trials <= 30 else "heavy"
    print(f"\nStarting MIPROv2 optimization (auto={auto_level})...")
    optimizer = dspy.MIPROv2(
        metric=trading_metric,
        num_threads=4,
        max_bootstrapped_demos=3,
        max_labeled_demos=3,
        auto=auto_level,
    )

    optimized_agent = optimizer.compile(
        agent,
        trainset=train_set,
        minibatch_size=min(25, len(train_set)),
    )

    # Save optimized module
    OPTIMIZED_DIR.mkdir(exist_ok=True)
    save_path = OPTIMIZED_DIR / f"{template_name}_optimized.json"
    optimized_agent.save(str(save_path))
    print(f"\nOptimized module saved to: {save_path}")

    # Extract and display the optimized prompt
    print("\n" + "=" * 60)
    print("OPTIMIZED PROMPT")
    print("=" * 60)

    # DSPy stores the optimized instructions in the module's predictor
    for name, param in optimized_agent.named_parameters():
        if hasattr(param, "signature"):
            instructions = getattr(param.signature, "instructions", "")
            if instructions:
                print(f"\n[{name}] Instructions:\n{instructions}")
        if hasattr(param, "demos"):
            print(f"\n[{name}] Few-shot demos: {len(param.demos)}")
            for i, demo in enumerate(param.demos):
                print(f"  Demo {i+1}: action={getattr(demo, 'action', '?')}, "
                      f"price={getattr(demo, 'price', '?')}, "
                      f"reward={getattr(demo, 'reward', '?')}")

    # Evaluate on validation set
    print("\n" + "=" * 60)
    print("VALIDATION RESULTS")
    print("=" * 60)

    evaluator = dspy.Evaluate(
        devset=val_set,
        metric=trading_metric,
        num_threads=4,
        display_progress=True,
    )

    baseline_score = evaluator(agent)
    optimized_score = evaluator(optimized_agent)

    print(f"\nBaseline score:  {baseline_score:.2f}")
    print(f"Optimized score: {optimized_score:.2f}")
    print(f"Improvement:     {optimized_score - baseline_score:+.2f}")

    return optimized_agent


# ============================================================================
# 5. deploy — extract optimized prompt back to YAML
# ============================================================================

def deploy_optimized_prompt(template_name: str):
    """Load optimized DSPy module and deploy its prompt to agentic_prompts.yaml."""

    save_path = OPTIMIZED_DIR / f"{template_name}_optimized.json"
    if not save_path.exists():
        print(f"ERROR: No optimized module found at {save_path}")
        print(f"Run optimization first: python dspy_optimize.py optimize --template {template_name}")
        sys.exit(1)

    # Load optimized module
    agent = TradingAgent()
    agent.load(str(save_path))

    # Extract the optimized instructions
    optimized_instructions = None
    demos_text = ""

    for name, param in agent.named_parameters():
        if hasattr(param, "signature"):
            optimized_instructions = getattr(param.signature, "instructions", None)
        if hasattr(param, "demos") and param.demos:
            # Format demos as few-shot examples in the prompt
            demo_lines = []
            for i, demo in enumerate(param.demos):
                demo_lines.append(f"Example {i+1}:")
                if hasattr(demo, "market_state"):
                    demo_lines.append(f"  Market: {str(getattr(demo, 'market_state', ''))[:100]}...")
                demo_lines.append(f"  Action: {getattr(demo, 'action', '?')}")
                demo_lines.append(f"  Price: {getattr(demo, 'price', '?')}")
                demo_lines.append(f"  Reasoning: {getattr(demo, 'reasoning', '?')}")
            demos_text = "\n".join(demo_lines)

    if not optimized_instructions:
        print("WARNING: No optimized instructions found in module. Using original prompt.")
        return

    # Build the new prompt
    new_prompt = optimized_instructions
    if demos_text:
        new_prompt += f"\n\nHere are examples of good trading decisions:\n{demos_text}"

    # Load current YAML
    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)

    templates = config.get("templates", {})
    if template_name not in templates:
        print(f"ERROR: Template '{template_name}' not found in config")
        sys.exit(1)

    # Save backup
    backup_path = CONFIG_PATH.with_suffix(".yaml.bak")
    with open(backup_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    print(f"Backup saved to: {backup_path}")

    # Create optimized version as a new template (don't overwrite original)
    optimized_name = f"{template_name}_dspy_optimized"
    templates[optimized_name] = {
        **templates[template_name],
        "name": f"{templates[template_name]['name']} (DSPy optimized)",
        "prompt": new_prompt,
    }

    config["templates"] = templates
    with open(CONFIG_PATH, "w") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    print(f"\nDeployed optimized prompt as template: '{optimized_name}'")
    print(f"Original template '{template_name}' is preserved.")
    print(f"\nTo use it, set agentic_prompt_template='{optimized_name}' in your settings.")


# ============================================================================
# 6. analyze — summarize existing log data
# ============================================================================

def analyze_logs(session_filter: str = None):
    """Analyze existing decision logs and print summary statistics."""

    episodes = load_episodes(session_filter=session_filter, min_decisions=1)

    if not episodes:
        print(f"No episodes found in {LOGS_DIR}")
        print("Run headless simulations first: POST /admin/run_headless_batch?num_markets=20")
        return

    print(f"Found {len(episodes)} episodes across {len(set(ep.market_id for ep in episodes))} markets\n")

    # Group by goal
    by_goal = {}
    for ep in episodes:
        by_goal.setdefault(ep.goal, []).append(ep)

    for goal, eps in sorted(by_goal.items()):
        rewards = [ep.terminal_reward for ep in eps]
        vwaps = [ep.terminal_vwap for ep in eps if ep.terminal_vwap > 0]
        completions = sum(1 for ep in eps if ep.goal_complete)
        decisions_per_ep = [len(ep.decisions) for ep in eps]

        direction = "BUY" if goal > 0 else "SELL" if goal < 0 else "SPEC"
        print(f"Goal: {direction} {abs(goal)} shares ({len(eps)} episodes)")
        print(f"  Completion rate: {completions}/{len(eps)} ({completions/len(eps)*100:.0f}%)")
        print(f"  Reward:  mean={statistics.mean(rewards):.2f}, "
              f"std={statistics.stdev(rewards):.2f}" if len(rewards) > 1 else f"  Reward: {rewards[0]:.2f}")
        if vwaps:
            print(f"  VWAP:    mean={statistics.mean(vwaps):.2f}, "
                  f"std={statistics.stdev(vwaps):.2f}" if len(vwaps) > 1 else f"  VWAP: {vwaps[0]:.2f}")
        print(f"  Decisions/episode: mean={statistics.mean(decisions_per_ep):.1f}, "
              f"range=[{min(decisions_per_ep)}, {max(decisions_per_ep)}]")

        # Top 5 and bottom 5 by reward
        sorted_eps = sorted(eps, key=lambda e: e.terminal_reward, reverse=True)
        print(f"  Best 3:  {[f'{e.terminal_reward:.1f} (VWAP={e.terminal_vwap:.1f})' for e in sorted_eps[:3]]}")
        print(f"  Worst 3: {[f'{e.terminal_reward:.1f} (VWAP={e.terminal_vwap:.1f})' for e in sorted_eps[-3:]]}")
        print()


# ============================================================================
# 7. compare — LLM vs informed algo from logs
# ============================================================================

def compare_results(session_id: str = None):
    """Compare LLM trader results vs informed algo results from log data.

    Looks at market logs to extract both agentic and informed trader performance.
    """
    episodes = load_episodes(session_filter=session_id, min_decisions=1)

    if not episodes:
        print("No episodes found. Run simulations first.")
        return

    # Summary for paper
    print("=" * 70)
    print("LLM TRADER PERFORMANCE SUMMARY (for comparison with informed algo)")
    print("=" * 70)

    by_goal = {}
    for ep in episodes:
        by_goal.setdefault(ep.goal, []).append(ep)

    for goal, eps in sorted(by_goal.items()):
        rewards = [ep.terminal_reward for ep in eps]
        vwaps = [ep.terminal_vwap for ep in eps if ep.terminal_vwap > 0]
        completions = sum(1 for ep in eps if ep.goal_complete)

        direction = "BUY" if goal > 0 else "SELL" if goal < 0 else "SPEC"
        n = len(eps)

        print(f"\n--- {direction} {abs(goal)} shares (n={n}) ---")
        print(f"  Fill rate:      {completions/n*100:.1f}%")

        if len(rewards) > 1:
            print(f"  Terminal reward: {statistics.mean(rewards):.2f} +/- {statistics.stdev(rewards):.2f}")
        else:
            print(f"  Terminal reward: {rewards[0]:.2f}")

        if vwaps and len(vwaps) > 1:
            print(f"  Terminal VWAP:   {statistics.mean(vwaps):.2f} +/- {statistics.stdev(vwaps):.2f}")
        elif vwaps:
            print(f"  Terminal VWAP:   {vwaps[0]:.2f}")

        # Efficiency: how many decisions to reach goal
        completed_eps = [ep for ep in eps if ep.goal_complete]
        if completed_eps:
            decisions_to_complete = [len(ep.decisions) for ep in completed_eps]
            print(f"  Decisions to complete: {statistics.mean(decisions_to_complete):.1f} "
                  f"+/- {statistics.stdev(decisions_to_complete):.1f}" if len(decisions_to_complete) > 1
                  else f"  Decisions to complete: {decisions_to_complete[0]}")

    print("\n" + "=" * 70)
    print("NOTE: To compare with informed algo, run the same market config with")
    print("num_informed_traders=1, num_agentic_traders=0, then compare metrics.")
    print("The informed algo's VWAP/reward can be extracted from market logs")
    print("using: python -c 'from utils.logfiles_analysis import ...'")
    print("=" * 70)


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="DSPy prompt optimization for agentic trader")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # analyze
    p_analyze = subparsers.add_parser("analyze", help="Analyze existing decision logs")
    p_analyze.add_argument("--session", type=str, default=None, help="Filter by session ID prefix")

    # optimize
    p_optimize = subparsers.add_parser("optimize", help="Run DSPy optimization")
    p_optimize.add_argument("--template", type=str, default="buyer_20_default", help="Template to optimize")
    p_optimize.add_argument("--num-trials", type=int, default=20, help="Number of optimization trials")
    p_optimize.add_argument("--model", type=str, default="openrouter/anthropic/claude-haiku-4.5",
                           help="LLM model for optimization")

    # deploy
    p_deploy = subparsers.add_parser("deploy", help="Deploy optimized prompt to YAML")
    p_deploy.add_argument("--template", type=str, required=True, help="Template name to deploy")

    # compare
    p_compare = subparsers.add_parser("compare", help="Compare LLM vs informed algo results")
    p_compare.add_argument("--session", type=str, default=None, help="Filter by session ID")

    args = parser.parse_args()

    if args.command == "analyze":
        analyze_logs(session_filter=args.session)
    elif args.command == "optimize":
        run_optimization(
            template_name=args.template,
            num_trials=args.num_trials,
            model=args.model,
        )
    elif args.command == "deploy":
        deploy_optimized_prompt(template_name=args.template)
    elif args.command == "compare":
        compare_results(session_id=args.session)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
