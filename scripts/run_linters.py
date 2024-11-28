#!/usr/bin/env python
import subprocess  # nosec B404
import sys
from typing import List, Tuple


def run_command(command: List[str]) -> Tuple[int, str]:
    """Run a command and return its exit code and output."""
    if isinstance(command, str):
        command = command.split()

    try:
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            shell=False,
            check=False,
        )
        return process.returncode, process.stdout + process.stderr
    except subprocess.SubprocessError as e:
        return 1, str(e)


def main():
    """Run all linters and return non-zero exit code if any fail."""
    commands = [
        ["black", "--check", "."],
        ["isort", "--check-only", "."],
        ["flake8", "."],
        ["bandit", "-r", ".", "-c", "bandit.yaml"],
    ]

    failed = False
    for command in commands:
        print(f"\nRunning {' '.join(command)}...")
        exit_code, output = run_command(command)
        if exit_code != 0:
            failed = True
            print(f"Failed with exit code {exit_code}")
            print(output)
        else:
            print("Passed!")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
