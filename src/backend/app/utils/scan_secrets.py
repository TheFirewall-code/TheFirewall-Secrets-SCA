import subprocess
import json
import os


def scan_secrets(file_list):
    secrets = []
    for file_path in file_list:
        try:
            command = f"trufflehog filesystem {file_path} --json"
            print(command)
            result = subprocess.run(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True)
            output, error = result.stdout, result.stderr

            if error:
                print(f"Error in trufflehog command: {error}")

            if output:
                for line in output.strip().split('\n'):
                    if line:
                        try:
                            sec = json.loads(line)
                            secrets.append(sec)
                        except json.JSONDecodeError:
                            print(f"Error parsing JSON: {line}")

        except Exception as e:
            print(f"Failed to run trufflehog: {e}")

        finally:
            try:
                os.remove(file_path)
                print(f"Deleted file: {file_path}")
            except OSError as e:
                print(f"Error deleting file {file_path}: {e}")

    return secrets
