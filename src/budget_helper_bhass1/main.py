from pathlib import Path
import click

from expensecategorizer import ExpenseCategorizer
import util


@click.command()
@click.argument('category_map', type=click.Path(exists=True), nargs=1)
@click.argument('bank_files', type=click.Path(exists=True), nargs=-1)
@click.argument('output', type=click.Path(
                                dir_okay=False,
                                writable=True,
                                path_type=Path
                                ), nargs=1)
def main(category_map, bank_files, output):
  """A CLI to help categorize exported expense databases from your bank"""

  util.set_log_level()

  expenseCat = ExpenseCategorizer(
        click.format_filename(category_map),
        [click.format_filename(infile) for infile in bank_files],
        output
  )

  expenseCat.one_shot()

if __name__=="__main__":
    main()

