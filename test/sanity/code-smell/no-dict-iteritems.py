#!/usr/bin/env python

import os
import re
import sys


def main():
    skip = set([
        'test/sanity/code-smell/%s' % os.path.basename(__file__),
        'lib/ansible/module_utils/six/__init__.py',
    ])

    for path in sys.argv[1:]:
        if path in skip:
            continue

        with open(path, 'r') as path_fd:
            for line, text in enumerate(path_fd.readlines()):
                match = re.search(r'(?<! six)\.(iteritems)', text)

                if match:
                    print('%s:%d:%d: use `dict.items` or `ansible.module_utils.six.iteritems` instead of `dict.iteritems`' % (
                        path, line + 1, match.start(1) + 1))


if __name__ == '__main__':
    main()
