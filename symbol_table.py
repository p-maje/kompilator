class Array:
    def __init__(self, memory_offset, first_index, last_index):
        self.memory_offset = memory_offset
        self.first_index = first_index
        self.last_index = last_index

    def __repr__(self):
        return f"[{self.memory_offset}, {self.first_index}:{self.last_index}]"

    def get_at(self, index):
        if self.first_index <= index <= self.last_index:
            return self.memory_offset + index - self.first_index
        else:
            raise Exception("Index out of range")


class Variable:
    def __init__(self, memory_offset):
        self.memory_offset = memory_offset
        self.register = None
        self.initialized = False

    def __repr__(self):
        return f"{'Uni' if not self.initialized else 'I'}nitialized variable at {self.memory_offset}"


class Iterator:
    def __init__(self, memory_offset, is_downto):
        self.is_downto = is_downto
        self.memory_offset = memory_offset  # stores the value, only stored when theres an embedded loop
        self.limit_address = memory_offset + 1  # stores the upper bound + 1 so that current_val = upper_bound + 1 - iters_left
        self.iters_left_address = memory_offset + 2  # stores iterations left, only stored when theres an embedded loop

    def __repr__(self):
        return f"iterator at {self.memory_offset}"


class SymbolTable(dict):
    def __init__(self):
        super().__init__()
        self.memory_offset = 0
        self.consts = {}
        self.iterators = {}

    def add_variable(self, name):
        if name in self:
            raise Exception(f"Redeclaration of {name}")
        self.setdefault(name, Variable(self.memory_offset))
        self.memory_offset += 1

    def add_array(self, name, begin, end):
        if name in self:
            raise Exception(f"Redeclaration of {name}")
        elif begin > end:
            raise Exception(f"Wrong range in declaration of {name}")
        self.setdefault(name, Array(self.memory_offset, begin, end))
        self.memory_offset += (end - begin) + 1

    def add_const(self, value):
        self.consts.setdefault(value, self.memory_offset)
        self.memory_offset += 1
        return self.memory_offset - 1

    def add_iterator(self, name, is_downto):
        iterator = Iterator(self.memory_offset, is_downto)
        self.memory_offset += 3
        self.iterators.setdefault(name, iterator)
        return iterator

    def is_iterator(self, value):
        return value in self.iterators

    def get_variable(self, name):
        if name in self:
            return self[name]
        elif name in self.iterators:
            return self.iterators[name]
        else:
            raise Exception(f"Undeclared variable {name}")

    def get_array_at(self, name, index):
        if name in self:
            try:
                return self[name].get_at(index)
            except AttributeError:
                raise Exception(f"Non-array {name} used as an array")
        else:
            raise Exception(f"Undeclared array {name}")

    def get_address(self, target):
        if type(target) == str:
            return self.get_variable(target).memory_offset
        else:
            return self.get_array_at(target[0], target[1])

    def get_iterator(self, name):
        if name in self.iterators:
            return self.iterators[name]

    def get_const(self, val):
        if val in self.consts:
            return self.consts[val]
