import helpers
import subprocess
import sys

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: mirror.py source dest1 [dest2 [... destN]]")
        exit(1)

    # Maintain unique list
    repositories = []
    for reference in sys.argv[1:]:
        for x in reference.split(","):
            # Identified this is an AWS target location
            if "dkr.ecr" in x:
                # Removing off the repository and tag info
                repository = x[:x.index("/")]
                # Check against unique hostname list
                if repository not in repositories:
                    # Login in uniquely
                    repositories.append(repository)
                    rc = helpers.ecr_login(repository)
                    if rc > 0:
                        exit(rc)

    for dest in sys.argv[2:]:
        for x in dest.split(","):
            # Run skopeo copy for each destination listed.
            copy_result = subprocess.run(
                ["skopeo", "copy", "--all", "docker://" + sys.argv[1], "docker://" + x],
                stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL
            )
            if copy_result.returncode > 0:
                exit(copy_result.returncode)

    exit(0)
