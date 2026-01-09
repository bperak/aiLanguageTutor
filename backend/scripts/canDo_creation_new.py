# Facade for backward compatibility
# This file re-exports everything from the cando_creation package
# to maintain backward compatibility with existing imports

import sys
from pathlib import Path

# Ensure the scripts directory is in the path for dynamic imports
_scripts_dir = Path(__file__).parent
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

from cando_creation import *  # noqa: F401, F403

# Re-export everything for backward compatibility
__all__ = [
    # All models, prompts, generators, and assembler are re-exported via the package
]
