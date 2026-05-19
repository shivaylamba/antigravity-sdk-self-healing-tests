import os
import sys
import uuid
from typing import Any
from google.antigravity import Agent, LocalAgentConfig
from google.antigravity.hooks import policy
from google.antigravity.types import Thought, Text, ToolCall, ToolResult

from .types import HealOptions, HealResult
from .prompt import build_healing_prompt
from .fs_utils import write_json

async def run_healing_agent(options: HealOptions) -> HealResult:
    # Set up config for the Antigravity Agent
    # Enable all tools and allow autonomous execution via policy.allow_all()
    config = LocalAgentConfig(
        system_instructions="You are TestFix, a senior QA automation engineer.",
        api_key=options.api_key,
        model=options.model,
        policies=[policy.allow_all()],
        workspaces=[options.cwd]
    )

    agent_id = str(uuid.uuid4())
    status = "finished"
    text_content = ""
    conv_id = "local-session"

    print("Initializing Google Antigravity Agent...")
    try:
        async with Agent(config) as agent:
            conv_id = agent.conversation_id or str(uuid.uuid4())
            prompt = build_healing_prompt(options.failure_context, options.dry_run)
            
            print(f"Sending prompt to agent (Conversation ID: {conv_id})...")
            response = await agent.chat(prompt)
            
            # Stream chunks in real-time
            async for chunk in response.chunks:
                if isinstance(chunk, Thought):
                    sys.stderr.write(chunk.text)
                    sys.stderr.flush()
                elif isinstance(chunk, Text):
                    sys.stdout.write(chunk.text)
                    sys.stdout.flush()
                elif isinstance(chunk, ToolCall):
                    # Safely render tool calls
                    args_summary = str(chunk.args)[:100] + ("..." if len(str(chunk.args)) > 100 else "")
                    sys.stderr.write(f"\n[tool] {chunk.name} calling with {args_summary}\n")
                    sys.stderr.flush()
                elif isinstance(chunk, ToolResult):
                    # Safely render tool results
                    success = chunk.error is None
                    sys.stderr.write(f"\n[tool result] {chunk.name}: success={success}\n")
                    sys.stderr.flush()

            text_content = await response.text()
    except Exception as e:
        print(f"\nAgent run failed with error: {e}", file=sys.stderr)
        status = "error"
        text_content = f"Error during healing: {e}"

    result = HealResult(
        status=status,
        result=text_content,
        agentId=agent_id,
        runId=conv_id,
        prUrls=[]
    )

    # Save outputs
    healer_dir = os.path.join(options.cwd, ".antigravity-healer")
    os.makedirs(healer_dir, exist_ok=True)
    
    write_json(os.path.join(healer_dir, "result.json"), result.model_dump(by_alias=True))
    await write_result_markdown(os.path.join(healer_dir, "result.md"), result)

    return result

async def write_result_markdown(path: str, result: HealResult) -> None:
    body = f"""## Google Antigravity self-healing test repair

**Status:** {result.status}

**Agent ID:** {result.agent_id}

**Conversation/Run ID:** {result.run_id}

### Antigravity result

{result.result or "No final result text was returned."}

### Pull requests

- Created by workflow step after this run
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
