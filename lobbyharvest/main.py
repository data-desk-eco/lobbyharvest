import click
import csv
import json
from typing import Optional
from src.scrapers import uk_lobbying


@click.group()
def cli():
    pass


@cli.command()
@click.argument('firm_name')
@click.option('--format', '-f', type=click.Choice(['json', 'csv']), default='json', help='Output format')
@click.option('--output', '-o', type=click.Path(), help='Output file path')
def uk_lobbying_register(firm_name: str, format: str, output: Optional[str]):
    click.echo(f"Searching UK Lobbying Register for: {firm_name}")

    results = uk_lobbying.scrape(firm_name)

    if not results:
        click.echo("No results found")
        return

    if format == 'json':
        output_data = json.dumps(results, indent=2)
        if output:
            with open(output, 'w') as f:
                f.write(output_data)
            click.echo(f"Results saved to {output}")
        else:
            click.echo(output_data)
    else:
        fieldnames = ['firm_name', 'firm_registration_number', 'client_name',
                      'client_registration_number', 'start_date', 'end_date']

        if output:
            with open(output, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(results)
            click.echo(f"Results saved to {output}")
        else:
            import sys
            writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)


if __name__ == "__main__":
    cli()
