#!/usr/bin/python
"""A script that helps with the parsing and composing of the glossary."""
from argparse import ArgumentParser
from itertools import takewhile
from functools import reduce
from re import compile as re_compile, Pattern
from sys import stderr, exit as sys_exit
from typing import List, Dict
from pprint import pprint
from subprocess import check_call
from tempfile import mkstemp

_RE_TAG: Pattern = re_compile(r"(?P<header>#{3,4}) (?P<content>[\w ]+)")
_RE_TEMPLATED: Pattern = re_compile(r"^ (?P<header>\w+)\?\n(?P<content>.+)\n*")

Glossary = Dict[str, List[str]]

# Core API

def parse_term(source: str) -> Glossary:
    assert source.strip()

    line, raw = source.split("\n", maxsplit=1)
    sliced = raw.rstrip().split("\n")

    match = _RE_TAG.fullmatch(line)
    assert match is not None, (repr(match), line)

    header, name = match.groups()
    assert len(header) == 3, f"Invalid header length for entry: {line!r}"

    body = sliced[: sliced.index("***")]

    synonyms = [
        _RE_TAG.fullmatch(line)["content"]
        for line in takewhile((lambda line: line[:5] == "#### "), body)
    ]

    return {name: {"synonyms": synonyms, "content": "\n".join(body[len(synonyms) :])}}


def load_glossary(filename: str) -> Glossary:
    """Parse some glossary."""
    collected: Dict[int, str] = {}
    cursor = None

    with open(filename) as file:
        stream = map(str.rstrip, file)

        # Skip ahed to the actual terms.
        for line in stream:
            if line == "## [Terms](#Index)":
                break

        for index, line in enumerate(stream):
            if len(line) >= 80:
                print(f"Ln:{index!r} is over 80 characters.", file=stderr)

            if line[:4] == "### ":
                if cursor in collected:
                    collected[cursor] = collected[cursor].rstrip()

                cursor = index
                collected[index] = f"{line!s}\n"
            elif cursor is not None:
                collected[cursor] += f"{line!s}\n"

    return reduce(
        (lambda x, y: {**x, **y}),
        map(parse_term, collected.values()),
    )


def dump_glossary(filename: str, glossary: Glossary) -> str:
    fmt = "\n".join([
        (entry := glossary[key])
        and (
            f"### {key}\n"
            + "".join(f"#### {synonym}\n" for synonym in entry["synonyms"])
            + f"{entry['content']}\n"
            + "***\n"
        )
        for key in sorted(glossary)
    ])

    with open(filename, "r+") as file:
        while True:
            if file.readline().rstrip() == "## [Terms](#Index)":
                file.seek(file.tell() + 1)
                break

        file.truncate()
        file.write(fmt)


# Action handlers


def _report(glossary: Glossary) -> bool:
    print(f"Summary: There are {len(glossary)} terms in the glossary.")
    return False

def _format(glossary: Glossary) -> bool:
    return True

TEMPLATE = """
# Name?
TEXT

# Desc?
TEXT
""".strip()

def _add(glossary: Glossary) -> bool:
    fd, filename = mkstemp(suffix=".tmp")

    with open(fd, "w+") as inf:
        inf.write(TEMPLATE)

    check_call(f"$EDITOR {filename}", shell=True)

    with open(filename) as inf:
        raw = inf.read()

    if not raw.startswith("\n"):
        raw = "\n" + raw

    body = raw.split("\n#")
    matches = list(filter(None, [_RE_TEMPLATED.fullmatch(part) for part in body]))

    results = {
        match["header"].lower(): match["content"].strip()
        for match in matches
    }


    if results["name"] == "TEXT":
        print("Skipping add, no changes appear to have been made...", file=stderr)
        return False

    if "desc" not in results:
        _, end = next(filter((lambda m: m["header"].lower() == "name"), matches)).span()
        desc = re_compile(r"\n?# Desc\?\n?").sub(" ", raw[end + 1:])
        results["desc"] = desc.strip()

    glossary[results["name"]] = {
        "synonyms": [],
        "content": f"\n{results['desc']}\n"
    }

    return True

ACTIONS = {
    "report": _report,
    "fmt": _format,
    "add": _add,
}


def main():
    """Composer entry point."""
    parser = ArgumentParser()
    parser.add_argument("action", nargs="?", default="report", choices=ACTIONS)
    parser.add_argument("--file", default="README.md")
    args = parser.parse_args()

    action = args.action
    glossary = load_glossary(args.file)

    should_dump = ACTIONS[args.action](glossary)

    if should_dump:
        dump_glossary(args.file, glossary)


if __name__ == "__main__":
    main()
