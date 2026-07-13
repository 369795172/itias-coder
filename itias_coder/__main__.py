"""Entry point: python -m itias_coder"""

import sys


def main() -> None:
    if len(sys.argv) >= 2 and sys.argv[1] == "--reliability":
        if len(sys.argv) < 4:
            print(
                "Usage: python -m itias_coder --reliability <file1.xlsx> <file2.xlsx> [out.xlsx]",
                file=sys.stderr,
            )
            sys.exit(1)
        from itias_coder.reliability import main_cli

        file1, file2 = sys.argv[2], sys.argv[3]
        out_path = sys.argv[4] if len(sys.argv) > 4 else ""
        try:
            main_cli(file1, file2, out_path)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        print(f"Reliability report saved.")
        return

    from itias_coder.main import run

    run()


if __name__ == "__main__":
    main()
