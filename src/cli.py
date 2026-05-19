import os
import sys
import argparse
import asyncio
from typing import List, Optional

from .failure_context import build_failure_context
from .agent_runner import run_healing_agent
from .types import HealOptions

def parse_list_arg(val: Optional[str]) -> List[str]:
    if not val:
        return []
    return [item.strip() for item in val.split(",") if item.strip()]

async def main_async() -> None:
    parser = argparse.ArgumentParser(description="Antigravity self-healing tests CLI")
    subparsers = parser.add_subparsers(dest="command", help="Subcommand to run")

    # Heal command parser
    heal_parser = subparsers.add_parser("heal", help="Heal failing tests")
    heal_parser.add_argument("--log-file", default=".antigravity-test.log", help="Path to test run logs")
    heal_parser.add_argument("--report", default="test-results,playwright-report,coverage", help="Comma-separated report paths")
    heal_parser.add_argument("--test-command", default=os.environ.get("TEST_COMMAND", "npm test"), help="Verification command")
    heal_parser.add_argument("--dry-run", action="store_true", help="Analyze without code edits")
    heal_parser.add_argument("--model", default=os.environ.get("GEMINI_MODEL", "gemini-3.5-flash"), help="Gemini model to use")
    heal_parser.add_argument("--api-key", default=os.environ.get("GEMINI_API_KEY") or os.environ.get("CURSOR_API_KEY"), help="Gemini API Key")
    heal_parser.add_argument("--failure-file", help="Path to failure context json override")

    # Server command parser
    server_parser = subparsers.add_parser("server", help="Start Webhook server")
    server_parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8787)), help="Webhook server port")
    server_parser.add_argument("--model", default=os.environ.get("GEMINI_MODEL", "gemini-3.5-flash"), help="Gemini model to use")
    server_parser.add_argument("--api-key", default=os.environ.get("GEMINI_API_KEY") or os.environ.get("CURSOR_API_KEY"), help="Gemini API Key")
    server_parser.add_argument("--webhook-secret", default=os.environ.get("WEBHOOK_SECRET"), help="GitHub Webhook secret")

    args = parser.parse_args()

    if args.command == "heal":
        if not args.api_key:
            print("Error: GEMINI_API_KEY or --api-key is required.", file=sys.stderr)
            sys.exit(1)

        report_paths = parse_list_arg(args.report)
        cwd = os.getcwd()

        print("Building failure context...")
        failure_context = await build_failure_context(
            cwd=cwd,
            failure_file=args.failure_file,
            log_file=args.log_file,
            report_paths=report_paths,
            test_command=args.test_command,
            provider="github-actions" if "GITHUB_ACTIONS" in os.environ else "manual"
        )

        options = HealOptions(
            apiKey=args.api_key,
            model=args.model,
            cwd=cwd,
            dryRun=args.dry_run,
            testCommand=args.test_command,
            failureContext=failure_context,
            repoUrl=failure_context.repo_url,
            startingRef=failure_context.branch
        )

        result = await run_healing_agent(options)
        
        print("\nAntigravity self-healing run complete")
        print(f"Agent ID: {result.agent_id}")
        print(f"Run ID: {result.run_id}")
        print(f"Status: {result.status}")

        if result.status != "finished":
            sys.exit(1)

    elif args.command == "server":
        if not args.api_key:
            print("Error: GEMINI_API_KEY or --api-key is required.", file=sys.stderr)
            sys.exit(1)

        from .server import server_command
        await server_command(
            port=args.port,
            api_key=args.api_key,
            model=args.model,
            webhook_secret=args.webhook_secret
        )
    else:
        parser.print_help()

def main():
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(1)

if __name__ == "__main__":
    main()
