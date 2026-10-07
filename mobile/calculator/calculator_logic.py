"""
Calculator logic — evaluates expressions and detects the secret sequence.

Secret sequence: 7 → 3 → 9 → 1 → =
If matched, calls the app's switch_to_private() method.
"""
from typing import Optional


# The secret key sequence to unlock private mode
SECRET_SEQUENCE = ["7", "3", "9", "1", "="]


class CalculatorLogic:
    """
    Handles calculator state and secret sequence detection.

    The secret sequence detection works by tracking the last N
    button presses that match the expected sequence. If no exact
    error message is shown when a wrong combo is entered — the
    calculator just operates normally (security by silence).
    """

    def __init__(self, on_secret_detected=None):
        self._display = "0"
        self._first_operand: Optional[float] = None
        self._operator: Optional[str] = None
        self._waiting_for_second = False
        self._new_number = True
        self._on_secret_detected = on_secret_detected

        # Secret sequence tracking
        self._secret_buffer: list[str] = []

    @property
    def display(self) -> str:
        return self._display

    def _update_secret_buffer(self, key: str) -> None:
        """
        Track button presses for secret sequence.
        Appends key to rolling buffer sized to SECRET_SEQUENCE length.
        """
        seq_len = len(SECRET_SEQUENCE)
        self._secret_buffer.append(key)
        # Keep only the last N entries
        if len(self._secret_buffer) > seq_len:
            self._secret_buffer = self._secret_buffer[-seq_len:]

        # Check if buffer matches secret
        if self._secret_buffer == SECRET_SEQUENCE:
            self._secret_buffer = []  # Reset
            if self._on_secret_detected:
                self._on_secret_detected()

    def press(self, key: str) -> str:
        """
        Handle a button press.
        Returns the updated display string.
        """
        self._update_secret_buffer(key)

        if key.isdigit() or key == ".":
            self._handle_number(key)
        elif key in ("+", "−", "×", "÷"):
            self._handle_operator(key)
        elif key == "=":
            self._handle_equals()
        elif key == "C":
            self._handle_clear()
        elif key == "±":
            self._handle_sign()
        elif key == "%":
            self._handle_percent()
        elif key == "⌫":
            self._handle_backspace()

        return self._display

    def _handle_number(self, key: str) -> None:
        if self._new_number:
            if key == ".":
                self._display = "0."
            else:
                self._display = key
            self._new_number = False
        else:
            if key == "." and "." in self._display:
                return  # Ignore duplicate decimal
            if len(self._display.lstrip("-")) < 12:  # Max digits
                self._display += key

    def _handle_operator(self, key: str) -> None:
        op_map = {"−": "-", "×": "*", "÷": "/"}
        op = op_map.get(key, key)

        if self._first_operand is not None and not self._new_number:
            # Chain calculation
            self._calculate()

        try:
            self._first_operand = float(self._display)
        except ValueError:
            pass

        self._operator = op
        self._new_number = True

    def _handle_equals(self) -> None:
        if self._operator and self._first_operand is not None:
            self._calculate()
            self._operator = None
            self._first_operand = None
            self._new_number = True

    def _calculate(self) -> None:
        try:
            second = float(self._display)
            first = self._first_operand
            op = self._operator

            if op == "+":
                result = first + second
            elif op == "-":
                result = first - second
            elif op == "*":
                result = first * second
            elif op == "/":
                if second == 0:
                    self._display = "Error"
                    self._reset_state()
                    return
                result = first / second
            else:
                return

            # Format result
            if result == int(result) and abs(result) < 1e12:
                self._display = str(int(result))
            else:
                self._display = f"{result:.10g}"

        except Exception:
            self._display = "Error"
            self._reset_state()

    def _handle_clear(self) -> None:
        self._display = "0"
        self._reset_state()

    def _handle_sign(self) -> None:
        try:
            val = float(self._display)
            val = -val
            if val == int(val):
                self._display = str(int(val))
            else:
                self._display = str(val)
        except ValueError:
            pass

    def _handle_percent(self) -> None:
        try:
            val = float(self._display)
            self._display = f"{val / 100:.10g}"
            self._new_number = True
        except ValueError:
            pass

    def _handle_backspace(self) -> None:
        if self._display not in ("0", "Error"):
            self._display = self._display[:-1] or "0"

    def _reset_state(self) -> None:
        self._first_operand = None
        self._operator = None
        self._new_number = True
        self._waiting_for_second = False
