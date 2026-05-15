import subprocess
import os

def initialize_agentcash_wallet():
    """
    Triggers AgentCash wallet auto-creation.
    Wallet gets stored in:
    ~/.agentcash/wallet.json
    """

    result = subprocess.run(
        ["npx","-y", "agentcash@latest", "balance"],
        capture_output=True,
        text=True
    )

    print(result.stdout)
    print(result.stderr)


initialize_agentcash_wallet()