import os


def markov(inp: str):
    with os.popen(f'echo "{inp}\n" | python3 markov.py') as stream:
        return stream.read().splitlines()[-1]


for i in range(1000):
    inp = hex(i)[2:]
    expected = hex(i-1)[2:]
    result = markov(inp)

    if result != expected:
        print(f'{inp=} {expected=} {result=}')
    else:
        print(f'GOOD {inp=} {result=}')
