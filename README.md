EN | <a href="README.pl.md">PL</a>

# Compiler of a Simple Imperative Language
Developed as part of a Formal Languages and Translation Techniques course at Wrocław University of Science and Technology (winter 2020/2021).

## Technologies
Created using:
- **Python 3.8.5**  
- **<a href=https://pypi.org/project/sly/>SLY 0.4</a>**

## How to use
In the main directory run
```bash
python3 compiler.py <input file> <output file>
```

## Files
- `specs.pdf` – project guidelines including the grammar of the compiled langugage and the assembly commands available in the virtual machine (in Polish),
- `compiler.py` – the lexer and the parser,  
- `symbol_table.py` – memory management and the symbol table,
- `code_generator.py` – generation of the output assembly code from the syntax tree.

The `tests_*` directories contain some examples that allow to test the output code. Most of them were written by <a href="cs.pwr.edu.pl/gebala">Maciej Gębala</a> and <a href="cs.pwr.edu.pl/gotfryd">Karol Gotfryd</a>. They can be conveniently run with
```bash
./test.sh <directory name>
```

Error handling tests can be run using
```bash
./test_errors.sh
```
Both scripts require a pre-compiled virtual machine executable in the main project directory. The machine was developed by the lecturer, Maciej Gębala. Its sources can be found inside the `virtual_machine` directory. In order for all tests to run correctly, build it with the <a href="https://www.ginac.de/CLN/">CLN library</a> installed.

The `misc` directory contains some simple scripts that helped me during the development process.