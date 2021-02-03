# Used to determine the range of numbers for which it is more optimal to INC/DEC instead of generating a const
# separately, i.e. for x := x + 2 it's cheaper to LOAD x and INC it twice instead of resetting another register,
# generating 2, and using the ADD operation but const generation uses bit shifts so it's cheaper for larger numbers.

for i in range(50):
    b = bin(i)[2:]
    instr = 6  # RESET and ADD costs
    for l in b:
        if l == "1":
            instr += 2  # SHL and INC
        else:
            instr += 1  # just SHL
    print(b, i, instr, i < instr, sep="\t")
