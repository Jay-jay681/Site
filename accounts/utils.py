WEAK_PINS = {"121212", "112233", "123123", "111222", "696969", "007007"}


def is_weak_pin(pin):
    if len(set(pin)) == 1:
        return True

    digits = [int(d) for d in pin]
    steps = {b - a for a, b in zip(digits, digits[1:])}
    if steps in ({1}, {-1}):
        return True

    return pin in WEAK_PINS