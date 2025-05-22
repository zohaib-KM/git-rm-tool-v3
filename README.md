# GitHub User Removal Tool

A command-line tool to search for and remove users from your GitHub organizations and repositories.

## Features

- Search for users across all your organizations and repositories
- Find users in organization memberships, repository collaborators, and team memberships
- Securely store and manage multiple GitHub Personal Access Tokens (PATs)
- Set and use default PAT for convenience
- Remove users from organizations with confirmation
- Bulk remove users from all organizations
- Rich terminal output with colorful formatting
- Optimized performance with parallel processing
- Caching to reduce API calls

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd git-rm-tool
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Make the script executable:
```bash
chmod +x git_rm_user.py
```

## Usage

### Managing GitHub Tokens

1. Add a new GitHub token:
```bash
# Add a token
./git_rm_user.py add-token <token-name> <github-pat>

# Add a token and set as default
./git_rm_user.py add-token <token-name> <github-pat> --default
```

2. Set an existing token as default:
```bash
./git_rm_user.py set-default <token-name>
```

3. List stored tokens:
```bash
./git_rm_user.py show-tokens
```

### Searching and Removing Users

1. Search for a user (uses default token if set):
```bash
# Using default token
./git_rm_user.py search <username>

# Using specific token
./git_rm_user.py search <username> --token-name <your-token-name>

# With debug information
./git_rm_user.py search <username> --debug
```

2. Search and remove with confirmation:
```bash
./git_rm_user.py search <username> --delete
```

3. Remove user from all organizations without confirmation:
```bash
./git_rm_user.py search <username> --deleteforcefull
```

## Required GitHub Token Permissions

Your GitHub Personal Access Token needs the following permissions:
- `read:org`
- `write:org`
- `admin:org`
- `repo` (for repository access)

## Security

- GitHub tokens are stored securely using the system's keyring
- No sensitive information is stored in plain text
- Each operation that removes a user requires explicit confirmation unless using `--deleteforcefull`
- Default token selection for convenience without compromising security

## Performance Optimizations

The tool includes several optimizations for better performance:
- Parallel processing of organizations and repositories
- Caching of organization member IDs
- User ID-based comparisons instead of username matching
- Efficient API call management
- Early termination when user is found

## Error Handling

The tool includes comprehensive error handling for:
- Invalid tokens
- Network issues
- Permission problems
- Non-existent users
- Organization access issues
- Repository access problems

## Contributing

Feel free to open issues or submit pull requests for any improvements or bug fixes. 