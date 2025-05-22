# GitHub User Removal Tool

A command-line tool to search for and remove users from your GitHub organizations and repositories.

## Features

- Search for users across all your organizations and repositories
- Find users in organization memberships, repository collaborators, and team memberships
- Securely store and manage multiple GitHub Personal Access Tokens (PATs)
- Set and use default PAT for convenience
- Remove users from organizations with confirmation
- Bulk remove users from all organizations
- Rich terminal output with colorful formatting and progress bars

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd git-rm-tool
```

2. Create and activate a virtual environment:
```bash
python3 -m venv myenv
source myenv/bin/activate
```

3. Install requirements:
```bash
pip install -r requirements.txt
```

4. Build the executable:
```bash
python build.py
```

5. Install system-wide (optional):
```bash
sudo cp dist/git-rm-user /usr/local/bin/
```

Or run it directly:
```bash
./dist/git-rm-user
```

## Usage

### Managing GitHub Tokens

1. Add a new GitHub token:
```bash
git-rm-user add-token <token-name> <github-pat> --default
```

2. List stored tokens:
```bash
git-rm-user show-tokens
```

### Searching and Removing Users

1. Search for a user:
```bash
git-rm-user search <username>
```

2. Search with debug information:
```bash
git-rm-user search <username> --debug
```

3. Remove user with confirmation:
```bash
git-rm-user search <username> --delete
```

4. Remove user without confirmation:
```bash
git-rm-user search <username> --deleteforcefull
```

## Required GitHub Token Permissions

Your GitHub Personal Access Token needs:
- `read:org`
- `write:org`
- `admin:org`
- `repo`

## Troubleshooting

1. Keyring issues:
```bash
sudo apt-get install python3-dbus python3-secretstorage libsecret-1-0 gnome-keyring
```

2. Command not found:
```bash
export PATH="$HOME/.local/bin:$PATH"
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 