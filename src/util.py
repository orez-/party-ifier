import contextlib
import itertools

def zip_duration(*args):
    iters = [iter(iterable) for iterable, _ in args]
    keyfns = [keyfn for _, keyfn in args]
    with contextlib.suppress(StopIteration):
        values = [next(i) for i in iters]
        keys = [keyfn(value) for keyfn, value in zip(keyfns, values)]

        while True:
            duration = min(keys)
            yield tuple(values), duration
            for i, key in enumerate(keys):
                if key == duration:
                    values[i] = next(iters[i])
                    keys[i] = keyfns[i](values[i])
                else:
                    keys[i] -= duration


def ncycles(iterable, n):
    "Returns the sequence elements n times"
    return itertools.chain.from_iterable(itertools.repeat(tuple(iterable), n))


if __name__ == '__main__':
    print('\n'.join(map(str,
        zip_duration(
            ("abcdef", lambda e: ord(e) - ord('a') + 1),
            ("fedcba", lambda e: ord(e) - ord('a') + 1)
        )
    )))

    # abbcccddddeeeeeffffff
    # ffffffeeeeeddddcccbba
    # 1 2  3   41   4  3 21
