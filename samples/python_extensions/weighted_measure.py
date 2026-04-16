from dice import dice_interpreter
from diceengine import FiniteMeasure


def build_result():
    session = dice_interpreter()

    def weather():
        return FiniteMeasure((("sun", 2), ("rain", 1)))

    session.register_function(weather)
    return session("d weather()")
