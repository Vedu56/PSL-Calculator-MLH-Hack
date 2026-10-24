"""Launcher: `streamlit run app.py` opens the full PSL Calculator site.

The site itself (home page, PSL Score page, PSL PvP page) lives in score_face.py.
runpy runs it fresh on every Streamlit rerun; a plain `import score_face` would only
run it once and leave the page blank after the first click.
"""
import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).with_name("score_face.py")), run_name="__main__")
