# Used to debug the logic behind division in generated asm code.

def divide(x, y):
    quotient = 0
    remainder = 0
    divisor = y
    divident = x
    temp = 0
    
    if divisor == 0:
        return quotient, remainder

    remainder = divident
    divident = divisor
    temp = remainder - divident
    if not temp <= 0:
        while True:
            temp = divident - remainder
            if not temp <= 0:
                break
            divident = shl(divident)
        divident = shr(divident)

    while True:
        temp = divident - remainder
        if not temp <= 0:
            break
        remainder -= divident
        quotient += 1
        while True:
            temp = divident - remainder
            if temp <= 0:
                break
            divident = shr(divident)
            temp = divisor - divident
            if not temp <= 0:
                return quotient, remainder
            quotient = shl(quotient)
            
    return quotient, remainder

def shl(x):
    return 2*x

def shr(x):
    return x//2

assert divide(1, 2) == (0, 1)
assert divide(12, 1) == (12, 0)
assert divide(4, 2) == (2, 0)