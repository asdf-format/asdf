# -*- coding: utf-8 -*-

import re

_REGEX = re.compile('^(?P<major>(?:0|[1-9][0-9]*))'
                    '\.(?P<minor>(?:0|[1-9][0-9]*))'
                    '\.(?P<patch>(?:0|[1-9][0-9]*))'
                    '(\-(?P<prerelease>[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*))?'
                    '(\+(?P<build>[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*))?$')

if not hasattr(__builtins__, 'cmp'):
    cmp = lambda a, b: (a > b) - (a < b)


def parse(version):
    """
    Parse version to major, minor, patch, pre-release, build parts.
    """
    match = _REGEX.match(version)
    if match is None:
        raise ValueError('%s is not valid SemVer string' % version)

    verinfo = match.groupdict()

    verinfo['major'] = int(verinfo['major'])
    verinfo['minor'] = int(verinfo['minor'])
    verinfo['patch'] = int(verinfo['patch'])

    return verinfo


def compare(ver1, ver2):
    def nat_cmp(a, b):
        a, b = a or '', b or ''
        convert = lambda text: int(text) if text.isdigit() else text.lower()
        alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
        return cmp(alphanum_key(a), alphanum_key(b))

    def compare_by_keys(d1, d2):
        for key in ['major', 'minor', 'patch']:
            v = cmp(d1.get(key), d2.get(key))
            if v:
                return v
        rc1, rc2 = d1.get('prerelease'), d2.get('prerelease')
        rccmp = nat_cmp(rc1, rc2)
        if not (rc1 or rc2):
            return rccmp
        if not rc1:
            return 1
        elif not rc2:
            return -1
        return rccmp or 0

    v1, v2 = parse(ver1), parse(ver2)

    return compare_by_keys(v1, v2)


def match(version, match_expr):
    prefix = match_expr[:2]
    if prefix in ('>=', '<=', '=='):
        match_version = match_expr[2:]
    elif prefix and prefix[0] in ('>', '<', '='):
        prefix = prefix[0]
        match_version = match_expr[1:]
    else:
        raise ValueError("match_expr parameter should be in format <op><ver>, "
                         "where <op> is one of ['<', '>', '==', '<=', '>=']. "
                         "You provided: %r" % match_expr)

    possibilities_dict = {
        '>': (1,),
        '<': (-1,),
        '==': (0,),
        '>=': (0, 1),
        '<=': (-1, 0)
    }

    possibilities = possibilities_dict[prefix]
    cmp_res = compare(version, match_version)

    return cmp_res in possibilities


def max_ver(ver1, ver2):
    cmp_res = compare(ver1, ver2)
    if cmp_res == 0 or cmp_res == 1:
        return ver1
    else:
        return ver2


def min_ver(ver1, ver2):
    cmp_res = compare(ver1, ver2)
    if cmp_res == 0 or cmp_res == -1:
        return ver1
    else:
        return ver2


def format_version(major, minor, patch, prerelease=None, build=None):
    version = "%d.%d.%d" % (major, minor, patch)
    if prerelease is not None:
        version = version + "-%s" % prerelease

    if build is not None:
        version = version + "+%s" % build

    return version

def bump_major(version):
    verinfo = parse(version)
    return format_version(verinfo['major'] + 1, 0, 0)

def bump_minor(version):
    verinfo = parse(version)
    return format_version(verinfo['major'], verinfo['minor'] + 1, 0)

def bump_patch(version):
    verinfo = parse(version)
    return format_version(verinfo['major'], verinfo['minor'], verinfo['patch'] + 1)
