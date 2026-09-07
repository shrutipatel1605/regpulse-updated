#!/usr/bin/env bash
set -euo pipefail

# Load environment variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/../.env"

if [[ -f "$ENV_FILE" ]]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

# Validate required env vars
: "${JIRA_BASE_URL:?JIRA_BASE_URL not set}"
: "${JIRA_EMAIL:?JIRA_EMAIL not set}"
: "${JIRA_API_TOKEN:?JIRA_API_TOKEN not set}"

API_URL="${JIRA_BASE_URL}/rest/api/3"
AUTH=$(echo -n "${JIRA_EMAIL}:${JIRA_API_TOKEN}" | base64)

# Helper function for API calls
jira_api() {
    local method="$1"
    local endpoint="$2"
    local data="${3:-}"

    if [[ -n "$data" ]]; then
        curl -s -X "$method" \
            -H "Authorization: Basic ${AUTH}" \
            -H "Content-Type: application/json" \
            -d "$data" \
            "${API_URL}${endpoint}"
    else
        curl -s -X "$method" \
            -H "Authorization: Basic ${AUTH}" \
            -H "Content-Type: application/json" \
            "${API_URL}${endpoint}"
    fi
}

# Get issue status
cmd_status() {
    local issue="$1"
    local response=$(jira_api GET "/issue/${issue}?fields=status,summary")

    local summary=$(echo "$response" | jq -r '.fields.summary // "Unknown"')
    local status=$(echo "$response" | jq -r '.fields.status.name // "Unknown"')

    echo "Issue: ${issue}"
    echo "Summary: ${summary}"
    echo "Status: ${status}"
}

# List available transitions
cmd_transitions() {
    local issue="$1"
    local response=$(jira_api GET "/issue/${issue}/transitions")

    echo "Available transitions for ${issue}:"
    echo "$response" | jq -r '.transitions[] | "  - \(.name) (id: \(.id))"'
}

# Move issue to a new status
cmd_move() {
    local issue="$1"
    local target_status="$2"

    # Get available transitions
    local transitions=$(jira_api GET "/issue/${issue}/transitions")

    # Find transition ID for target status (case-insensitive)
    local transition_id=$(echo "$transitions" | jq -r --arg status "$target_status" \
        '.transitions[] | select(.name | ascii_downcase == ($status | ascii_downcase)) | .id')

    if [[ -z "$transition_id" ]]; then
        echo "Error: No transition found for status '${target_status}'"
        echo "Available transitions:"
        echo "$transitions" | jq -r '.transitions[] | "  - \(.name)"'
        exit 1
    fi

    # Perform transition
    local data="{\"transition\": {\"id\": \"${transition_id}\"}}"
    jira_api POST "/issue/${issue}/transitions" "$data" > /dev/null

    echo "Moved ${issue} to '${target_status}'"
}

# Add comment to issue
cmd_comment() {
    local issue="$1"
    local comment="$2"

    local data=$(jq -n --arg body "$comment" '{body: {type: "doc", version: 1, content: [{type: "paragraph", content: [{type: "text", text: $body}]}]}}')

    jira_api POST "/issue/${issue}/comment" "$data" > /dev/null
    echo "Added comment to ${issue}"
}

# Update issue: move to status and add comment
cmd_update() {
    local issue="$1"
    local status="$2"
    local comment="${3:-}"

    cmd_move "$issue" "$status"

    if [[ -n "$comment" ]]; then
        cmd_comment "$issue" "$comment"
    fi
}

# Show usage
usage() {
    cat <<EOF
Usage: $(basename "$0") <command> [args]

Commands:
  status <ISSUE>                      Get issue status
  transitions <ISSUE>                 List available transitions
  move <ISSUE> <STATUS>               Move issue to status
  comment <ISSUE> <MESSAGE>           Add comment to issue
  update <ISSUE> <STATUS> [MESSAGE]   Move to status and optionally add comment

Examples:
  $(basename "$0") status RP-2
  $(basename "$0") move RP-2 "Done"
  $(basename "$0") comment RP-2 "Schema implemented"
  $(basename "$0") update RP-2 "In Progress" "Starting work"
EOF
}

# Main
case "${1:-}" in
    status)
        [[ $# -lt 2 ]] && { echo "Error: Issue required"; usage; exit 1; }
        cmd_status "$2"
        ;;
    transitions)
        [[ $# -lt 2 ]] && { echo "Error: Issue required"; usage; exit 1; }
        cmd_transitions "$2"
        ;;
    move)
        [[ $# -lt 3 ]] && { echo "Error: Issue and status required"; usage; exit 1; }
        cmd_move "$2" "$3"
        ;;
    comment)
        [[ $# -lt 3 ]] && { echo "Error: Issue and message required"; usage; exit 1; }
        cmd_comment "$2" "$3"
        ;;
    update)
        [[ $# -lt 3 ]] && { echo "Error: Issue and status required"; usage; exit 1; }
        cmd_update "$2" "$3" "${4:-}"
        ;;
    *)
        usage
        exit 1
        ;;
esac
