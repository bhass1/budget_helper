import click
import logging
from pathlib import Path

from expensecategorizer import ExpenseCategorizer
import util


@click.command()
@click.argument('category_map', type=click.Path(exists=True), nargs=1)
@click.argument('source_map', type=click.Path(exists=True), nargs=1)
@click.argument('bank_files', type=click.Path(exists=True), nargs=-1)
@click.option('--merge-file', type=click.Path(exists=True, dir_okay=False,
                                             path_type=Path),
              default=None, help='Existing workbook to merge month data into.')
@click.option('--output', type=click.Path(
                                dir_okay=False,
                                writable=True,
                                path_type=Path
                                ), default=None,
              help='Output xlsx file to write fresh month sheets to.')
def main(category_map, source_map, bank_files, merge_file, output):
  """A CLI to help categorize exported expense databases from your bank

  Either --merge-file or --output must be provided (but not both).
  """

  try:
    util.set_log_level()

    if merge_file is not None and output is not None:
      raise click.UsageError('Cannot provide both --merge-file and --output.')
    if merge_file is None and output is None:
      raise click.UsageError('Either --merge-file or --output is required.')

    expenseCat = ExpenseCategorizer(
          click.format_filename(category_map),
          click.format_filename(source_map),
          [click.format_filename(infile) for infile in bank_files],
          output,
          merge_file=merge_file
    )

    expenseCat.one_shot()
  finally:
    logging.shutdown()

if __name__=="__main__":
    main()