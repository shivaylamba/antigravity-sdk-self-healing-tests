import os
from typing import Dict, Optional

from ..types import FailureContext
from .base import CIProviderAdapter
from .registry import register_provider


class GitHubActionsAdapter:
    name = "github-actions"

    def can_handle(self, environ: Dict[str, str]) -> bool:
        return "GITHUB_ACTIONS" in environ

    def build_context(self, cwd: str, environ: Dict[str, str], log_excerpt: Optional[str]) -> FailureContext:
        repository = environ.get("GITHUB_REPOSITORY")
        run_id = environ.get("GITHUB_RUN_ID")
        server = environ.get("GITHUB_SERVER_URL", "https://github.com")
        return FailureContext(
            provider=self.name,
            repository=repository,
            repoUrl=f"{server}/{repository}" if repository else None,
            branch=environ.get("GITHUB_HEAD_REF") or environ.get("GITHUB_REF_NAME"),
            baseBranch=environ.get("GITHUB_BASE_REF"),
            commitSha=environ.get("GITHUB_SHA"),
            runId=run_id,
            runUrl=f"{server}/{repository}/actions/runs/{run_id}" if repository and run_id else None,
            pipelineId=run_id,
            pipelineUrl=f"{server}/{repository}/actions/runs/{run_id}" if repository and run_id else None,
            pipelineName=environ.get("GITHUB_WORKFLOW"),
            jobName=environ.get("GITHUB_JOB"),
            logExcerpt=log_excerpt,
            environment=_safe_subset(environ),
        )


class GitLabCIAdapter:
    name = "gitlab-ci"

    def can_handle(self, environ: Dict[str, str]) -> bool:
        return environ.get("GITLAB_CI") == "true"

    def build_context(self, cwd: str, environ: Dict[str, str], log_excerpt: Optional[str]) -> FailureContext:
        return FailureContext(
            provider=self.name,
            repository=environ.get("CI_PROJECT_PATH"),
            repoUrl=environ.get("CI_PROJECT_URL"),
            branch=environ.get("CI_COMMIT_REF_NAME"),
            baseBranch=environ.get("CI_DEFAULT_BRANCH"),
            commitSha=environ.get("CI_COMMIT_SHA"),
            runId=environ.get("CI_PIPELINE_ID"),
            runUrl=environ.get("CI_PIPELINE_URL"),
            pipelineId=environ.get("CI_PIPELINE_ID"),
            pipelineUrl=environ.get("CI_PIPELINE_URL"),
            pipelineName=environ.get("CI_PIPELINE_SOURCE"),
            jobName=environ.get("CI_JOB_NAME"),
            logExcerpt=log_excerpt,
            environment=_safe_subset(environ),
        )


class JenkinsAdapter:
    name = "jenkins"

    def can_handle(self, environ: Dict[str, str]) -> bool:
        return "JENKINS_HOME" in environ or "JENKINS_URL" in environ

    def build_context(self, cwd: str, environ: Dict[str, str], log_excerpt: Optional[str]) -> FailureContext:
        return FailureContext(
            provider=self.name,
            repository=environ.get("JOB_NAME"),
            repoUrl=environ.get("GIT_URL"),
            branch=environ.get("GIT_BRANCH"),
            commitSha=environ.get("GIT_COMMIT"),
            runId=environ.get("BUILD_ID"),
            runUrl=environ.get("BUILD_URL"),
            pipelineId=environ.get("BUILD_ID"),
            pipelineUrl=environ.get("BUILD_URL"),
            pipelineName=environ.get("JOB_NAME"),
            jobName=environ.get("STAGE_NAME") or environ.get("JOB_NAME"),
            logExcerpt=log_excerpt,
            environment=_safe_subset(environ),
        )


class CircleCIAdapter:
    name = "circleci"

    def can_handle(self, environ: Dict[str, str]) -> bool:
        return environ.get("CIRCLECI") == "true"

    def build_context(self, cwd: str, environ: Dict[str, str], log_excerpt: Optional[str]) -> FailureContext:
        vcs_url = environ.get("CIRCLE_REPOSITORY_URL")
        project = environ.get("CIRCLE_PROJECT_USERNAME")
        repo = environ.get("CIRCLE_PROJECT_REPONAME")
        full_repo = f"{project}/{repo}" if project and repo else None
        return FailureContext(
            provider=self.name,
            repository=full_repo,
            repoUrl=vcs_url,
            branch=environ.get("CIRCLE_BRANCH"),
            commitSha=environ.get("CIRCLE_SHA1"),
            runId=environ.get("CIRCLE_WORKFLOW_ID"),
            runUrl=environ.get("CIRCLE_BUILD_URL"),
            pipelineId=environ.get("CIRCLE_WORKFLOW_ID"),
            pipelineUrl=environ.get("CIRCLE_BUILD_URL"),
            pipelineName=environ.get("CIRCLE_JOB"),
            jobName=environ.get("CIRCLE_JOB"),
            logExcerpt=log_excerpt,
            environment=_safe_subset(environ),
        )


class ManualAdapter:
    name = "manual"

    def can_handle(self, environ: Dict[str, str]) -> bool:
        return True

    def build_context(self, cwd: str, environ: Dict[str, str], log_excerpt: Optional[str]) -> FailureContext:
        return FailureContext(
            provider=self.name,
            branch=os.environ.get("AG_BRANCH"),
            commitSha=os.environ.get("AG_COMMIT_SHA"),
            logExcerpt=log_excerpt,
            environment=_safe_subset(environ),
        )


def _safe_subset(environ: Dict[str, str]) -> Dict[str, str]:
    allowed_prefixes = ("GITHUB_", "CI_", "CIRCLE_", "JENKINS_", "BUILD_", "GIT_")
    redaction_markers = ("TOKEN", "KEY", "SECRET", "PASSWORD")
    result: Dict[str, str] = {}
    for k, v in environ.items():
        if not k.startswith(allowed_prefixes):
            continue
        key_parts = k.split("_")
        if any(marker in key_parts or k.endswith(marker) for marker in redaction_markers):
            result[k] = "***REDACTED***"
        else:
            result[k] = v
    return result


def auto_detect_provider(environ: Dict[str, str]) -> CIProviderAdapter:
    adapters = [GitHubActionsAdapter(), GitLabCIAdapter(), JenkinsAdapter(), CircleCIAdapter(), ManualAdapter()]
    for adapter in adapters:
        if adapter.can_handle(environ):
            return adapter
    return ManualAdapter()


def register_builtin_provider_adapters() -> None:
    register_provider(GitHubActionsAdapter())
    register_provider(GitLabCIAdapter())
    register_provider(JenkinsAdapter())
    register_provider(CircleCIAdapter())
    register_provider(ManualAdapter())
