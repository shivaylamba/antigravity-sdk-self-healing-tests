from typing import Literal, Optional, List, Any
from pydantic import BaseModel, Field, ConfigDict

class FailureContext(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    provider: Literal["github-actions", "manual", "webhook"]
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
    log_excerpt: Optional[str] = Field(default=None, alias="logExcerpt")
    raw_event_path: Optional[str] = Field(default=None, alias="rawEventPath")

class HealOptions(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    api_key: str = Field(..., alias="apiKey")
    model: str
    runtime: Literal["local"] = "local"  # Antigravity SDK runs locally
    cwd: str
    repo_url: Optional[str] = Field(default=None, alias="repoUrl")
    starting_ref: Optional[str] = Field(default=None, alias="startingRef")
    auto_create_pr: bool = Field(default=False, alias="autoCreatePR")
    dry_run: bool = Field(default=False, alias="dryRun")
    test_command: Optional[str] = Field(default=None, alias="testCommand")
    failure_context: FailureContext = Field(..., alias="failureContext")

class HealResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: Literal["finished", "error", "cancelled"]
    result: Optional[str] = None
    agent_id: str = Field(..., alias="agentId")
    run_id: str = Field(..., alias="runId")
    pr_urls: List[str] = Field(default_factory=list, alias="prUrls")
