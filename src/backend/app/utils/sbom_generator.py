import subprocess
import json
import os

async def generate_sbom(repo_path: str) -> dict:
    try:
        # Convert to absolute path
        absolute_repo_path = os.path.abspath(repo_path)

        # Syft command to generate SBOM
        command = ["syft", absolute_repo_path, "-o", "json"]
        result = subprocess.run(command, capture_output=True, text=True)

        if result.returncode != 0:
            raise Exception(f"Error generating SBOM: {result.stderr.strip()}")

        # Parse the SBOM JSON output
        sbom_json = json.loads(result.stdout)
        return sbom_json

    except Exception as e:
        raise Exception(f"SBOM generation failed: {str(e)}")
