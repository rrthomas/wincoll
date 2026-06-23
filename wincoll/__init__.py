# © Reuben Thomas <rrt@sc3d.org> 2024
# Released under the GPL version 3, or (at your option) any later version.

import asyncio
import re
import sys

from .wincoll_game import WincollGame


def main(argv: list[str] = sys.argv[1:]) -> None:
    asyncio.run(WincollGame().main(argv))


if __name__ == "__main__":
    sys.argv[0] = re.sub(r"__init__.py$", "wincoll", sys.argv[0])
    main()
