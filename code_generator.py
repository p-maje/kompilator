from symbol_table import Variable


class CodeGenerator:
    def __init__(self, commands, symbols):
        self.commands = commands
        self.symbols = symbols
        self.code = []
        self.iterators = []
        self.registers = {reg: None for reg in ['a', 'b', 'c', 'd', 'e']}
        self.is_reg_stored = {reg: True for reg in ['a', 'b', 'c', 'd', 'e']}
        self.regs_loaded = set()
        self.regs_used = set()
        self.upper_regs_used = set()

    def gen_code(self):
        self.gen_code_from_commands(self.commands)
        self.code.append("HALT")

    def gen_code_from_commands(self, commands):
        for command in commands:
            if command[0] == "write":
                value = command[1]
                if value[0] == "load":
                    for reg in self.registers:
                        if self.registers[reg] == value[1]:
                            self.store_register(reg)
                    if type(value[1]) == tuple:
                        if value[1][0] == "undeclared":
                            var = value[1][1]
                            register = self.load_variable_address(var, declared=False)
                        elif value[1][0] == "array":
                            register = self.load_array_address_at(value[1][1], value[1][2])
                        else:
                            raise Exception("Unexpected error")
                    else:
                        if self.symbols[value[1]].initialized:
                            register = self.load_variable_address(value[1])
                        else:
                            raise Exception(f"Use of uninitialized variable {value[1]}")
                elif value[0] == "const":
                    address = self.symbols.get_const(value[1])
                    if address is None:
                        address = self.symbols.add_const(value[1])
                        register = self.load_const(address)
                        register1 = self.load_const(value[1])
                        self.code.append(f"STORE {register1} {register}")
                    else:
                        register = self.load_const(address)
                else:
                    raise Exception("Unexpected error")
                self.code.append(f"PUT {register}")

            elif command[0] == "read":
                target = command[1]
                if type(target) == tuple:
                    if target[0] == "undeclared":
                        if target[1] in self.symbols.iterators:
                            raise Exception(f"Reading to iterator {target[1]}")
                        else:
                            raise Exception(f"Reading to undeclared variable {target[1]}")
                    elif target[0] == "array":
                        # TODO arrays initialized?
                        register = self.load_array_address_at(target[1], target[2])
                    else:
                        raise Exception("Unexpected error")
                else:
                    # reading to x invalidates register stored x and t(x)
                    for reg in self.registers:
                        val = self.registers[reg]
                        if val == target:
                            self.registers[reg] = None
                        elif type(val) == tuple and val[1] == ('load', target):
                            self.store_register(reg)
                            self.registers[reg] = None
                    register = self.load_variable_address(target)
                    self.symbols[target].initialized = True
                self.code.append(f"GET {register}")

            elif command[0] == "assign":
                target = command[1]
                expression = command[2]
                target_reg = self.calculate_expression(expression)
                self.registers[target_reg] = target
                self.is_reg_stored[target_reg] = False
                if type(target) == tuple:
                    if target[0] == "undeclared":
                        if target[1] in self.symbols.iterators:
                            raise Exception(f"Assigning to iterator {target[1]}")
                        else:
                            raise Exception(f"Assigning to undeclared variable {target[1]}")
                    elif target[0] == "array":
                        self.registers[target_reg] = target[1:]
                        # second_reg = self.load_array_address_at(target[1], target[2])
                        # self.code.append(f"STORE {target_reg} {second_reg}")
                    else:
                        raise Exception("Unexpected error")
                else:
                    if type(self.symbols[target]) == Variable:
                        self.symbols[target].initialized = True
                        for reg in self.registers:
                            var = self.registers[reg]
                            if type(var) == tuple and var[1] == ('load', target):
                                self.registers[reg] = None
                    else:
                        raise Exception(f"Assigning to array {target} with no index provided")
                name = self.registers[target_reg]
                for reg in self.registers:
                    if reg != target_reg and self.registers[reg] == name:
                        self.registers[reg] = None
                # self.code.append(f"STORE {target_reg} {second_reg}")

            elif command[0] == "if":
                condition_start = len(self.code)
                self.check_condition(command[1])
                command_start = len(self.code)
                self.gen_code_from_commands(command[2])
                command_end = len(self.code)
                for i in range(condition_start, command_start):
                    self.code[i] = self.code[i].replace('finish', str(command_end - i))

            elif command[0] == "ifelse":
                condition_start = len(self.code)
                self.check_condition(command[1])
                if_start = len(self.code)
                self.gen_code_from_commands(command[2])
                self.code.append(f"JUMP finish")
                else_start = len(self.code)
                self.gen_code_from_commands(command[3])
                command_end = len(self.code)
                self.code[else_start - 1] = self.code[else_start - 1].replace('finish',
                                                                              str(command_end - else_start + 1))
                for i in range(condition_start, if_start):
                    self.code[i] = self.code[i].replace('finish', str(else_start - i))

            elif command[0] == "while":
                condition_start = len(self.code)
                self.check_condition(command[1])
                loop_start = len(self.code)
                for reg in self.registers:
                    if type(self.registers[reg]) == int:
                        self.registers[reg] = None
                self.gen_code_from_commands(command[2])
                self.code.append(f"JUMP {condition_start - len(self.code)}")
                loop_end = len(self.code)
                for i in range(condition_start, loop_start):
                    self.code[i] = self.code[i].replace('finish', str(loop_end - i))

            elif command[0] == "until":
                loop_start = len(self.code)
                for reg in self.registers:
                    if type(self.registers[reg]) == int:
                        self.registers[reg] = None
                self.gen_code_from_commands(command[2])
                condition_start = len(self.code)
                self.check_condition(command[1])
                condition_end = len(self.code)
                for i in range(condition_start, condition_end):
                    self.code[i] = self.code[i].replace('finish', str(loop_start - i))

            elif command[0] == "forup":
                temp_reg = None
                if self.iterators:
                    last_iter = self.symbols.get_iterator(self.iterators[-1])
                    temp_reg = self.load_const(last_iter.iters_left_address)
                    self.code.append(f"STORE f {temp_reg}")
                    self.free_register(temp_reg)
                    temp_reg = self.load_const(last_iter.limit_address)
                    self.code.append(f"LOAD {temp_reg} {temp_reg}")
                    self.code.append(f"SUB {temp_reg} f")
                    self.gen_const(last_iter.memory_offset, 'f')
                    self.code.append(f"STORE {temp_reg} f")
                    self.registers[temp_reg] = self.iterators[-1]

                iterator_name = command[1]
                iterator = self.symbols.add_iterator(iterator_name, is_downto=False)

                # for j from i to x (if we're already inside a 'for i ...' loop)
                if temp_reg and type(command[2]) == tuple and type(command[2][1]) == tuple and command[2][1][1] == self.iterators[-1]:
                    lower_bound_reg = temp_reg
                else:
                    lower_bound_reg = self.calculate_expression(command[2])
                    # if temp_reg:
                    #     self.free_register(temp_reg)

                # for i from x to x TODO this doesnt work
                # if command[2] == command[3]:
                #     self.code.append("RESET f")
                #     self.code.append(f"ADD f {lower_bound_reg}")
                #     self.gen_code_from_commands(command[4])
                #     continue

                # number of iterations left, upper + 1 - lower, will be stored in reg f
                # then if we store (upper + 1) we can restore i = upper + 1 - f
                if command[3][0] == 'const':
                    self.gen_const(command[3][1], 'f')
                else:
                    if temp_reg and type(command[3][1]) == tuple and command[3][1][1] == self.iterators[-1]:
                        self.code.append("RESET f")
                        self.code.append(f"ADD f {temp_reg}")
                    else:
                        address = self.symbols.get_address(command[3])
                        self.gen_const(address, 'f')
                        self.code.append("LOAD f f")
                if temp_reg:
                    self.free_register(temp_reg)
                self.code.append("INC f")
                temp_reg = self.load_const(iterator.limit_address)
                self.code.append(f"STORE f {temp_reg}")
                self.free_register(temp_reg)
                self.code.append(f"SUB f {lower_bound_reg}")
                self.free_register(lower_bound_reg)

                self.iterators.append(iterator_name)

                condition_start = len(self.code)
                self.code.append("JZERO f finish")

                loop_start = len(self.code)
                # dont use reg-stored values to load stuff because cie zmiecie z planszy
                for reg in self.registers:
                    if type(self.registers[reg]) == int:
                        self.registers[reg] = None

                self.gen_code_from_commands(command[4])
                for reg in self.regs_loaded:
                    self.register_changed(reg)
                self.regs_loaded.clear()
                self.code.append(f"DEC f")
                self.code.append(f"JUMP {condition_start - len(self.code)}")
                loop_end = len(self.code)

                self.code[loop_start - 1] = f"JZERO f {loop_end - loop_start + 1}"

                self.iterators.pop()

                if self.iterators:
                    address = self.symbols.get_iterator(self.iterators[-1]).iters_left_address
                    self.gen_const(address, 'f')
                    self.code.append(f"LOAD f f")

            elif command[0] == "fordown":
                temp_reg = None
                if self.iterators:
                    last_iter = self.symbols.get_iterator(self.iterators[-1])
                    temp_reg = self.load_const(last_iter.iters_left_address)
                    self.code.append(f"STORE f {temp_reg}")
                    self.free_register(temp_reg)
                    temp_reg = self.load_const(last_iter.limit_address)
                    self.code.append(f"LOAD {temp_reg} {temp_reg}")
                    self.code.append(f"SUB {temp_reg} f")
                    self.gen_const(last_iter.memory_offset, 'f')
                    self.code.append(f"STORE {temp_reg} f")
                    self.registers[temp_reg] = self.iterators[-1]

                iterator_name = command[1]
                iterator = self.symbols.add_iterator(iterator_name, is_downto=True)

                # for j from i downto x (if we're already inside a 'for i ...' loop)
                if temp_reg and type(command[3]) == tuple and type(command[3][1]) == tuple and command[3][1][1] == \
                        self.iterators[-1]:
                    lower_bound_reg = temp_reg
                else:
                    lower_bound_reg = self.calculate_expression(command[3])

                # number of iterations left, upper + 1 - lower, will be stored in reg f
                # then if we store (upper + 1) we can restore i = upper + 1 - f
                if command[2][0] == 'const':
                    self.gen_const(command[2][1], 'f')
                else:
                    if temp_reg and type(command[2][1]) == tuple and command[2][1][1] == self.iterators[-1]:
                        self.code.append("RESET f")
                        self.code.append(f"ADD f {temp_reg}")
                    else:
                        address = self.symbols.get_address(command[2])
                        self.gen_const(address, 'f')
                        self.code.append("LOAD f f")
                if temp_reg:
                    self.free_register(temp_reg)
                self.code.append(f"DEC {lower_bound_reg}")
                temp_reg = self.load_const(iterator.limit_address)
                self.code.append(f"STORE {lower_bound_reg} {temp_reg}")
                self.free_register(temp_reg)
                self.code.append(f"SUB f {lower_bound_reg}")
                self.free_register(lower_bound_reg)

                self.iterators.append(iterator_name)

                condition_start = len(self.code)
                self.code.append("JZERO f finish")

                loop_start = len(self.code)
                for reg in self.registers:
                    if type(self.registers[reg]) == int:
                        self.registers[reg] = None

                self.gen_code_from_commands(command[4])
                for reg in self.regs_loaded:
                    self.register_changed(reg)
                self.regs_loaded.clear()
                self.code.append(f"DEC f")
                self.code.append(f"JUMP {condition_start - len(self.code)}")
                loop_end = len(self.code)

                self.code[loop_start - 1] = f"JZERO f {loop_end - loop_start + 1}"

                self.iterators.pop()

                if self.iterators:
                    address = self.symbols.get_iterator(self.iterators[-1]).iters_left_address
                    self.gen_const(address, 'f')
                    self.code.append(f"LOAD f f")

            self.regs_used.clear()

    def gen_const(self, const, reg):
        self.code.append(f"RESET {reg}")
        if const > 0:
            bits = bin(const)[2:]
            for bit in bits[:-1]:
                if bit == '1':
                    self.code.append(f"INC {reg}")
                self.code.append(f"SHL {reg}")
            if bits[-1] == '1':
                self.code.append(f"INC {reg}")

    def calculate_expression(self, expression):
        if expression[0] == "const":
            val = expression[1]
            reg = self.load_const(val)
            return reg

        elif expression[0] == "load":
            if type(expression[1]) == tuple:
                if expression[1][0] == "undeclared":
                    reg = self.load_variable(expression[1][1], declared=False)
                elif expression[1][0] == "array":
                    reg = self.load_array_at(expression[1][1], expression[1][2])
                else:
                    raise Exception("Unexpected error")
            else:
                if self.symbols[expression[1]].initialized:
                    reg = self.load_variable(expression[1])
                else:
                    raise Exception(f"Use of uninitialized variable {expression[1]}")
            return reg

        elif expression[0] == "add" or expression[0] == "sub":
            if expression[1][0] == expression[2][0] == "const":
                if expression[0] == "add":
                    val = expression[1][1] + expression[2][1]
                else:
                    val = expression[1][1] - expression[2][1]
                reg = self.load_const(val)
            elif expression[1][0] == "const" and expression[1][1] < 12:
                reg = self.calculate_expression(expression[2])
                self.register_changed(reg)
                change = ("INC " if expression[0] == "add" else "DEC ") + reg
                self.code += expression[1][1] * [change]
            elif expression[2][0] == "const" and expression[2][1] < 12:
                reg = self.calculate_expression(expression[1])
                self.register_changed(reg)
                change = ("INC " if expression[0] == "add" else "DEC ") + reg
                self.code += expression[2][1] * [change]
            else:
                reg = self.calculate_expression(expression[1])
                reg2 = self.calculate_expression(expression[2])
                self.register_changed(reg)
                self.code.append(f"{expression[0].upper()} {reg} {reg2}")
                self.free_register(reg2)
            return reg

        elif expression[0] == "mul":
            const = None
            expr = None

            if expression[1][0] == expression[2][0] == "const":
                val = expression[1][1] * expression[2][1]
                reg = self.load_const(val)
                return reg

            elif expression[1][0] == "const":
                const = expression[1][1]
                expr = expression[2]

            elif expression[2][0] == "const":
                const = expression[2][1]
                expr = expression[1]

            if const is not None:
                if const == 0:
                    reg = self.load_const(0)
                    return reg
                elif const == 1:
                    reg = self.calculate_expression(expr)
                    self.register_changed(reg)
                    return reg
                elif const & (const - 1) == 0:
                    reg = self.calculate_expression(expr)
                    self.register_changed(reg)
                    while const > 1:
                        self.code.append(f"SHL {reg}")
                        const /= 2
                    return reg

            second_reg = self.calculate_expression(expression[1])
            third_reg = self.calculate_expression(expression[2])
            target_reg = self.anonymously_allocate_register()

            self.register_changed(second_reg)
            self.register_changed(third_reg)

            self.code.append(f"RESET {target_reg}")
            self.code.append(f"JZERO {second_reg} 21")
            self.code.append(f"JZERO {third_reg} 20")
            self.code.append(f"ADD {target_reg} {second_reg}")
            self.code.append(f"SUB {target_reg} {third_reg}")
            self.code.append(f"JZERO {target_reg} 9")

            # if second >= third it's better to do $2 * $3
            self.code.append(f"RESET {target_reg}")
            self.code.append(f"JZERO {third_reg} 15")
            self.code.append(f"JODD {third_reg} 2")
            self.code.append("JUMP 2")
            self.code.append(f"ADD {target_reg} {second_reg}")
            self.code.append(f"SHR {third_reg}")
            self.code.append(f"SHL {second_reg}")
            self.code.append("JUMP -6")

            # if second <= third it's better to do $3 * $2
            self.code.append(f"RESET {target_reg}")
            self.code.append(f"JZERO {second_reg} 7")
            self.code.append(f"JODD {second_reg} 2")
            self.code.append("JUMP 2")
            self.code.append(f"ADD {target_reg} {third_reg}")
            self.code.append(f"SHR {second_reg}")
            self.code.append(f"SHL {third_reg}")
            self.code.append("JUMP -6")

            self.free_register(second_reg)
            self.free_register(third_reg)
            return target_reg

        elif expression[0] == "div":
            if expression[1][0] == expression[2][0] == "const":
                if expression[2][1] > 0:
                    reg = self.load_const(expression[1][1] // expression[2][1])
                else:
                    reg = self.load_const(0)
                return reg

            elif expression[1][0] == "const" and expression[1][1] == 0:
                reg = self.load_const(0)
                return reg

            elif expression[2][0] == "const" and expression[2][1] < 2:
                if expression[2][1] == 0:
                    reg = self.load_const(0)
                else:
                    reg = self.calculate_expression(expression[1])
                    self.register_changed(reg)
                return reg

            # when divided by a power of two, use shr
            elif expression[2][0] == "const" and (expression[2][1] & (expression[2][1] - 1) == 0):
                reg = self.calculate_expression(expression[1])
                self.register_changed(reg)
                n = expression[2][1]
                while n > 1:
                    self.code.append(f"SHR {reg}")
                    n /= 2
                return reg

            else:
                dividend_reg = self.calculate_expression(expression[1])
                divisor_reg = self.calculate_expression(expression[2])
                self.register_changed(dividend_reg)
                self.register_changed(dividend_reg)

                reg = self.perform_division(dividend_reg, divisor_reg)
                return reg

        elif expression[0] == "mod":
            if expression[1][0] == expression[2][0] == "const":
                if expression[2][1] > 0:
                    reg = self.load_const(expression[1][1] % expression[2][1])
                else:
                    reg = self.load_const(0)
                return reg

            elif expression[1][0] == "const" and expression[1][1] == 0:
                reg = self.load_const(0)
                return reg

            elif expression[2][0] == "const" and expression[2][1] < 3:
                if expression[2][1] < 2:
                    reg = self.load_const(0)
                else:
                    reg2 = self.calculate_expression(expression[1])
                    reg = self.anonymously_allocate_register()
                    self.code.append(f"RESET {reg}")
                    self.code.append(f"JODD {reg2} 2")
                    self.code.append(f"JUMP 2")
                    self.code.append(f"INC {reg}")
                    self.free_register(reg2)
                return reg

            else:
                dividend_reg = self.calculate_expression(expression[1])
                divisor_reg = self.calculate_expression(expression[2])
                self.register_changed(dividend_reg)
                self.register_changed(dividend_reg)
                reg = self.perform_division(dividend_reg, divisor_reg, modulo=True)
                return reg

    def perform_division(self, dividend_register, divisor_register, modulo=False):
        quotient_register = self.anonymously_allocate_register()
        remainder_register = self.anonymously_allocate_register()
        temp_register = self.anonymously_allocate_register()

        start = len(self.code)
        self.code.append(f"RESET {quotient_register}")
        self.code.append(f"RESET {remainder_register}")
        self.code.append(f"JZERO {divisor_register} finish")
        self.code.append(f"ADD {remainder_register} {dividend_register}")

        self.code.append(f"RESET {dividend_register}")
        self.code.append(f"ADD {dividend_register} {divisor_register}")
        self.code.append(f"RESET {temp_register}")
        self.code.append(f"ADD {temp_register} {remainder_register}")
        self.code.append(f"SUB {temp_register} {dividend_register}")
        self.code.append(f"JZERO {temp_register} block_start")
        self.code.append(f"RESET {temp_register}")
        self.code.append(f"ADD {temp_register} {dividend_register}")
        self.code.append(f"SUB {temp_register} {remainder_register}")
        self.code.append(f"JZERO {temp_register} 3")
        self.code.append(f"SHR {dividend_register}")
        self.code.append(f"JUMP 3")
        self.code.append(f"SHL {dividend_register}")
        self.code.append(f"JUMP -7")

        block_start = len(self.code)
        self.code.append(f"RESET {temp_register}")
        self.code.append(f"ADD {temp_register} {dividend_register}")
        self.code.append(f"SUB {temp_register} {remainder_register}")
        self.code.append(f"JZERO {temp_register} 2")
        self.code.append(f"JUMP finish")
        self.code.append(f"SUB {remainder_register} {dividend_register}")
        self.code.append(f"INC {quotient_register}")

        midblock_start = len(self.code)
        self.code.append(f"RESET {temp_register}")
        self.code.append(f"ADD {temp_register} {dividend_register}")
        self.code.append(f"SUB {temp_register} {remainder_register}")
        self.code.append(f"JZERO {temp_register} block_start")
        self.code.append(f"SHR {dividend_register}")
        self.code.append(f"RESET {temp_register}")
        self.code.append(f"ADD {temp_register} {divisor_register}")
        self.code.append(f"SUB {temp_register} {dividend_register}")
        self.code.append(f"JZERO {temp_register} 2")
        self.code.append(f"JUMP finish")
        self.code.append(f"SHL {quotient_register}")
        self.code.append(f"JUMP midblock_start")
        end = len(self.code)

        for i in range(start, end):
            self.code[i] = self.code[i].replace('midblock_start', str(midblock_start - i))
            self.code[i] = self.code[i].replace('block_start', str(block_start - i))
            self.code[i] = self.code[i].replace('finish', str(end - i))

        self.free_register(dividend_register)
        self.free_register(divisor_register)
        self.free_register(temp_register)
        if modulo:
            self.free_register(quotient_register)
            return remainder_register
        else:
            self.free_register(remainder_register)
            return quotient_register

    def check_condition(self, condition, first_reg='a', second_reg='b', third_reg='c'):
        if condition[1][0] == "const" and condition[2][0] == "const":
            if condition[0] == "le":
                if not condition[1][1] <= condition[2][1]:
                    self.code.append(f"JUMP finish")

            elif condition[0] == "ge":
                if not condition[1][1] >= condition[2][1]:
                    self.code.append(f"JUMP finish")

            elif condition[0] == "lt":
                if not condition[1][1] < condition[2][1]:
                    self.code.append(f"JUMP finish")

            elif condition[0] == "gt":
                if not condition[1][1] > condition[2][1]:
                    self.code.append(f"JUMP finish")

            elif condition[0] == "eq":
                if not condition[1][1] == condition[2][1]:
                    self.code.append(f"JUMP finish")

            elif condition[0] == "ne":
                if not condition[1][1] != condition[2][1]:
                    self.code.append(f"JUMP finish")

        elif condition[1][0] == "const" and condition[1][1] == 0:
            if condition[0] == "le":
                pass

            elif condition[0] == "lt":
                self.code.append(f"JUMP finish")

            elif condition[0] == "ge" or condition[0] == "eq":
                reg = self.calculate_expression(condition[2])
                self.code.append(f"JZERO {reg} 2")
                self.code.append("JUMP finish")
                self.free_register(reg)

            elif condition[0] == "gt" or condition[0] == "ne":
                reg = self.calculate_expression(condition[2])
                self.code.append(f"JZERO {reg} finish")
                self.free_register(reg)

        elif condition[2][0] == "const" and condition[2][1] == 0:
            if condition[0] == "ge":
                pass

            elif condition[0] == "lt":
                self.code.append(f"JUMP finish")

            elif condition[0] == "le" or condition[0] == "eq":
                reg = self.calculate_expression(condition[1])
                self.code.append(f"JZERO {reg} 2")
                self.code.append("JUMP finish")
                self.free_register(reg)

            elif condition[0] == "gt" or condition[0] == "ne":
                reg = self.calculate_expression(condition[1])
                self.code.append(f"JZERO {reg} finish")
                self.free_register(reg)

        else:
            first_reg = self.calculate_expression(condition[1])
            second_reg = self.calculate_expression(condition[2])

            if condition[0] == "le":
                self.register_changed(first_reg)
                self.code.append(f"SUB {first_reg} {second_reg}")
                self.code.append(f"JZERO {first_reg} 2")
                self.code.append(f"JUMP finish")

            elif condition[0] == "ge":
                self.register_changed(second_reg)
                self.code.append(f"SUB {second_reg} {first_reg}")
                self.code.append(f"JZERO {second_reg} 2")
                self.code.append(f"JUMP finish")

            elif condition[0] == "lt":
                self.register_changed(second_reg)
                self.code.append(f"SUB {second_reg} {first_reg}")
                self.code.append(f"JZERO {second_reg} finish")

            elif condition[0] == "gt":
                self.register_changed(first_reg)
                self.code.append(f"SUB {first_reg} {second_reg}")
                self.code.append(f"JZERO {first_reg} finish")

            elif condition[0] == "eq":
                third_reg = self.load_const(0)
                self.register_changed(first_reg)
                self.register_changed(second_reg)
                self.code.append(f"ADD {third_reg} {first_reg}")
                self.code.append(f"SUB {first_reg} {second_reg}")
                self.code.append(f"JZERO {first_reg} 2")
                self.code.append(f"JUMP finish")
                self.code.append(f"SUB {second_reg} {third_reg}")
                self.code.append(f"JZERO {second_reg} 2")
                self.code.append(f"JUMP finish")
                self.free_register(third_reg)

            elif condition[0] == "ne":
                third_reg = self.load_const(0)
                self.register_changed(first_reg)
                self.register_changed(second_reg)
                self.code.append(f"ADD {third_reg} {first_reg}")
                self.code.append(f"SUB {first_reg} {second_reg}")
                self.code.append(f"JZERO {first_reg} 2")
                self.code.append(f"JUMP 3")
                self.code.append(f"SUB {second_reg} {third_reg}")
                self.code.append(f"JZERO {second_reg} finish")
                self.free_register(third_reg)
            self.free_register(first_reg)
            self.free_register(second_reg)


    def load_array_at(self, array, index):
        for reg in self.registers:
            if self.registers[reg] == (array, index):
                self.regs_used.add(reg)
                return reg
        # if type(index) == int:
        #     for reg in self.registers:
        #         if self.registers[reg] == (array, index):
        #             self.regs_used.add(reg)
        #             return reg
        reg = self.load_array_address_at(array, index)
        self.code.append(f"LOAD {reg} {reg}")
        self.regs_loaded.add(reg)
        self.is_reg_stored[reg] = True
        return reg

    def load_array_address_at(self, array, index):
        if type(index) == int:
            address = self.symbols.get_address((array, index))
            reg = self.load_const(address)
            return reg
        elif type(index) == tuple:
            if type(index[1]) == tuple:
                reg1 = self.load_variable(index[1][1], declared=False)
            else:
                if not self.symbols[index[1]].initialized:
                    raise Exception(f"Trying to use {array}({index[1]}) where variable {index[1]} is uninitialized")
                reg1 = self.load_variable(index[1])
            var = self.symbols.get_variable(array)
            if var.first_index > 0:
                reg2 = self.allocate_register(var.first_index)
                if self.registers[reg2] != var.first_index:
                    self.registers[reg2] = var.first_index
                    self.gen_const(var.first_index, reg2)
                self.code.append(f"SUB {reg1} {reg2}")
                self.free_register(reg2)
            if var.memory_offset > 0:
                reg2 = self.allocate_register(var.memory_offset)
                if self.registers[reg2] != var.memory_offset:
                    self.registers[reg2] = var.memory_offset
                    self.gen_const(var.memory_offset, reg2)
                self.code.append(f"ADD {reg1} {reg2}")
                self.free_register(reg2)
            self.registers[reg1] = None
            return reg1

    def load_const(self, val):
        reg = self.allocate_register(val)
        if self.registers[reg] != val:
            self.registers[reg] = val
            self.gen_const(val, reg)
        return reg

    def load_variable(self, name, declared=True):
        if not declared and self.iterators and name == self.iterators[-1]:
            reg = self.allocate_register(name)
            iterator = self.symbols.get_iterator(name)
            bound_address = iterator.limit_address
            self.gen_const(bound_address, reg)
            self.code.append(f"LOAD {reg} {reg}")
            if iterator.is_downto:
                self.code.append(f"ADD {reg} f")
            else:
                self.code.append(f"SUB {reg} f")
            self.is_reg_stored[reg] = True
        else:
            for reg in self.registers:
                if self.registers[reg] == name:
                    self.regs_used.add(reg)
                    return reg
            reg = self.load_variable_address(name, declared)
            self.code.append(f"LOAD {reg} {reg}")
            self.regs_loaded.add(reg)
            self.is_reg_stored[reg] = True
        return reg

    def load_variable_address(self, name, declared=True):
        if declared or name in self.iterators:
            address = self.symbols.get_address(name)
            reg = self.allocate_register(address)
            if self.registers[reg] != address:
                self.registers[reg] = address
                self.gen_const(address, reg)
            if self.iterators and name == self.iterators[-1]:
                temp_reg = self.load_variable(name, declared=False)
                self.code.append(f"STORE {temp_reg} {reg}")
                self.free_register(temp_reg)
            return reg
        else:
            raise Exception(f"Undeclared variable {name}")

    def anonymously_allocate_register(self):
        for reg in self.registers:
            if reg not in self.regs_used:
                self.register_changed(reg)
                self.regs_used.add(reg)
                self.registers[reg] = None
                return reg

    def allocate_register(self, var):
        for reg in self.registers:
            if self.registers[reg] == var:
                self.regs_used.add(reg)
                return reg

        for reg in self.registers:
            if reg not in self.regs_used:
                self.register_changed(reg)
                # in case we want x's address but x was in unused reg so its address was loaded bc reg changed
                for reg2 in self.registers:
                    if self.registers[reg2] == var:
                        self.regs_used.add(reg2)
                        return reg2
                self.regs_used.add(reg)
                return reg

        print("ALLOCATION FAILED WHAT THE HECK")

    def register_changed(self, reg):
        if not self.is_reg_stored[reg]:
            self.store_register(reg)
        self.registers[reg] = None

    def store_register(self, reg):
        var = self.registers[reg]
        if var is None or type(var) == int:
            return

        lock_needed = reg not in self.regs_used
        if lock_needed:
            self.regs_used.add(reg)

        if type(var) == tuple:
            temp_reg = self.load_array_address_at(*var)
            self.code.append(f"STORE {reg} {temp_reg}")
            self.free_register(temp_reg)
        else:
            temp_reg = self.load_variable_address(var)
            self.code.append(f"STORE {reg} {temp_reg}")
            self.free_register(temp_reg)

        if lock_needed:
            self.free_register(reg)

    def free_register(self, reg):
        self.regs_used.remove(reg)

    def lock_atomic_expressions(self, var_list):
        for reg in self.registers:
            if self.registers[reg] in var_list:
                var_list.remove(self.registers[reg])
                self.regs_used.add(reg)
                if not var_list:
                    break
