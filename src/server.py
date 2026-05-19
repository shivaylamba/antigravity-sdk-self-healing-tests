import os
import hmac
import hashlib
import asyncio
from typing import Optional
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.requests import Request
import uvicorn

from .types import HealOptions, FailureContext
from .agent_runner import run_healing_agent

def verify_github_signature(body: bytes, header: Optional[str], secret: str) -> bool:
    if not header or not header.startswith("sha256="):
        return False
    mac = hmac.new(secret.encode("utf-8"), body, hashlib.sha256)
    expected = "sha256=" + mac.hexdigest()
    return hmac.compare_digest(expected, header)

def github_payload_to_failure_context(event_name: str, payload: dict) -> Optional[FailureContext]:
    if event_name == "workflow_run" and payload.get("workflow_run", {}).get("conclusion") != "failure":
        return None
    if event_name == "check_suite" and payload.get("check_suite", {}).get("conclusion") != "failure":
        return None

    repo = payload.get("repository", {})
    workflow_run = payload.get("workflow_run", {})
    check_suite = payload.get("check_suite", {})
    
    branch = (workflow_run.get("head_branch") if workflow_run 
              else check_suite.get("head_branch") if check_suite 
              else payload.get("ref"))
    sha = (workflow_run.get("head_sha") if workflow_run 
           else check_suite.get("head_sha") if check_suite 
           else payload.get("after"))
    
    run_id = (str(workflow_run.get("id")) if workflow_run and workflow_run.get("id")
              else str(check_suite.get("id")) if check_suite and check_suite.get("id")
              else None)
    
    run_url = (workflow_run.get("html_url") if workflow_run 
               else check_suite.get("url") if check_suite 
               else None)
               
    job_name = (workflow_run.get("name") if workflow_run 
                else check_suite.get("app", {}).get("name") if check_suite 
                else None)

    return FailureContext(
        provider="webhook",
        repository=repo.get("full_name"),
        repoUrl=repo.get("html_url"),
        branch=branch,
        commitSha=sha,
        runId=run_id,
        runUrl=run_url,
        jobName=job_name,
        failedTests=[],
        reportPaths=[],
        logExcerpt=f"GitHub {event_name} reported a failing run. Inspect the repository and GitHub context for details."
    )

async def github_webhook(request: Request) -> JSONResponse:
    app_state = request.app.state
    body = await request.body()
    signature = request.headers.get("x-hub-signature-256")

    if app_state.webhook_secret and not verify_github_signature(body, signature, app_state.webhook_secret):
        return JSONResponse({"error": "invalid_signature"}, status_code=401)

    event_name = request.headers.get("x-github-event", "unknown")
    try:
        import json
        payload = json.loads(body.decode("utf-8"))
    except Exception:
        return JSONResponse({"error": "invalid_json"}, status_code=400)

    context = github_payload_to_failure_context(event_name, payload)
    if not context:
        return JSONResponse({"status": "ignored", "eventName": event_name}, status_code=202)

    options = HealOptions(
        apiKey=app_state.api_key,
        model=app_state.model,
        runtime="local",
        cwd=os.getcwd(),
        repoUrl=context.repo_url,
        startingRef=context.branch or context.base_branch,
        autoCreatePR=True,
        dryRun=False,
        failureContext=context
    )

    # Spawn healing run in background
    asyncio.create_task(run_healing_agent(options))

    return JSONResponse({
        "status": "started",
        "repository": context.repository,
        "runUrl": context.run_url
    }, status_code=202)

async def server_command(
    port: int,
    api_key: str,
    model: str,
    webhook_secret: Optional[str] = None
) -> None:
    app = Starlette(routes=[
        Route("/github/webhook", github_webhook, methods=["POST"])
    ])
    
    app.state.api_key = api_key
    app.state.model = model
    app.state.webhook_secret = webhook_secret

    print(f"Starting Antigravity self-healing webhook server on port {port}...")
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()
