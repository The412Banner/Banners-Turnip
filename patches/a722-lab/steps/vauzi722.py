"""Comparison only: the current 710-720-Test A722 block (patches/a710-720.py, Vauzi-17/710 regs)."""
import os
import runpy
runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "a710-720.py"), run_name="__main__")
