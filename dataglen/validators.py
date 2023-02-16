
def min(min, value):
    if min <= value:
        return True
    else:
        return False

def max(max, value):
    if value <= max:
        return True
    else:
        return False

def range(min, max, value):
    if min <= value <= max:
        return True
    else:
        return False

def non_zero(value):
    if value == 0:
        return False
    else:
        return True
