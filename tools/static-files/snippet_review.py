#!/usr/bin/env python3
"""snippet_review.py PUBLISHED NEW: what a new copy of a privileged list changes.

The parsing follows the browser's own code in this series, so the verdicts
"runs", "dropped" and "rejected" describe what the browser does with a rule:

  FlatbufferConverter::ConvertFilter, FilterClassifier::Classify,
  SnippetFilter::FromString, DomainOption::FromString,
  SnippetTokenizer::Tokenize (eyeo-133.0.6943.49-base.patch) and
  FlatbufferSerializer::SerializeSnippetFilter (Eyeo-Adblock-for-Cromite.patch).

After the counts and the added rules that do not run, it prints in full every
removed snippet rule (with what it did in the published copy) and every added
rule that runs (with its domains and snippet names): the changes that alter
what runs on pages.

Every added rule still has to be read by a person. Exit status 1 means: stop,
do not publish (a self-check failed, or the new copy adds a header filter).

  python3 snippet_review.py --self-test   runs only the self-checks
"""
import sys

# kAllowedSnippets and kAllowedPropertyReadValues in
# components/adblock/core/converter/serializer/flatbuffer_serializer.cc.
# Compared case-insensitively, as base::EqualsCaseInsensitiveASCII does.
ALLOWED_SNIPPETS = {s.lower() for s in (
    "log", "debug", "trace", "race", "hide-if-classifies", "hide-if-contains",
    "hide-if-contains-image", "hide-if-contains-similar-text",
    "hide-if-contains-visible-text", "hide-if-contains-and-matches-style",
    "hide-if-has-and-matches-style", "hide-if-labelled-by",
    "hide-if-matches-xpath", "hide-if-matches-xpath3",
    "hide-if-matches-computed-xpath", "hide-if-shadow-contains",
    "abort-current-inline-script", "abort-on-property-read",
    "abort-on-property-write", "abort-on-iframe-property-read",
    "abort-on-iframe-property-write", "cookie-remover", "freeze-element",
    "json-prune", "override-property-read", "prevent-listener", "skip-video")}
ALLOWED_PROPERTY_READ_VALUES = {s.lower() for s in (
    "false", "true", "null", "noopFunc", "trueFunc", "falseFunc",
    "emptyArray", "emptyObj", "undefined", "0", "1")}
ASCII_WHITESPACE = " \t\n\v\f\r"


def tokenize(text):
    """SnippetTokenizer::Tokenize: a list of calls, each a list of strings."""
    script, token, arguments = [], [], []
    escape = quotes_just_closed = within_quotes = False

    def add_argument():
        nonlocal token
        if quotes_just_closed or token:
            arguments.append("".join(token))
            token = []

    def add_function_call():
        nonlocal arguments
        # A call is dropped if empty, or if a quote or an escape is unfinished.
        if not arguments or within_quotes or escape:
            return
        script.append(arguments)
        arguments = []

    for ch in text:
        if escape:
            token.append({"r": "\r", "n": "\n", "t": "\t", "u": "\\u"}.get(ch, ch))
            escape = False
            quotes_just_closed = False
        elif ch == "\\":
            escape = True
            quotes_just_closed = False
        elif ch == "'":
            within_quotes = not within_quotes
            quotes_just_closed = not within_quotes
        elif within_quotes or (ch != ";" and ch not in ASCII_WHITESPACE):
            token.append(ch)
            quotes_just_closed = False
        else:
            add_argument()
            if ch == ";":
                add_function_call()
            quotes_just_closed = False
    add_argument()
    add_function_call()
    return script


def include_domains(domain_list):
    """DomainOption::FromString plus RemoveDomainsWithNoSubdomain."""
    valid = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-.")
    out = set()
    for d in domain_list.lower().split(","):
        d = d.strip(ASCII_WHITESPACE).rstrip(".").rstrip("*")
        if not d or d.startswith("~"):
            continue
        if not set(d) <= valid or ".." in d:
            continue
        if d == "localhost" or "." in d:
            out.add(d)
    return out


def classify(line):
    """Returns None for a line that is not a snippet rule, else
    (verdict, reason, include_domains)."""
    f = line.strip(ASCII_WHITESPACE)
    if not f or f.startswith("!"):
        return None
    pos = f.find("#")
    if pos < 0 or not f[pos:].startswith("#$#"):
        return None
    domains = include_domains(f[:pos])
    snippet = f[pos + 3:]
    if not snippet:
        return ("rejected", "no snippet script", domains)
    if not domains:
        return ("rejected", "no include domain with a subdomain", domains)
    script = tokenize(snippet)
    if not script:
        return ("rejected", "tokenizer returned no call", domains)
    for call in script:
        if call[0].lower() not in ALLOWED_SNIPPETS:
            return ("dropped", "snippet not allowed: " + call[0], domains)
        if call[0].lower() == "override-property-read":
            for value in call[2:]:
                if value.lower() not in ALLOWED_PROPERTY_READ_VALUES:
                    return ("dropped", "override-property-read value: " + value,
                            domains)
    return ("runs", ", ".join(c[0] for c in script), domains)


