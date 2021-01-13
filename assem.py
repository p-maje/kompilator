import re
class AssemblyGenerator:
    def __init__(self, blocks, symbols):
        self.blocks = blocks
        self.symbols = symbols
        self.code = []
        self.iterators = []
        self.block_beginnings = []
        self.iterator_end = False

    def gen_code(self):
        for b in self.blocks:
            start = len(self.code)
            if self.iterator_end:
                self.iterator_end = False
                if len(self.iterators) != 1:
                    self.load_variable(self.iterators[-2], 'f')
                self.iterators.pop()
            self.block_beginnings.append(start)
            self.gen_code_from_commands(b.commands)
            b.code = self.code[start:]

        for i, c in enumerate(self.code):
            jump_loc = re.search('B[0-9]+', c)
            if jump_loc:
                self.code[i] = c[:jump_loc.start()] + f"{self.block_beginnings[int(jump_loc.group()[1:])] - i}"

    def gen_code_from_commands(self, commands):
        for command in commands:
            if command[0] == "write":
                value = command[1]
                register = 'a'
                register1 = 'b'
                if type(value) == int:
                    address = self.symbols.get_const(value)
                    if address is None:
                        address = self.symbols.add_const(value)
                        self.gen_const(address, register)
                        self.gen_const(value, register1)
                        self.code.append(f"STORE {register1} {register}")
                    else:
                        self.gen_const(address, register)
                elif value in self.iterators:
                    self.load_variable_address(value, register)
                    if value == self.iterators[-1]:
                        self.code.append(f"STORE f {register}")
                elif type(value) == tuple:
                    self.load_array_address_at(value[0], value[1], register, register1)
                else:
                    if self.symbols[value].initialized:
                        self.load_variable_address(value, register)
                    else:
                        raise Exception(f"Use of uninitialized variable {value}")
                self.code.append(f"PUT {register}")

            elif command[0] == "read":
                target = command[1]
                register = 'a'
                register1 = 'b'
                if type(target) == tuple and target[0] == "array":
                    self.load_array_address_at(target[1], target[2], register, register1)
                else:
                    self.load_variable_address(target, register)
                self.code.append(f"GET {register}")

            elif command[0] == "store":
                value = command[1]
                register = 'a'
                register1 = 'b'
                address = self.symbols.add_const(value)
                self.gen_const(address, register)
                self.gen_const(value, register1)
                self.code.append(f"STORE {register1} {register}")

            elif command[0] == "inc":
                self.code.append(f"INC f")
                self.iterator_end = True

            elif command[0] == "dec":
                self.code.append(f"DEC f")
                self.iterator_end = True

            elif command[0] == "assign":
                target = command[1]
                expression = command[2:]

                target_reg = 'a'
                second_reg = 'b'
                third_reg = 'c'
                self.calculate_expression(expression)

                if type(target) == tuple:
                    self.load_array_address_at(target[0], target[1], second_reg, third_reg)
                else:
                    self.load_variable_address(target, second_reg)
                self.code.append(f"STORE {target_reg} {second_reg}")

            elif command[0] == "copy":
                target = command[1]
                value = command[2]
                target_reg = 'a'
                second_reg = 'b'
                third_reg = 'c'
                if target in self.symbols.iterators:
                    if self.iterators:
                        address, bound_address = self.symbols.get_iterator(self.iterators[-1])
                        self.gen_const(address, 'e')
                        self.code.append(f"STORE f e")
                    self.iterators.append(target)
                    self.calculate_value(value, 'f', second_reg)
                    continue

                self.calculate_value(value, target_reg, second_reg)
                if type(target) == tuple:
                    self.load_array_address_at(target[0], target[1], second_reg, third_reg)
                else:
                    self.load_variable_address(target, second_reg)
                self.code.append(f"STORE {target_reg} {second_reg}")

            elif command[0].startswith('j'):
                self.conditional_jump(command)

            elif command[0] == 'halt':
                self.code.append("HALT")
                return

            else:
                raise Exception(f"Wrong command {command}")

    def gen_const(self, const, reg='a'):
        self.code.append(f"RESET {reg}")
        if const > 0:
            bits = bin(const)[2:]
            for bit in bits[:-1]:
                if bit == '1':
                    self.code.append(f"INC {reg}")
                self.code.append(f"SHL {reg}")
            if bits[-1] == '1':
                self.code.append(f"INC {reg}")

    def calculate_value(self, value, target_reg, second_reg=None):
        if type(value) == int:
            self.gen_const(value, target_reg)
        elif type(value) == str:
            self.load_variable(value, target_reg)
        else:
            self.load_array_at(value[0], value[1], target_reg, second_reg)

    def calculate_expression(self, expression, target_reg='a', second_reg='b', third_reg='c', fourth_reg='d',
                             fifth_reg='e'):
        if isinstance(expression[1], int):
            const, var = 1, 2
        elif isinstance(expression[2], int):
            const, var = 2, 1
        else:
            const = None

        if expression[0] == "add":
            if const and expression[const] < 12:
                self.calculate_value(expression[var], target_reg, second_reg)
                change = f"INC {target_reg}"
                self.code += expression[const] * [change]
            else:
                self.calculate_value(expression[1], target_reg, second_reg)
                if expression[1] == expression[2]:
                    self.code.append(f"SHL {target_reg}")
                else:
                    self.calculate_value(expression[2], second_reg, third_reg)
                    self.code.append(f"ADD {target_reg} {second_reg}")

        elif expression[0] == "sub":
            if const and const == 2 and expression[const] < 12:
                self.calculate_value(expression[var], target_reg, second_reg)
                change = f"DEC {target_reg}"
                self.code += expression[const] * [change]
            else:
                self.calculate_value(expression[1], target_reg, second_reg)
                self.calculate_value(expression[2], second_reg, third_reg)
                self.code.append(f"SUB {target_reg} {second_reg}")

        elif expression[0] == "mul":
            if const:
                val = expression[const]
                if val & (val - 1) == 0:
                    self.calculate_value(expression[var], target_reg, second_reg)
                    while val > 1:
                        self.code.append(f"SHL {target_reg}")
                        val /= 2
                    return

            self.calculate_value(expression[1], second_reg, target_reg)
            if expression[1] != expression[2]:
                self.calculate_value(expression[2], third_reg, target_reg)
            else:
                self.code.append(f"RESET {third_reg}")
                self.code.append(f"ADD {third_reg} {second_reg}")

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

        elif expression[0] == "div":
            if const and const == 2:
                val = expression[const]
                if val & (val - 1) == 0:
                    self.calculate_value(expression[var], target_reg, second_reg)
                    while val > 1:
                        self.code.append(f"SHR {target_reg}")
                        val /= 2
                    return

            self.calculate_value(expression[1], third_reg, second_reg)
            if expression[1] == expression[2]:
                self.code.append(f"RESET {target_reg}")
                self.code.append(f"JZERO {third_reg} 2")
                self.code.append(f"INC {target_reg}")
            else:
                self.calculate_value(expression[2], fourth_reg, second_reg)
                self.perform_division(target_reg, second_reg, third_reg, fourth_reg, fifth_reg)

        elif expression[0] == "mod":
            if const and const == 2:
                if expression[const] == 2:
                    self.calculate_value(expression[var], second_reg, target_reg)
                    self.code.append(f"RESET {target_reg}")
                    self.code.append(f"JODD {second_reg} 2")
                    self.code.append(f"JUMP 2")
                    self.code.append(f"INC {target_reg}")
                    return

            self.calculate_value(expression[1], third_reg, second_reg)
            self.calculate_value(expression[2], fourth_reg, second_reg)
            self.perform_division(second_reg, target_reg, third_reg, fourth_reg, fifth_reg)

    def perform_division(self, quotient_register='a', remainder_register='b', dividend_register='c',
                         divisor_register='d', temp_register='e'):
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

    def conditional_jump(self, jump, first_reg='a', second_reg='b', third_reg='c'):
            condition = jump[0][2:]
            block_to_jump = jump[-1]

            if not condition:
                self.code.append(f"JUMP B{block_to_jump}")
                return

            if jump[1] == 0:
                if self.iterators and jump[2] == self.iterators[-1]:
                    first_reg = 'f'
                else:
                    self.calculate_value(jump[2], first_reg, third_reg)
                if condition == "eq":
                    self.code.append(f"JZERO {first_reg} B{block_to_jump}")
                elif condition == "ne":
                    self.code.append(f"JZERO {first_reg} 2")
                    self.code.append(f"JUMP B{block_to_jump}")
                return

            elif jump[2] == 0:
                if self.iterators and jump[1] == self.iterators[-1]:
                    first_reg = 'f'
                else:
                    self.calculate_value(jump[1], first_reg, third_reg)
                if condition == "eq":
                    self.code.append(f"JZERO {first_reg} B{block_to_jump}")
                elif condition == "ne":
                    self.code.append(f"JZERO {first_reg} 2")
                    self.code.append(f"JUMP B{block_to_jump}")
                return

            self.calculate_value(jump[1], first_reg, third_reg)
            self.calculate_value(jump[2], second_reg, third_reg)

            if condition == "le":
                self.code.append(f"SUB {first_reg} {second_reg}")
                self.code.append(f"JZERO {first_reg} B{block_to_jump}")

            elif condition == "ge":
                self.code.append(f"SUB {second_reg} {first_reg}")
                self.code.append(f"JZERO {second_reg} B{block_to_jump}")

            elif condition == "lt":
                self.code.append(f"SUB {second_reg} {first_reg}")
                self.code.append(f"JZERO {second_reg} 2")
                self.code.append(f"JUMP B{block_to_jump}")

            elif condition == "gt":
                self.code.append(f"SUB {first_reg} {second_reg}")
                self.code.append(f"JZERO {first_reg} 2")
                self.code.append(f"JUMP B{block_to_jump}")

            elif condition == "eq":
                self.code.append(f"RESET {third_reg}")
                self.code.append(f"ADD {third_reg} {first_reg}")
                self.code.append(f"SUB {first_reg} {second_reg}")
                self.code.append(f"JZERO {first_reg} 2")
                self.code.append(f"JUMP 3")
                self.code.append(f"SUB {second_reg} {third_reg}")
                self.code.append(f"JZERO {second_reg} B{block_to_jump}")

            elif condition == "ne":
                self.code.append(f"RESET {third_reg}")
                self.code.append(f"ADD {third_reg} {first_reg}")
                self.code.append(f"SUB {first_reg} {second_reg}")
                self.code.append(f"JZERO {first_reg} 2")
                self.code.append(f"JUMP B{block_to_jump}")
                self.code.append(f"SUB {second_reg} {third_reg}")
                self.code.append(f"JZERO {second_reg} 2")
                self.code.append(f"JUMP B{block_to_jump}")

    def load_array_at(self, array, index, reg1, reg2):
        self.load_array_address_at(array, index, reg1, reg2)
        self.code.append(f"LOAD {reg1} {reg1}")

    def load_array_address_at(self, array, index, reg1, reg2):
        if type(index) == int:
            address = self.symbols.get_address((array, index))
            self.gen_const(address, reg1)
        else:
            if index in self.iterators:
                self.load_variable(index, reg1)
            else:
                if not self.symbols[index].initialized:
                    raise Exception(f"Trying to use {array}({index}) where variable {index} is uninitialized")
                self.load_variable(index, reg1)
            var = self.symbols.get_variable(array)
            self.gen_const(var.first_index, reg2)
            self.code.append(f"SUB {reg1} {reg2}")
            self.gen_const(var.memory_offset, reg2)
            self.code.append(f"ADD {reg1} {reg2}")

    def load_variable(self, name, reg):
        if self.iterators and name == self.iterators[-1]:
            self.code.append(f"RESET {reg}")
            self.code.append(f"ADD {reg} f")
        else:
            self.load_variable_address(name, reg)
            self.code.append(f"LOAD {reg} {reg}")

    def load_variable_address(self, name, reg):
        address = self.symbols.get_address(name)
        self.gen_const(address, reg)
