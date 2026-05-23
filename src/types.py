from typing import Literal, Optional, List, Dict
from pydantic import BaseModel, Field, ConfigDict

class FailureContext(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    provider: str
    pipeline_id: Optional[str] = Field(default=None, alias="pipelineId")
    pipeline_url: Optional[str] = Field(default=None, alias="pipelineUrl")
    pipeline_name: Optional[str] = Field(default=None, alias="pipelineName")
    repository: Optional[str] = None
    repo_url: Optional[str] = Field(default=None, alias="repoUrl")
    branch: Optional[str] = None
    base_branch: Optional[str] = Field(default=None, alias="baseBranch")
    commit_sha: Optional[str] = Field(default=None, alias="commitSha")
    run_id: Optional[str] = Field(default=None, alias="runId")
    run_url: Optional[str] = Field(default=None, alias="runUrl")
    job_name: Optional[str] = Field(default=None, alias="jobName")
    failed_tests: List[str] = Field(default_factory=list, alias="failedTests")
    test_command: Optional[str] = Field(default=None, alias="testCommand")
    report_paths: List[str] = Field(default_factory=list, alias="reportPaths")
    artifacts: List[str] = Field(default_factory=list)
    environment: Dict[str, str] = Field(default_factory=dict)
    log_excerpt: Optional[str] = Field(default=None, alias="logExcerpt")
    raw_event_path: Optional[str] = Field(default=None, alias="rawEventPath")


class SafetyControls(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    max_healing_attempts: int = Field(default=1, alias="maxHealingAttempts")
    allowed_paths: List[str] = Field(default_factory=list, alias="allowedPaths")
    max_patch_lines: int = Field(default=400, alias="maxPatchLines")
    rollback_on_guardrail_violation: bool = Field(default=True, alias="rollbackOnGuardrailViolation")
    audit_log_path: str = Field(default=".antigravity-healer/audit.log", alias="auditLogPath")

class HealOptions(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    api_key: str = Field(..., alias="apiKey")
    model: str
    runtime: Literal["local"] = "local"  # Antigravity SDK runs locally
    cwd: str
    mode: Literal["local-dry-run", "local-apply", "ci-autonomous", "webhook-server"] = "local-apply"
    repo_url: Optional[str] = Field(default=None, alias="repoUrl")
    starting_ref: Optional[str] = Field(default=None, alias="startingRef")
    auto_create_pr: bool = Field(default=False, alias="autoCreatePR")
    dry_run: bool = Field(default=False, alias="dryRun")
    test_command: Optional[str] = Field(default=None, alias="testCommand")
    failure_context: FailureContext = Field(..., alias="failureContext")
    safety: SafetyControls = Field(default_factory=SafetyControls)

class HealResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: Literal["finished", "error", "cancelled"]
    result: Optional[str] = None
    agent_id: str = Field(..., alias="agentId")
    run_id: str = Field(..., alias="runId")
    pr_urls: List[str] = Field(default_factory=list, alias="prUrls")
