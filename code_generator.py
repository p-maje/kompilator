
class CodeGenerator:
    def __init__(self, commands, symbols):
        self.commands = commands
        self.symbols = symbols
        self.code = []

    def gen_code(self):
        self.gen_code_from_commands(self.commands)
        self.code.append("HALT")

    def gen_code_from_commands(self, commands):
        for command in commands:
            if command[0] == "write":
                value = command[1]
                register = 'a'
                if value[0] == "load":
                    address = self.symbols.get_address(value[1])
                    self.gen_const(address, register)
                else:
                    address = self.symbols.get_const(value[1])
                    if address is None:
                        register1 = 'b'
                        address = self.symbols.add_const(value[1])
                        self.gen_const(address, register)
                        self.gen_const(value[1], register1)
                        self.code.append(f"STORE {register1} {register}")
                    else:
                        self.gen_const(address, register)
                self.code.append(f"PUT {register}")

            elif command[0] == "read":
                target = command[1]
                register = 'a'
                address = self.symbols.get_address(target)
                self.gen_const(address, register)
                self.code.append(f"GET {register}")

            elif command[0] == "assign":
                target = command[1]
                expression = command[2]
                target_reg = 'a'
                second_reg = 'b'
                self.calculate_expression(expression)
                target_address = self.symbols.get_address(target)
                self.gen_const(target_address, second_reg)
                self.code.append(f"STORE {target_reg} {second_reg}")

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
                self.code[else_start - 1] = self.code[else_start - 1].replace('finish', str(command_end - else_start + 1))
                for i in range(condition_start, if_start):
                    self.code[i] = self.code[i].replace('finish', str(else_start - i))

            elif command[0] == "while":
                condition_start = len(self.code)
                self.check_condition(command[1])
                loop_start = len(self.code)
                self.gen_code_from_commands(command[2])
                self.code.append(f"JUMP {condition_start - len(self.code)}")
                loop_end = len(self.code)
                for i in range(condition_start, loop_start):
                    self.code[i] = self.code[i].replace('finish', str(loop_end - i))

            elif command[0] == "until":
                loop_start = len(self.code)
                self.gen_code_from_commands(command[2])
                condition_start = len(self.code)
                self.check_condition(command[1])
                condition_end = len(self.code)
                for i in range(condition_start, condition_end):
                    self.code[i] = self.code[i].replace('finish', str(loop_start - i))

            elif command[0] == "forup":
                # TODO 'constantify' variable if it's in condition
                prep_start = len(self.code)
                self.gen_code_from_commands([command[2]])
                self.code.append("JUMP loop_start")
                condition_start = len(self.code)
                self.check_condition(command[3])
                loop_start = len(self.code)
                self.gen_code_from_commands(command[4])
                address = self.symbols.get_address(command[1])
                self.gen_const(address, 'f')
                self.code.append(f"LOAD e f")
                self.code.append(f"INC e")
                self.code.append(f"STORE e f")
                self.code.append(f"JUMP {condition_start - len(self.code)}")
                loop_end = len(self.code)
                self.code[condition_start - 1] = f"JUMP {loop_start - condition_start + 1}"
                for i in range(condition_start, loop_start):
                    self.code[i] = self.code[i].replace('finish', str(loop_end - i))

            elif command[0] == "fordown":
                prep_start = len(self.code)
                self.gen_code_from_commands([command[2]])
                self.code.append("JUMP loop_start")
                condition_start = len(self.code)
                self.check_condition(command[3])
                loop_start = len(self.code)
                self.gen_code_from_commands(command[4])
                address = self.symbols.get_address(command[1])
                self.gen_const(address, 'f')
                self.code.append(f"LOAD e f")
                self.code.append(f"DEC e")
                self.code.append(f"STORE e f")
                self.code.append(f"JUMP {condition_start - len(self.code)}")
                loop_end = len(self.code)
                self.code[condition_start - 1] = f"JUMP {loop_start - condition_start + 1}"
                for i in range(condition_start, loop_start):
                    self.code[i] = self.code[i].replace('finish', str(loop_end - i))

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

    def calculate_expression(self, expression, target_reg='a', second_reg='b', third_reg='c', fourth_reg='d', fifth_reg='e'):
        if expression[0] == "const":
            self.gen_const(expression[1], target_reg)

        elif expression[0] == "load":
            src_address = self.symbols.get_address(expression[1])
            self.gen_const(src_address, second_reg)
            self.code.append(f"LOAD {target_reg} {second_reg}")

        elif expression[0] == "add" or expression[0] == "sub":
            self.calculate_expression(expression[1], target_reg, second_reg)
            self.calculate_expression(expression[2], second_reg, third_reg)
            self.code.append(f"{expression[0].upper()} {target_reg} {second_reg}")

        elif expression[0] == "mul":
            # TODO order optimization
            self.calculate_expression(expression[1], second_reg, target_reg)
            self.calculate_expression(expression[2], third_reg, target_reg)
            self.code.append(f"RESET {target_reg}")
            self.code.append(f"JZERO {third_reg} 7")
            self.code.append(f"JODD {third_reg} 2")
            self.code.append("JUMP 2")
            self.code.append(f"ADD {target_reg} {second_reg}")
            self.code.append(f"SHR {third_reg}")
            self.code.append(f"SHL {second_reg}")
            self.code.append("JUMP -6")

        elif expression[0] == "div":
            self.calculate_expression(expression[1], third_reg, second_reg)
            self.calculate_expression(expression[2], fourth_reg, second_reg)
            self.perform_division(target_reg, second_reg, third_reg, fourth_reg, fifth_reg)

        elif expression[0] == "mod":
            self.calculate_expression(expression[1], third_reg, second_reg)
            self.calculate_expression(expression[2], fourth_reg, second_reg)
            self.perform_division(second_reg, target_reg, third_reg, fourth_reg, fifth_reg)

    def perform_division(self, quotient_register='a', remainder_register='b', dividend_register='c', divisor_register='d', temp_register='e'):
        # TODO blad w cond1
        start = len(self.code)
        self.code.append(f"RESET {quotient_register}")
        self.code.append(f"RESET {remainder_register}")
        self.code.append(f"JZERO {divisor_register} finish")
        self.code.append(f"ADD {remainder_register} {dividend_register}")

        self.code.append(f"RESET {dividend_register}")
        self.code.append(f"ADD {dividend_register} {divisor_register}")
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
            self.code[i] = self.code[i].replace('midblock_start', str(midblock_start-i))
            self.code[i] = self.code[i].replace('block_start', str(block_start-i))
            self.code[i] = self.code[i].replace('finish', str(end-i))

    def check_condition(self, condition, first_reg='a', second_reg='b', third_reg='c'):
        self.calculate_expression(condition[1], first_reg, third_reg)
        self.calculate_expression(condition[2], second_reg, third_reg)

        if condition[0] == "le":
            self.code.append(f"SUB {first_reg} {second_reg}")
            self.code.append(f"JZERO {first_reg} 2")
            self.code.append(f"JUMP finish")

        elif condition[0] == "ge":
            self.code.append(f"SUB {second_reg} {first_reg}")
            self.code.append(f"JZERO {second_reg} 2")
            self.code.append(f"JUMP finish")

        elif condition[0] == "lt":
            self.code.append(f"SUB {second_reg} {first_reg}")
            self.code.append(f"JZERO {second_reg} finish")

        elif condition[0] == "gt":
            self.code.append(f"SUB {first_reg} {second_reg}")
            self.code.append(f"JZERO {first_reg} finish")

        elif condition[0] == "eq":
            self.code.append(f"RESET {third_reg}")
            self.code.append(f"ADD {third_reg} {first_reg}")
            self.code.append(f"SUB {first_reg} {second_reg}")
            self.code.append(f"JZERO {first_reg} 2")
            self.code.append(f"JUMP finish")
            self.code.append(f"SUB {second_reg} {third_reg}")
            self.code.append(f"JZERO {second_reg} 2")
            self.code.append(f"JUMP finish")

        elif condition[0] == "ne":
            self.code.append(f"RESET {third_reg}")
            self.code.append(f"ADD {third_reg} {first_reg}")
            self.code.append(f"SUB {first_reg} {second_reg}")
            self.code.append(f"JZERO {first_reg} 2")
            self.code.append(f"JUMP 3")
            self.code.append(f"SUB {second_reg} {third_reg}")
            self.code.append(f"JZERO {second_reg} finish")

