# agent.py
"""
A single agent that calls Claude repeatedly to answer one question,
printing a trace of every step to the terminal.

Usage:
    python agent.py "Can I drive to San Francisco without charging?"
    python agent.py --verbose "..."   # also dump the full message list each step
"""

import argparse
import json
import os
import time

from anthropic import Anthropic
from dotenv import load_dotenv

from agent_tools import TOOLS, TOOL_FUNCTIONS

load_dotenv()

MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
MAX_STEPS = 10

SYSTEM = """You are an assistant for the owner of a Hyundai Ioniq electric car.
Answer the owner's question by gathering facts with your tools rather than guessing.
Use as many tool calls as you need, and call independent tools in parallel.
Distances are in miles. Keep the final answer short and practical."""

client = Anthropic()


# ---------- Trace printing ----------

BOLD, DIM, CYAN, YELLOW, GREEN, RED, RESET = (
    "\033[1m", "\033[2m", "\033[36m", "\033[33m", "\033[32m", "\033[31m", "\033[0m"
)


def trace(label, text="", color=""):
    print(f"{color}{BOLD}{label}{RESET} {text}")


def trace_body(text, color=""):
    for line in str(text).splitlines():
        print(f"{color}    │ {line}{RESET}")


def shorten(value, limit=400):
    text = value if isinstance(value, str) else json.dumps(value)
    return text if len(text) <= limit else text[:limit] + f"... ({len(text)} chars)"


def dump_messages(messages):
    def to_jsonable(obj):
        return obj.model_dump(exclude_none=True) if hasattr(obj, "model_dump") else str(obj)
    trace_body(json.dumps(messages, indent=2, default=to_jsonable), DIM)


# ---------- Tool execution ----------

def run_tool(name, tool_input):
    """Run one tool and return (result_text, is_error)."""
    func = TOOL_FUNCTIONS.get(name)
    if func is None:
        return f"Unknown tool: {name}", True
    try:
        return json.dumps(func(**tool_input)), False
    except Exception as e:
        return f"{type(e).__name__}: {e}", True


# ---------- Agent loop ----------

def run_agent(question, verbose=False):
    messages = [{"role": "user", "content": question}]
    totals = {"input": 0, "output": 0}
    started = time.perf_counter()

    trace("QUESTION", question, CYAN)
    trace("MODEL", MODEL, DIM)

    for step in range(1, MAX_STEPS + 1):
        print()
        trace(f"━━ Step {step} ━━", "calling Claude...", CYAN)
        if verbose:
            trace("messages sent:", "", DIM)
            dump_messages(messages)

        t0 = time.perf_counter()
        response = client.messages.create(
            model=MODEL,
            max_tokens=16000,
            system=SYSTEM,
            thinking={"type": "adaptive", "display": "summarized"},
            tools=TOOLS,
            messages=messages,
        )
        elapsed = time.perf_counter() - t0

        usage = response.usage
        totals["input"] += usage.input_tokens
        totals["output"] += usage.output_tokens
        trace(
            "claude:",
            f"stop={response.stop_reason}  {elapsed:.1f}s  "
            f"tokens in={usage.input_tokens} out={usage.output_tokens}  "
            f"(running total in={totals['input']} out={totals['output']})",
            DIM,
        )

        # Show what Claude produced, in order: thinking, text, tool calls
        for block in response.content:
            if block.type == "thinking":
                trace("💭 thinking", "", YELLOW)
                trace_body(block.thinking or "(empty)", YELLOW)
            elif block.type == "text":
                trace("💬 text", "", GREEN)
                trace_body(block.text, GREEN)
            elif block.type == "tool_use":
                trace("🔧 tool call", f"{block.name}({json.dumps(block.input)})", CYAN)

        # Keep the whole response (thinking blocks included) in the conversation
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            if response.stop_reason != "end_turn":
                trace("⚠ stopped early:", response.stop_reason, RED)
            answer = "".join(b.text for b in response.content if b.type == "text")
            print()
            trace(
                "━━ Done ━━",
                f"{step} Claude call(s), {time.perf_counter() - started:.1f}s total, "
                f"tokens in={totals['input']} out={totals['output']}",
                CYAN,
            )
            return answer

        # Run every tool Claude asked for; send all results back in one message
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            t0 = time.perf_counter()
            result, is_error = run_tool(block.name, block.input)
            color = RED if is_error else DIM
            trace(f"   ↳ {block.name}", f"{'ERROR ' if is_error else ''}({time.perf_counter() - t0:.1f}s)", color)
            trace_body(shorten(result), color)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result,
                "is_error": is_error,
            })
        messages.append({"role": "user", "content": tool_results})

    trace("⚠ Step limit reached", f"({MAX_STEPS} Claude calls) without a final answer", RED)
    return None


def main():
    parser = argparse.ArgumentParser(description="Ask the car agent a question.")
    parser.add_argument("question")
    parser.add_argument("--verbose", action="store_true", help="dump the full message list sent each step")
    args = parser.parse_args()

    answer = run_agent(args.question, verbose=args.verbose)
    if answer:
        print()
        trace("ANSWER", "", GREEN)
        trace_body(answer, GREEN)


if __name__ == "__main__":
    main()
