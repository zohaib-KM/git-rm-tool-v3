#!/usr/bin/env python3

import click
import keyring
from github import Github
from rich.console import Console
from rich.table import Table
from rich import print as rprint
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
)
import sys
from typing import Optional, Dict, Set, List
from dataclasses import dataclass
from github.Repository import Repository
from github.Organization import Organization
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache

console = Console()
DEFAULT_TOKEN_KEY = "git-rm-tool-default"

# Create a custom progress bar for the tool
def create_progress() -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console
    )

@dataclass
class UserLocation:
    org_name: str
    repo_name: Optional[str] = None
    access_type: str = "organization member"

def store_token(token_name: str, token: str, make_default: bool = False):
    """Store GitHub PAT in system keyring."""
    try:
        keyring.set_password("git-rm-tool", token_name, token)
        add_token_to_list(token_name)
        if make_default:
            set_default_token(token_name)
        rprint(f"[green]✓[/green] Token '{token_name}' stored successfully!")
        if make_default:
            rprint(f"[green]✓[/green] Set as default token!")
    except Exception as e:
        rprint(f"[red]✗[/red] Failed to store token: {str(e)}")

def get_tokens() -> list[str]:
    """Get all stored token names."""
    try:
        tokens_str = keyring.get_password("git-rm-tool", "token_list") or ""
        return tokens_str.split(",") if tokens_str else []
    except Exception:
        return []

def add_token_to_list(token_name: str):
    """Add token name to the list of stored tokens."""
    tokens = get_tokens()
    if token_name not in tokens:
        tokens.append(token_name)
        keyring.set_password("git-rm-tool", "token_list", ",".join(tokens))

def get_token(token_name: str) -> Optional[str]:
    """Retrieve GitHub PAT from system keyring."""
    return keyring.get_password("git-rm-tool", token_name)

def set_default_token(token_name: str):
    """Set a token as the default token."""
    keyring.set_password("git-rm-tool", DEFAULT_TOKEN_KEY, token_name)

def get_default_token_name() -> Optional[str]:
    """Get the name of the default token."""
    return keyring.get_password("git-rm-tool", DEFAULT_TOKEN_KEY)

def list_tokens():
    """Display all stored tokens."""
    tokens = get_tokens()
    if not tokens:
        rprint("[yellow]No tokens stored.[/yellow]")
        return

    default_token = get_default_token_name()
    table = Table(title="Stored GitHub Tokens")
    table.add_column("Token Name", style="cyan")
    table.add_column("Default", style="green")
    
    for token in tokens:
        table.add_row(token, "✓" if token == default_token else "")
    
    console.print(table)

@lru_cache(maxsize=128)
def get_cached_member_ids(org_name: str, g: Github) -> Set[int]:
    """Cache organization member IDs to reduce API calls."""
    try:
        org = g.get_organization(org_name)
        return {member.id for member in org.get_members()}
    except:
        return set()

def check_repo_access(repo: Repository, username: str, user_id: int, debug: bool) -> Optional[str]:
    """Check if user has access to repository through collaborators or teams."""
    try:
        # Check direct collaborators (using user_id for faster comparison)
        collaborators = list(repo.get_collaborators())
        if any(c.id == user_id for c in collaborators):
            return "repository collaborator"

        # Check team members
        teams = list(repo.get_teams())
        for team in teams:
            try:
                if team.has_in_members(team.organization.get_member(username)):
                    return f"team member ({team.name})"
            except Exception as e:
                if debug:
                    rprint(f"[yellow]Warning: Could not check team {team.name}: {str(e)}[/yellow]")

    except Exception as e:
        if debug:
            rprint(f"[yellow]Warning: Could not check repository {repo.name}: {str(e)}[/yellow]")
    
    return None

def check_org_access(org: Organization, username: str, user_id: int, g: Github, debug: bool, repo_progress=None) -> List[UserLocation]:
    """Check user access in a single organization."""
    results = []
    try:
        # Check organization membership using cached member IDs
        member_ids = get_cached_member_ids(org.login, g)
        if user_id in member_ids:
            results.append(UserLocation(org_name=org.login))

        # Check repositories in parallel
        repos = list(org.get_repos())
        total_repos = len(repos)
        
        if repo_progress:
            repo_task = repo_progress.add_task(f"[cyan]Scanning {org.login} repositories...", total=total_repos)

        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_repo = {
                executor.submit(check_repo_access, repo, username, user_id, debug): repo
                for repo in repos
            }
            
            completed = 0
            for future in as_completed(future_to_repo):
                completed += 1
                if repo_progress:
                    repo_progress.update(repo_task, completed=completed)
                
                repo = future_to_repo[future]
                access_type = future.result()
                if access_type:
                    results.append(UserLocation(
                        org_name=org.login,
                        repo_name=repo.name,
                        access_type=access_type
                    ))

        if repo_progress:
            repo_progress.remove_task(repo_task)

    except Exception as e:
        if debug:
            rprint(f"[yellow]Warning: Could not check organization {org.login}: {str(e)}[/yellow]")
    
    return results

