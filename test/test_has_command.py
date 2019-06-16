import re
from io import StringIO

import pytest
import sh


def test_generated_command_exists():
    out = StringIO()

    with pytest.raises(sh.ErrorReturnCode):
        sh.tor_apprentice(_out=out, _err=out, _env={'DEBUG_MODE': 'True', 'NOOP_MODE': 'True'})

    lines = out.getvalue().strip().splitlines()
    pattern = re.compile('bugsnag.* No API Key', re.IGNORECASE)
    assert any(pattern.search(line) for line in lines)
