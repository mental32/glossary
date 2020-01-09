#!/usr/bin/python
"""A script that helps with the parsing and composing of the glossary."""
from argparse import ArgumentParser
from itertools import takewhile
from re import compile as re_compile, Pattern
from sys import stderr, exit as sys_exit
from typing import List, Dict
from pprint import pprint

_RE_TAG: Pattern = re_compile(r"(?P<header>#{3,4}) (?P<content>[\w ]+)")

Glossary = Dict[str, List[str]]

# Core API


def load_glossary(filename: str) -> Glossary:
    """Parse some glossary."""
    collected: List[str] = []
    positions: List[int] = []

    with open(filename) as file:
        stream = map(str.rstrip, file)

        # Skip ahed to the actual terms.
        for line in stream:
            if line == "## [Terms](#Index)":
                break

        for index, line in enumerate(stream):
            if len(line) >= 80:
                print(f"Ln:{index!r} is over 80 characters.", file=stderr)

            collected.append(line)

            if line[:4] == "### ":
                positions.append(index)

    terms = {}

    for position in positions:
        line = collected[position]

        match = _RE_TAG.fullmatch(line)
        assert match is not None, (repr(match), line)

        header, name = match.groups()
        assert len(header) == 3, f"Invalid header length for entry: {line!r}"

        sliced = collected[position + 1 :]
        body = sliced[: sliced.index("***")]

        synonyms = [
            _RE_TAG.fullmatch(line)["content"]
            for line in takewhile((lambda line: line[:5] == "#### "), body)
        ]

        terms[name] = {"synonyms": synonyms, "content": "\n".join(body[len(synonyms) :])}

    return terms


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


def _report(_, glossary: Glossary) -> None:
    print(f"Summary: There are {len(glossary)} terms in the glossary.")


def _format(args, glossary: Glossary) -> None:
    # Serializing glossaries automatically formats them :D
    dump_glossary(args.file, glossary)
    print("Formatted glossary.")


ACTIONS = {
    "report": _report,
    "fmt": _format,
}


def main():
    """Composer entry point."""
    parser = ArgumentParser()
    parser.add_argument("action", nargs="?", default="report", choices=ACTIONS)
    parser.add_argument("--file", default="README.md")
    args = parser.parse_args()

    action = args.action
    glossary = load_glossary(args.file)

    ACTIONS[args.action](args, glossary)


if __name__ == "__main__":
    main()
