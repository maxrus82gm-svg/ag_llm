import tkinter as tk

from b2_contract_test import assert_contract

class UltraApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        assert_contract()
