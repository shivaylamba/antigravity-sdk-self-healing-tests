import os
import sys
import argparse
import asyncio
from typing import List, Optional

from .adapters import register_builtin_adapters
from .config import load_app_config
from .failure_context import build_failure_context
from .orchestrator import build_context_with_adapters, run_healing_loop
from .types import HealOptions, SafetyControls

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
    heal_parser.add_argument("--provider", help="CI provider adapter to use (github-actions, gitlab-ci, jenkins, circleci, manual)")
    heal_parser.add_argument("--test-runner", help="Test adapter override (pytest, jest, playwright, maven-surefire, go-test, generic)")
    heal_parser.add_argument("--mode", choices=["local-dry-run", "local-apply", "ci-autonomous"], default=os.environ.get("AG_MODE", "local-apply"), help="Execution mode")
    heal_parser.add_argument("--config-file", help="Path to JSON config file")
    heal_parser.add_argument("--max-healing-attempts", type=int, help="Maximum healing attempts")
    heal_parser.add_argument("--allowed-paths", help="Comma-separated allowed file/path prefixes")
    heal_parser.add_argument("--max-patch-lines", type=int, help="Maximum changed lines allowed")
    heal_parser.add_argument("--rollback-on-guardrail-violation", choices=["true", "false"], help="Rollback changes when guardrails fail")
    heal_parser.add_argument("--audit-log-path", help="Audit log path")

    # Server command parser
    server_parser = subparsers.add_parser("server", help="Start Webhook server")
    server_parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8787)), help="Webhook server port")
    server_parser.add_argument("--model", default=os.environ.get("GEMINI_MODEL", "gemini-3.5-flash"), help="Gemini model to use")
    server_parser.add_argument("--api-key", default=os.environ.get("GEMINI_API_KEY") or os.environ.get("CURSOR_API_KEY"), help="Gemini API Key")
    server_parser.add_argument("--webhook-secret", default=os.environ.get("WEBHOOK_SECRET"), help="GitHub Webhook secret")

    args = parser.parse_args()

    if args.command == "heal":
        register_builtin_adapters()
        cwd = os.getcwd()
        cli_overrides = {
            "provider": args.provider,
            "testRunner": args.test_runner,
            "model": args.model,
            "apiKey": args.api_key,
            "testCommand": args.test_command,
            "mode": args.mode,
            "safety": {
                "maxHealingAttempts": args.max_healing_attempts,
                "allowedPaths": parse_list_arg(args.allowed_paths),
                "maxPatchLines": args.max_patch_lines,
                "rollbackOnGuardrailViolation": args.rollback_on_guardrail_violation,
                "auditLogPath": args.audit_log_path,
            },
        }
        app_config = load_app_config(cwd, args.config_file, cli_overrides)

        if not app_config.api_key:
            print("Error: GEMINI_API_KEY or --api-key is required.", file=sys.stderr)
            sys.exit(1)

        report_paths = parse_list_arg(args.report)
        final_command = app_config.test_command or args.test_command
        dry_run = args.dry_run or app_config.mode == "local-dry-run"
        provider_name = app_config.provider
        if args.failure_file:
            print("Building failure context from failure file...")
            failure_context = await build_failure_context(
                cwd=cwd,
                failure_file=args.failure_file,
                log_file=args.log_file,
                report_paths=report_paths,
                test_command=final_command,
                provider=provider_name,
            )
        else:
            print("Building failure context from adapters...")
            failure_context = await build_context_with_adapters(
                cwd=cwd,
                provider_name=provider_name,
                test_command=final_command,
                log_file=args.log_file,
            )
            failure_context.report_paths = list(set(failure_context.report_paths + report_paths))

        safety = app_config.safety if app_config.safety else SafetyControls()

        options = HealOptions(
            apiKey=app_config.api_key,
            model=app_config.model or args.model,
            cwd=cwd,
            mode=app_config.mode or args.mode,
            dryRun=dry_run,
            testCommand=final_command,
            failureContext=failure_context,
            repoUrl=failure_context.repo_url,
            startingRef=failure_context.branch,
            safety=safety,
        )

        result = await run_healing_loop(options)
        
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
