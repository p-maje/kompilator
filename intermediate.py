from symbol_table import Variable


class CodeBlock:
    def __init__(self, start_index, commands):
        self.start_index = start_index
        self.commands = commands
        self.code = []


class IntermediateCodeGenerator:
    def __init__(self, commands, symbols):
        self.commands = commands
        self.symbols = symbols
        self.code = []
        self.blocks = []
        self.active_iters = set()

    def generate_intermediate_code(self):
        self.code = self.generate_code(self.commands)
        self.code.append(("halt",))
        return self.code

    def generate_code(self, commands):
        code = []
        for command in commands:
            if command[0] == "write":
                value = self.unpack_value(command[1])
                code.append(("write", value))

            elif command[0] == "read":
                target = self.unpack_value(command[1], update=True)
                code.append(("read", target))
                if type(command[1]) != tuple:
                    self.symbols[command[1]].initialized = True

            elif command[0] == "assign":
                if command[2][0] not in ['load', 'const']:
                    expr = (command[2][0], self.unpack_value(command[2][1]), self.unpack_value(command[2][2]))
                    expr, to_copy = self.unpack_expr(expr)
                    if to_copy:
                        code.append(("copy", self.unpack_value(command[1], update=True), expr))
                    else:
                        code.append(("assign", self.unpack_value(command[1], update=True), *expr))
                else:
                    code.append(("copy", self.unpack_value(command[1], update=True), self.unpack_value(command[2])))
                if type(command[1]) != tuple:
                    self.symbols[command[1]].initialized = True

            elif command[0] == "if":
                condition = self.unpack_cond(command[1])
                if type(condition) == bool:
                    if condition:
                        continue
                    else:
                        code.extend(self.generate_code(command[2]))
                else:
                    start = len(code)
                    code.extend(self.generate_code(command[2]))
                    condition = (*condition, len(code) - start + 1)
                    code[start:] = [condition] + code[start:]

            elif command[0] == "ifelse":
                condition = self.unpack_cond(command[1])
                if type(condition) == bool:
                    if condition:
                        code.extend(self.generate_code(command[3]))
                    else:
                        code.extend(self.generate_code(command[2]))
                else:
                    start = len(code)
                    code.extend(self.generate_code(command[2]))
                    condition = (*condition, len(code) - start + 2)
                    code[start:] = [condition] + code[start:]
                    mid = len(code)
                    code.extend(self.generate_code(command[3]))
                    code[mid:] = [("j", len(code) - mid + 1)] + code[mid:]

            elif command[0] == "while":
                condition = self.unpack_cond(command[1])
                if type(condition) == bool:
                    if condition:
                        continue
                    else:
                        start = len(code)
                        code.extend(self.generate_code(command[2]))
                        code.append(("j", start - len(code)))
                else:
                    start = len(code)
                    code.extend(self.generate_code(command[2]))
                    condition = (*condition, len(code) - start + 2)
                    code[start:] = [condition] + code[start:]
                    code.append(("j", start - len(code)))

            elif command[0] == "until":
                start = len(code)
                code.extend(self.generate_code(command[2]))
                condition = self.unpack_cond(command[1])
                if type(condition) == bool:
                    if condition:
                        continue
                    else:
                        code.append(("j", start - len(code)))
                else:
                    condition = (*condition, start - len(code))
                    code.append(condition)

            elif command[0] == "forup":
                iterator = command[1]

                code.append(("copy", iterator, self.unpack_value(command[2])))
                code.append(("copy", iterator+"*", self.unpack_value(command[3])))
                self.active_iters.add(iterator)
                self.symbols.add_iterator(iterator)

                start = len(code)
                code.extend(self.generate_code(command[4]))
                code.append(("inc", iterator))
                code.append(("j", start - len(code) - 1))
                code[start:] = [("j_gt", iterator, iterator+"*", len(code) - start + 1)] + code[start:]
                self.active_iters.remove(iterator)

            elif command[0] == "fordown":
                iterator = command[1]

                code.append(("copy", iterator, self.unpack_value(command[2])))
                code.append(("copy", iterator+"*", self.unpack_value(command[3])))
                self.active_iters.add(iterator)
                self.symbols.add_iterator(iterator)

                start = len(code)
                code.extend(self.generate_code(command[4]))
                code.append(("j_eq", iterator, 0, 3))
                code.append(("dec", iterator))
                code.append(("j", start - len(code) - 1))
                code[start:] = [("j_lt", iterator, iterator+"*", len(code) - start + 1)] + code[start:]
                self.active_iters.remove(iterator)
        return code

    def unpack_expr(self, expr):
        if isinstance(expr[1], int) and isinstance(expr[2], int):
            if expr[0] == 'add':
                return expr[1] + expr[2], True
            elif expr[0] == 'sub':
                return expr[1] - expr[2], True
            elif expr[0] == 'mul':
                return expr[1] * expr[2], True
            elif expr[0] == 'div':
                return expr[1] // expr[2] if expr[2] > 0 else 0, True
            elif expr[0] == 'mod':
                return expr[1] % expr[2] if expr[2] > 0 else 0, True
        elif isinstance(expr[1], int):
            if expr[1] == 0:
                if expr[0] == 'add':
                    return expr[2], True
                else:
                    return 0, True
            elif expr[1] == 1 and expr[0] == 'mul':
                return expr[2], True
            else:
                return expr, False
        elif isinstance(expr[2], int):
            if expr[2] == 0:
                if expr[0] == 'add' or expr[0] == 'sub':
                    return expr[1], True
                else:
                    return 0, True
            elif expr[2] == 1 and (expr[0] == 'mul' or expr[0] == 'div'):
                return expr[1], True
            elif expr[2] == 1 and expr[0] == 'mod':
                return 0, True
            else:
                return expr, False
        else:
            return expr, False

    def unpack_cond(self, cond):
        if cond[0] == "eq":
            check = "j_ne"

            def func(x, y):
                return x != y
        elif cond[0] == "ne":
            check = "j_eq"

            def func(x, y):
                return x == y
        else:
            check = "j_"
            if cond[0][0] == 'l':
                check += 'g'

                def f1(x, y):
                    return x > y
            else:
                check += 'l'

                def f1(x, y):
                    return x < y

            if cond[0][1] == 'e':
                check += 't'

                def func(x, y):
                    return f1(x, y)
            else:
                check += 'e'

                def func(x, y):
                    return f1(x, y) or x == y

        if cond[1][0] == cond[2][0] == "const":
            return func(cond[1][1], cond[2][1])

        elif cond[1][0] == "const" and cond[1][1] == 0:
            if check == "j_le":
                return True

            elif check == "j_gt":
                return False

            elif check == "j_ge" or check == "j_eq":
                return "j_eq", 0, self.unpack_value(cond[2])

            elif check == "j_lt" or check == "j_ne":
                return "j_ne", 0, self.unpack_value(cond[2])

        elif cond[2][0] == "const" and cond[2][1] == 0:
            if check == "j_ge":
                return True

            elif check == "j_lt":
                return False

            elif check == "j_le" or check == "j_eq":
                return "j_eq", 0, self.unpack_value(cond[1])

            elif check == "j_gt" or check == "j_ne":
                return "j_ne", 0, self.unpack_value(cond[1])

        else:
            return check, self.unpack_value(cond[1]), self.unpack_value(cond[2])

    def unpack_value(self, value, update=False):
        if value[0] == "load":
            if type(value[1]) == tuple:
                if value[1][0] == "undeclared":
                    var = value[1][1]
                    if var in self.active_iters:
                        if update:
                            raise Exception(f"Assigning to iterator {var}")
                        else:
                            return var
                    else:
                        if type(self.symbols.get_variable(var)) != Variable:
                            raise Exception(f"Incorrect usage of array {var} with no index provided")
                        elif update:
                            return var
                        else:
                            raise Exception(f"Use of undeclared variable {var}")
                elif value[1][0] == "array":
                    index = value[1][2]
                    if type(index) == int:
                        return value[1][1], index
                    else:
                        return value[1][1], self.unpack_value(index)
            else:
                if type(self.symbols.get_variable(value[1])) != Variable:
                    raise Exception(f"Incorrect usage of array {value[1]} with no index provided")
                elif update or self.symbols[value[1]].initialized:
                    return value[1]
                else:
                    raise Exception(f"Use of uninitialized variable {value[1]}")
        elif value[0] == "const":
            return value[1]
        else:
            return self.unpack_value(("load", value), update)

    def divide_into_blocks(self):
        block_starts = [0]
        jumps = []
        for i, code in enumerate(self.code):
            if "j" in code[0]:
                jumps.append(i)
                block_starts.append(i + code[-1])
                block_starts.append(i + 1)
        block_starts = sorted(set(block_starts))
        block_ids = {s: i for i, s in enumerate(block_starts)}
        for i in jumps:
            jump = self.code[i]
            self.code[i] = (*jump[:-1], block_ids[i + jump[-1]])
        self.blocks = [CodeBlock(s1, self.code[s1:s2]) for s1, s2 in zip(block_starts, block_starts[1:])]
        last_block = block_starts[-1]
        self.blocks.append(CodeBlock(last_block, self.code[last_block:]))

    def get_block_by_line(self, line_no):
        candidate = 0
        for i, b in enumerate(self.blocks):
            if b.start_index <= line_no:
                candidate = i
            else:
                break
        return candidate
