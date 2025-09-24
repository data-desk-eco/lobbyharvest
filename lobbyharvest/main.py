import csv
import json
from pathlib import Path

import click

from src.scrapers.fara import scrape_fara


@click.group()
def cli():
    pass


@cli.command()
@click.argument('firm_name')
@click.option('--output', '-o', default='output.csv', help='Output file path')
@click.option('--format', '-f', type=click.Choice(['csv', 'json']), default='csv', help='Output format')
def fara(firm_name, output, format):
    click.echo(f"Scraping FARA data for: {firm_name}")

    try:
        results = scrape_fara(firm_name)

        if not results:
            click.echo(f"No results found for {firm_name}")
            return

        click.echo(f"Found {len(results)} client records")

        if format == 'csv':
            with open(output, 'w', newline='') as f:
                if results:
                    fieldnames = ['firm_name', 'firm_registration_number', 'client_name',
                                  'client_country', 'start_date', 'end_date']
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(results)
        else:
            with open(output, 'w') as f:
                json.dump(results, f, indent=2, default=str)

        click.echo(f"Results saved to {output}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.ClickException(str(e))


def main():
    cli()


if __name__ == "__main__":
    main()