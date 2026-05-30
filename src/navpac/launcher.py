import pathlib
import sys

import streamlit.web.cli


def main():
    app = pathlib.Path(__file__).parent / "webapp" / "app.py"
    sys.argv = ["streamlit", "run", str(app)]
    sys.exit(streamlit.web.cli.main())
