# Ak spúšťaš pytest na serveri bez tkinter, tieto mocky zabránia pádu importu Kinak
import sys
from unittest.mock import MagicMock
try:
    import tkinter
except ImportError:
    sys.modules['tkinter'] = MagicMock()
    sys.modules['tkinter.font'] = MagicMock()
    sys.modules['tkinter.ttk'] = MagicMock()
    sys.modules['tkinter.messagebox'] = MagicMock()
    sys.modules['tkinter.colorchooser'] = MagicMock()
    sys.modules['tkinter.filedialog'] = MagicMock()
