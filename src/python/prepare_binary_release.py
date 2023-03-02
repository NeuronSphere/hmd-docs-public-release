import csv
import datetime
import os
from pathlib import Path
import shutil
from tempfile import gettempdir

from cement.utils import shell
from hmd_cli_tools import cd


BINARY_RELEASE_CSV = Path(__file__).parent / ".." / "data" / "open_binaries.csv"
HMD_REPO_HOME = os.environ.get("HMD_REPO_HOME")
LICENSE_PATH = Path(__file__).parent / "LICENSE.txt"


def main():
    with open(BINARY_RELEASE_CSV) as br:
        binary_releases = list(csv.DictReader(br))

    assert HMD_REPO_HOME is not None, "Must set HMD_REPO_HOME"

    for repo in binary_releases:
        print(f"Preparing {repo['Repository']}")
        repo_path = Path(HMD_REPO_HOME) / repo["Repository"]
        try:
            with cd(repo_path):
                if os.path.exists(os.path.join(gettempdir(), repo["Repository"])):
                    shutil.rmtree(os.path.join(gettempdir(), repo["Repository"]))

                if not os.path.exists(repo_path / "LICENSE.txt"):
                    print("Writing LICENSE file")
                    shutil.copy(LICENSE_PATH, repo_path / "LICENSE.txt")
                    repo["License"] = datetime.datetime.now().strftime("%Y-%b-%d")

                if os.path.exists(repo_path / "src" / "python" / "setup.py"):
                    with open(repo_path / "src" / "python" / "setup.py") as spy:
                        setup = spy.read()

                    setup = setup.replace(
                        'license="unlicensed"', 'license="Apache 2.0"'
                    )

                    with open(repo_path / "src" / "python" / "setup.py", "w") as spy:
                        spy.write(setup)

                if os.path.exists(repo_path / "src" / "python"):
                    print("Running Snyk scan")
                    pco_cmd = ["hmd", "python", "build", "-pco"]

                    shell.exec_cmd2(pco_cmd)
                    snyk_cmd = ["snyk", "test", "--file=./src/python/requirements.txt"]

                    snyk = shell.exec_cmd2(snyk_cmd)

                    if snyk == 0:
                        repo["Snyk"] = datetime.datetime.now().strftime("%Y-%b-%d")
        except Exception as e:
            print(e)
            pass

    with open(BINARY_RELEASE_CSV, "w") as br:
        writer = csv.DictWriter(br, binary_releases[0].keys())
        writer.writeheader()
        writer.writerows(binary_releases)


if __name__ == "__main__":
    main()
