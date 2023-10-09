from typing import List, Optional


class LineBase:
    def __init__(self, global_context: 'GlobalContext'):
        self.global_context = global_context

    def append(self, next_line: 'LineBase') -> bool:
        pass


class Variable(LineBase):
    def __init__(self, global_context: 'GlobalContext', name: str, values: str):
        super().__init__(global_context)
        self.name = name
        self.values = list(values)


class GlobalVariable(Variable):
    pass


class GlobalContext:
    variables: List[GlobalVariable]
    contexts: List['Context']
    current_context: 'Context' = None

    def __init__(self):
        self.variables = []
        self.contexts = []

    def append(self, next_line: 'LineBase'):
        if isinstance(next_line, GlobalVariable):
            self.append_variable(next_line)
            return

        if isinstance(next_line, Variable):
            if self.current_context is None:
                raise Exception('Trying to append variable to no context')
            self.current_context.append_variable(next_line)
            return

        if isinstance(next_line, CodeLine):
            if self.current_context is None:
                raise Exception('Trying to append code to no context')
            self.current_context.append_code(next_line)
            return

        if isinstance(next_line, EndContext):
            self.contexts.append(self.current_context)
            self.current_context = None
            return

        if isinstance(next_line, Context):
            if self.current_context is not None:
                raise Exception('Trying to start context, when previous not ended')
            self.current_context = next_line
            return

    def get_variable(self, name: str) -> Variable:
        for var in self.current_context.variables:
            if var.name == name:
                return var

        for var in self.variables:
            if var.name == name:
                return var

        raise Exception(f'Unknown variable {name}')

    def append_variable(self, variable: GlobalVariable):
        self.variables.append(variable)

    def snapshots(self):
        if len(self.variables) == 0:
            yield dict()
            return

        indexes = [0] * len(self.variables)

        while True:
            for i, variable in reversed(list(enumerate(self.variables))):
                if indexes[i] >= len(variable.values):
                    if i == 0:
                        return

                    indexes[i] = 0
                    indexes[i - 1] += 1

            d = dict()
            for i, variable in enumerate(self.variables):
                d[variable.name] = variable.values[indexes[i]]

            indexes[-1] += 1
            yield d

    def compile(self):
        text = "// Compiled with tup 0.1a\n\n"

        if self.current_context is not None:
            raise Exception('Context not closed when file ends')

        for snapshot in self.snapshots():
            for context in self.contexts:
                text += context.compile(snapshot)
                text += "// Next context\n"

        return text


class EndContext(LineBase):
    pass


class CodeLine(LineBase):
    def __init__(self, global_context: GlobalContext, code: str):
        super().__init__(global_context)
        self.code = code


import re


CODE_USE_VARIABLE_RE = re.compile(r'\$\{(?P<expression>[^}]*)\}')


def process_code_line(global_context: GlobalContext, line: str, snapshot: dict):
    def calc_val(m1):
        e = m1.group('expression')
        return eval(f'str({e})', globals(), snapshot)

    m = re.search('\\$\\{(?P<expression>[^}]*)\\}', line)
    if m is None:
        return line

    return process_code_line(global_context, re.sub(CODE_USE_VARIABLE_RE.pattern, calc_val, line), snapshot)


class Context(LineBase):
    variables: List[Variable] = []
    code_lines: List[str] = []

    def __init__(self, global_context: GlobalContext, name: str):
        super().__init__(global_context)
        self.variables = []
        self.code_lines = []
        self.name = name

    def append_variable(self, variable: Variable):
        self.variables.append(variable)

    def append_code(self, line: CodeLine):
        self.code_lines.append(line.code)

    def snapshots(self, from_snap: dict):
        if len(self.variables) == 0:
            yield from_snap
            return
        indexes = [0] * len(self.variables)

        while True:
            for i, variable in reversed(list(enumerate(self.variables))):
                if indexes[i] >= len(variable.values):
                    if i == 0:
                        return

                    indexes[i] = 0
                    indexes[i - 1] += 1

            d = from_snap.copy()
            for i, variable in enumerate(self.variables):
                d[variable.name] = variable.values[indexes[i]]

            indexes[-1] += 1
            yield d

    def compile(self, global_snapshot: dict):
        snapshots = self.snapshots(global_snapshot)

        text = f"\n// Context '{self.name}'\n"

        for snapshot in snapshots:
            text += f"// Snapshot: {snapshot}\n"
            compiled = []
            for line in self.code_lines:
                processed = process_code_line(self.global_context, line, snapshot)
                compiled.append(processed)

            for line in compiled:
                text += f'{line}\n'

        return text


GLOBAL_VAR_RE = re.compile('^#GLOBALVAR (?P<name>[a-zA-Z0-9_]+) (?P<values>.*)$')
VAR_RE = re.compile('^#VAR (?P<name>[a-zA-Z0-9_]+) (?P<values>.*)$')

CONTEXT_RE = re.compile('^#CONTEXT (?P<name>[a-zA-Z0-9_]+)$')
END_CONTEXT_RE = re.compile('^#ENDCONTEXT$')


def parse_line(line: str, global_context: GlobalContext) -> Optional[LineBase]:
    if line.startswith('//') or line == '':
        return None

    if line.startswith('#'):
        if GLOBAL_VAR_RE.match(line):
            m = GLOBAL_VAR_RE.match(line)
            return GlobalVariable(global_context, m.group('name'), m.group('values'))

        if VAR_RE.match(line):
            m = VAR_RE.match(line)
            return Variable(global_context, m.group('name'), m.group('values'))

        if CONTEXT_RE.match(line):
            m = CONTEXT_RE.match(line)
            return Context(global_context, m.group('name'))

        if END_CONTEXT_RE.match(line):
            return EndContext(global_context)

    return CodeLine(global_context, line)


def process_parsed_line(global_context: GlobalContext, parsed: LineBase):
    global_context.append(parsed)


def compile(text: str) -> str:
    lines = text.splitlines(False)

    global_context = GlobalContext()

    parsed_lines = []
    for line in lines:
        parsed = parse_line(line, global_context)
        parsed_lines.append(parsed)

    for parsed in parsed_lines:
        if parsed is None:
            continue
        process_parsed_line(global_context, parsed)

    return global_context.compile()


def main():
    with open('program3.mrkp') as file:
        text = file.read()
        result = compile(text)

    with open('output3.mrk', 'w') as file:
        file.write(result)
        file.flush()


if __name__ == '__main__':
    main()