def self_test():
    checks = [
        # Counterexample: single quotes are delimiters.
        (tokenize("'cookie-remover' foo"), [["cookie-remover", "foo"]]),
        (classify("example.com#$#'cookie-remover' foo")[0], "runs"),
        # A quoted ';' stays inside its argument; ';' outside splits calls.
        (tokenize("json-prune 'a;b' ; skip-video x"),
         [["json-prune", "a;b"], ["skip-video", "x"]]),
        # Double quotes are ordinary characters.
        (tokenize('log "a b"'), [["log", '"a', 'b"']]),
        # Escapes: \n becomes a newline, \' a literal quote, \u stays "\u".
        (tokenize("log a\\nb \\'x \\u1"), [["log", "a\nb", "'x", "\\u1"]]),
        # Empty quotes give an empty argument.
        (tokenize("log ''"), [["log", ""]]),
        # An unfinished quote or escape drops the last call.
        (tokenize("log 'abc"), []),
        (tokenize("log a\\"), []),
        (tokenize("log a; trace 'b"), [["log", "a"]]),
        # Names compare case-insensitively.
        (classify("example.com#$#Cookie-Remover x")[0], "runs"),
        (classify("example.com#$#simulate-mouse-event x")[0], "dropped"),
        (classify("example.com#$#log a; replace-outbound-value b")[0], "dropped"),
        (classify("example.com#$#override-property-read a NOOPFUNC")[0], "runs"),
        (classify("example.com#$#override-property-read a 42")[0], "dropped"),
        # Snippet rules need an include domain with a dot (or localhost).
        (classify("#$#log a")[0], "rejected"),
        (classify("~example.com#$#log a")[0], "rejected"),
        (classify("com#$#log a")[0], "rejected"),
        (classify("example.*#$#log a")[0], "runs"),
        # Element hiding and comments are not snippet rules.
        (classify("example.com##.ad"), None),
        (classify("! example.com#$#log a"), None),
    ]
    failed = [i for i, (got, want) in enumerate(checks) if got != want]
    for i in failed:
        print(f"SELF-CHECK {i} FAILED: got {checks[i][0]!r}, want {checks[i][1]!r}")
    return not failed


def rules(text_lines):
    out = {}
    for line in text_lines:
        c = classify(line)
        if c is not None:
            out[line.strip(ASCII_WHITESPACE)] = c
    return out


def read(path):
    return open(path, encoding="utf-8", errors="replace").read().splitlines()


def review(old_lines, new_lines):
    """Compares two copies of a list. Returns (report lines, stop)."""
    out = []
    old, new = rules(old_lines), rules(new_lines)
    added = [l for l in new if l not in old]
    removed = [l for l in old if l not in new]
    out.append(f"snippet rules: {len(old)} -> {len(new)}, "
               f"added {len(added)}, removed {len(removed)}")
    counts = {"runs": 0, "dropped": 0, "rejected": 0}
    for l in added:
        verdict, reason, _ = new[l]
        counts[verdict] += 1
        if verdict != "runs":
            out.append(f"{verdict.upper()} ({reason}): {l[:200]}")
    out.append("added rules that run: {runs}, dropped by the serializer: "
               "{dropped}, rejected by the parser: {rejected}".format(**counts))
    stop = False
    old_set = {l.strip(ASCII_WHITESPACE) for l in old_lines}
    new_set = {l.strip(ASCII_WHITESPACE) for l in new_lines}
    for l in sorted(new_set - old_set):
        if not l.startswith("!") and ("$header=" in l or ",header=" in l):
            out.append(f"NEW HEADER FILTER (privileged): {l[:200]}")
            stop = True
    old_domains = {d for v in old.values() if v[0] == "runs" for d in v[2]}
    first = sorted({d for l in added if new[l][0] == "runs" for d in new[l][2]}
                   - old_domains)
    out.append(f"domains that get running snippets for the first time "
               f"({len(first)}): " + " ".join(first[:200]))
    # The executable changes, in full: what stops running and what starts.
    out.append(f"== removed snippet rules ({len(removed)}) ==")
    for l in removed:
        out.append(f"REMOVED (was {old[l][0]}): {l}")
    running = [l for l in added if new[l][0] == "runs"]
    out.append(f"== added snippet rules that run ({len(running)}) ==")
    for l in running:
        _, names, domains = new[l]
        out.append(f"RUNS [domains: {', '.join(sorted(domains))}] "
                   f"[snippets: {names}]: {l}")
    return out, stop


def self_test_review():
    old = ["a.example#$#log x", "b.example#$#log y", "! comment"]
    new = ["a.example#$#log x",
           "c.example,d.example#$#cookie-remover z; skip-video v",
           "e.example#$#simulate-mouse-event q"]
    out, stop = review(old, new)
    checks = [
        (out[0], "snippet rules: 2 -> 3, added 2, removed 1"),
        ("== removed snippet rules (1) ==" in out, True),
        ("REMOVED (was runs): b.example#$#log y" in out, True),
        ("== added snippet rules that run (1) ==" in out, True),
        ("RUNS [domains: c.example, d.example] [snippets: cookie-remover, "
         "skip-video]: c.example,d.example#$#cookie-remover z; skip-video v"
         in out, True),
        # A dropped rule is reported as before, not as running.
        (any(l.startswith("RUNS") and "simulate-mouse-event" in l
             for l in out), False),
        (any(l.startswith("DROPPED (snippet not allowed: simulate-mouse-event)")
             for l in out), True),
        (stop, False),
        # A new header filter still stops.
        (review(old, old + ["||x.example^$header=via=1"])[1], True),
        (review(old, old)[0][-1], "== added snippet rules that run (0) =="),
    ]
    failed = [i for i, (got, want) in enumerate(checks) if got != want]
    for i in failed:
        print(f"REVIEW SELF-CHECK {i} FAILED: got {checks[i][0]!r}, "
              f"want {checks[i][1]!r}")
    return not failed


def main():
    if not (self_test() and self_test_review()):
        sys.exit(1)
    if sys.argv[1:] == ["--self-test"]:
        print("self-checks passed")
        return
    out, stop = review(read(sys.argv[1]), read(sys.argv[2]))
    print("\n".join(out))
    sys.exit(1 if stop else 0)


if __name__ == "__main__":
    main()
