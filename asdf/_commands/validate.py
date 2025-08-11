"""
Commands for validating ASDF files
"""

import asdf

from .main import Command

__all__ = ["validate"]


class Validate(Command):
    @classmethod
    def setup_arguments(cls, subparsers):
        parser = subparsers.add_parser(
            "validate",
            help="Validates an ASDF file.",
            description="validates \n - against all tagged schemas (and optionally a custom schema) \n - blocks with stored checksums (can be disabled)",
        )

        parser.add_argument("filename", help="ASDF file to validate")
        parser.add_argument(
            "--custom_schema",
            type=str,
            help="URI or filename for custom schema to use during validation.",
        )
        parser.add_argument(
            "--skip_checksums",
            default=False,
            action="store_true",
            help="Skip block checksum validation.",
        )
        parser.set_defaults(func=cls.run)

        return parser

    @classmethod
    def run(cls, args):
        validate(args.filename, args.custom_schema, args.skip_checksums)


def validate(filename, custom_schema, skip_checksums):
    # if we are skipping checksums we can lazy load, otherwise don't
    with asdf.open(
        filename, custom_schema=custom_schema, validate_checksums=not skip_checksums, lazy_load=skip_checksums
    ) as af:  # noqa: F841
        msg = f"{filename} is valid"
        if custom_schema:
            msg += f", conforms to {custom_schema}"
        if not skip_checksums:
            msg += ", and block checksums match"
        print(msg)
