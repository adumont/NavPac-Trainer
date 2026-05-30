import pathlib
import sys

import streamlit.web.cli


def main():
    app = pathlib.Path(__file__).with_name("app.py")
    sys.argv = ["streamlit", "run", str(app)]
    sys.exit(streamlit.web.cli.main())
