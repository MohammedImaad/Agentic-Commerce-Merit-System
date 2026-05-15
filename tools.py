import subprocess
import json
import os

WALLET_PATH = os.path.expanduser("~/.agentcash/wallet.json")

def create_wallet_if_not_exists():
    """Create an AgentCash wallet if one does not already exist."""

    # wallet already exists
    if os.path.exists(WALLET_PATH):
        return {
            "success": True,
            "message": "Wallet already exists",
            "wallet_path": WALLET_PATH
        }

    # trigger AgentCash auto-wallet creation
    result = subprocess.run(
        [
            "npx",
            "-y",
            "agentcash@latest",
            "balance"
        ],
        capture_output=True,
        text=True
    )

    # verify wallet created
    if os.path.exists(WALLET_PATH):
        return {
            "success": True,
            "message": "Wallet created successfully",
            "wallet_path": WALLET_PATH,
            "response": json.loads(result.stdout)
        }

    return {
        "success": False,
        "error": result.stderr
    }



def check_balance():
    """Check the AgentCash wallet balance."""
    result = subprocess.run(
        [
            "npx",
            "-y",
            "agentcash@latest",
            "balance"
        ],
        capture_output=True,
        text=True
    )

    return json.loads(result.stdout)

def get_wallet_addresses():
    """Get all wallet addresses created by AgentCash."""
    result = subprocess.run(
        [
            "npx",
            "-y",
            "agentcash@latest",
            "accounts"
        ],
        capture_output=True,
        text=True
    )

    data = json.loads(result.stdout)

    return data["data"]["accounts"]


def search_tools(query: str):
    """Search the x402 ecosystem for tools/services."""
    result = subprocess.run(
        [
            "npx",
            "-y",
            "agentcash@latest",
            "search",
            query
        ],
        capture_output=True,
        text=True
    )

    data = json.loads(result.stdout)

    tools = data["data"]["results"]["results"]

    return tools[:5]

def execute_x402_tool(
    url: str,
    method: str = "GET",
    body: dict | None = None,
    base_url: str = ""
):
    """Execute a paid x402 API endpoint using AgentCash CLI."""

    print("\n===== EXECUTE X402 TOOL =====")
    print("URL:", url)
    print("METHOD:", method)
    print("BODY:", body)
    print("BASE URL:", base_url)

    # convert relative path into full URL
    if url.startswith("/") and base_url:
        url = base_url.rstrip("/") + url

    print("\n===== FINAL URL =====")
    print(url)

    command = [
        "npx",
        "-y",
        "agentcash@latest",
        "fetch",
        url,
        "--method",
        method
    ]

    if body:
        command.extend([
            "--body",
            json.dumps(body)
        ])

    print("\n===== FINAL COMMAND =====")
    print(command)

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    print("\n===== STDOUT =====")
    print(result.stdout)

    print("\n===== STDERR =====")
    print(result.stderr)

    try:
        parsed = json.loads(result.stdout)

        print("\n===== PARSED RESPONSE =====")
        print(parsed)

        return parsed

    except Exception as e:

        print("\n===== JSON PARSE FAILED =====")
        print(e)

        return {
            "success": False,
            "raw_output": result.stdout,
            "stderr": result.stderr
        }
'''
response = execute_x402_tool(
    url="https://api.printmoneylab.com/api/v1/kimchi-premium?symbol=BTC",
    method="GET"
)

print(response)
'''