def find_user_in_orgs(g: Github, username: str, debug: bool) -> list[UserLocation]:
    """Find user in all accessible organizations and their repositories."""
    results = []
    
    with create_progress() as progress:
        try:
            # First, verify the token works by getting the authenticated user
            auth_task = progress.add_task("[yellow]Authenticating...", total=1)
            auth_user = g.get_user()
            progress.update(auth_task, completed=1)
            rprint(f"[green]✓[/green] Authenticated as: {auth_user.login}")
            
            # Get user ID once for faster comparisons
            user_task = progress.add_task("[yellow]Verifying target user...", total=1)
            try:
                user = g.get_user(username)
                user_id = user.id
                progress.update(user_task, completed=1)
            except:
                progress.update(user_task, completed=1)
                rprint(f"[red]Error: Could not find user '{username}'[/red]")
                return results

            # Get all organizations the authenticated user is part of
            org_list_task = progress.add_task("[yellow]Fetching organizations...", total=1)
            orgs = list(auth_user.get_orgs())
            progress.update(org_list_task, completed=1)
            
            if not orgs:
                rprint("[yellow]Warning: No organizations found for your account.[/yellow]")
                return results
                
            rprint(f"[green]✓[/green] Found {len(orgs)} organizations")
            
            # Check organizations in parallel
            org_task = progress.add_task("[cyan]Scanning organizations...", total=len(orgs))
            
            with ThreadPoolExecutor(max_workers=3) as executor:
                future_to_org = {
                    executor.submit(
                        check_org_access, 
                        org, 
                        username, 
                        user_id, 
                        g, 
                        debug,
                        progress
                    ): org for org in orgs
                }
                
                completed_orgs = 0
                for future in as_completed(future_to_org):
                    completed_orgs += 1
                    progress.update(org_task, completed=completed_orgs)
                    
                    org_results = future.result()
                    results.extend(org_results)
                    
            if not results:
                rprint(f"[yellow]Checked all organizations and repositories. User '{username}' not found.[/yellow]")
                
        except Exception as e:
            rprint(f"[red]Error accessing organizations: {str(e)}[/red]")
            if "Bad credentials" in str(e):
                rprint("[red]The provided token appears to be invalid or expired.[/red]")
            elif "Not Found" in str(e):
                rprint("[red]The token might not have sufficient permissions to list organizations.[/red]")
    
    return results

def remove_user_from_org(org: Organization, username: str, location: UserLocation) -> bool:
    """Remove user from organization or repository."""
    try:
        if location.repo_name:
            repo = org.get_repo(location.repo_name)
            if "team member" in location.access_type:
                # Remove from all teams in the repository
                for team in repo.get_teams():
                    try:
                        if team.has_in_members(org.get_member(username)):
                            team.remove_membership(org.get_member(username))
                    except:
                        pass
            else:
                # Remove as collaborator
                repo.remove_from_collaborators(username)
        else:
            # Remove from organization
            org.remove_from_members(username)
        return True
    except Exception as e:
        rprint(f"[red]✗[/red] Failed to remove {username}: {str(e)}")
        return False

@click.group()
def cli():
    """GitHub User Removal Tool - Manage organization members across multiple repositories."""
    pass

@cli.command()
@click.argument('token_name')
@click.argument('token')
@click.option('--default', is_flag=True, help='Set this token as the default')
def add_token(token_name: str, token: str, default: bool):
    """Store a new GitHub PAT with a given name."""
    store_token(token_name, token, default)

@cli.command()
@click.argument('token_name')
def set_default(token_name: str):
    """Set a stored token as the default token."""
    if token_name in get_tokens():
        set_default_token(token_name)
        rprint(f"[green]✓[/green] Set '{token_name}' as default token!")
    else:
        rprint(f"[red]Token '{token_name}' not found![/red]")

@cli.command()
def show_tokens():
    """List all stored GitHub PATs."""
    list_tokens()

@cli.command()
@click.argument('username')
@click.option('--token-name', help='Name of the stored token to use (uses default if not specified)')
@click.option('--delete', is_flag=True, help='Delete user from organizations (with confirmation)')
@click.option('--deleteforcefull', is_flag=True, help='Delete user from all organizations without confirmation')
@click.option('--debug', is_flag=True, help='Show debug information')
def search(username: str, token_name: str, delete: bool, deleteforcefull: bool, debug: bool):
    """Search for a user across all your organizations and optionally remove them."""
    if not token_name:
        token_name = get_default_token_name()
        if not token_name:
            rprint("[red]No default token set. Please specify --token-name or set a default token.[/red]")
            sys.exit(1)
        if debug:
            rprint(f"[cyan]Using default token: {token_name}[/cyan]")

    token = get_token(token_name)
    if not token:
        rprint(f"[red]Token '{token_name}' not found![/red]")
        sys.exit(1)

    if debug:
        rprint(f"[cyan]Debug: Using token name: {token_name}[/cyan]")
        rprint(f"[cyan]Debug: Searching for user: {username}[/cyan]")

    g = Github(token)
    locations = find_user_in_orgs(g, username, debug)

    if not locations:
        return

    table = Table(title=f"Locations where user '{username}' was found")
    table.add_column("Organization", style="cyan")
    table.add_column("Repository", style="green")
    table.add_column("Access Type", style="yellow")
    
    for loc in locations:
        table.add_row(
            loc.org_name,
            loc.repo_name or "-",
            loc.access_type
        )
    console.print(table)

    if delete or deleteforcefull:
        with create_progress() as progress:
            removal_task = progress.add_task("[red]Removing user access...", total=len(locations))
            
            for loc in locations:
                org = g.get_organization(loc.org_name)
                if deleteforcefull:
                    if remove_user_from_org(org, username, loc):
                        rprint(f"[green]✓[/green] Removed {username} from {loc.org_name}" + 
                              (f" repository {loc.repo_name}" if loc.repo_name else ""))
                else:
                    prompt = f"Remove {username} from {loc.org_name}"
                    if loc.repo_name:
                        prompt += f" repository {loc.repo_name}"
                    prompt += "?"
                    
                    if click.confirm(prompt):
                        if remove_user_from_org(org, username, loc):
                            rprint(f"[green]✓[/green] Removed {username} from {loc.org_name}" + 
                                  (f" repository {loc.repo_name}" if loc.repo_name else ""))
                
                progress.update(removal_task, advance=1)

if __name__ == '__main__':
    cli() 