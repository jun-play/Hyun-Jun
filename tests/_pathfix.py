"""테스트가 패키지를 설치하지 않고도 src/ylearn 을 import할 수 있게 해준다."""

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
