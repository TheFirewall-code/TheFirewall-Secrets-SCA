import subprocess
import json
from app.core.logger import logger
import time
import os
import uuid


def runScan(target_dir, repo_name):
    # Run Gitleaks scan
    logger.info(f"Running gitleaks for %s", target_dir)
    leaks_file_path = f"leaks_{uuid.uuid4()}.json"
    command = [
        "gitleaks",
        "--source",
        target_dir,
        "detect",
        "-f",
        "json",
        "-r",
        leaks_file_path]
    try:
        print(command)
        response = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        out, err = response.communicate()
        out_str = out.decode().strip()
        err_str = err.decode().strip()

        
        logger.info(
            f"Ran scanning command, file created {leaks_file_path} "
            f"{os.path.exists(leaks_file_path)}"
        )


        if err_str:
            print("Error:", out_str, err_str, command)
            logger.error("Error output from gitleaks: %s", err_str)

        # Check if the leaks file exists before trying to open it
        if not os.path.exists(leaks_file_path):
            logger.error(
                f"{leaks_file_path} file not found for repository {repo_name}.")
            return {
                "error": f"{leaks_file_path} file not found for repository {repo_name}."}
        else:
            logger.info(
                f"{leaks_file_path} file found for repository {repo_name}.")
            try:
                with open(leaks_file_path, 'r') as file:
                    data = json.load(file)
                    print('Sending data', data)
                    # logger.info(f"Got data from {leaks_file_path}")
                    # logger.info(f"Got data from {leaks_file_path}: {data}")
                    return data
            except Exception as e:
                logger.error("Error while opening leak.json", e)
                return []

    except Exception as e:
        logger.error(
            "An error occurred while running the scan: %s %s %s",
            command,
            target_dir,
            e,
            exc_info=True)
        return {"error": "An error occurred: " + e}
