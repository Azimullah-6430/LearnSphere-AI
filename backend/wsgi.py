import sys
from pathlib import Path

# Ensure backend directory is in python path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from server import app

if __name__ == "__main__":
    app.run()

