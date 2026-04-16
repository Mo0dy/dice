from dice import dice_interpreter


def build_result():
    session = dice_interpreter()

    def add_two(value):
        return value + 2

    session.register_function(add_two)
    return session("add_two([1..3])")
