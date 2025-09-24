import click
import csv
import json
from pathlib import Path
from typing import List, Dict
from src.scrapers import australia_lobbying


@click.group()
def cli():
    """Lobbyharvest CLI tool for aggregating lobbying firm client data"""
    pass


@cli.command()
@click.option('--firm', '-f', required=True, help='Name of the lobbying firm to search for')
@click.option('--output', '-o', type=click.Choice(['json', 'csv']), default='json', help='Output format')
@click.option('--output-file', '-of', type=click.Path(), help='Output file path')
def australia(firm, output, output_file):
    """Scrape Australian Lobbying Register for firm client data"""
    click.echo(f"Searching Australian Lobbying Register for: {firm}")

    results = australia_lobbying.scrape(firm)

    if not results:
        click.echo("No results found.")
        return

    click.echo(f"Found {len(results)} client records")

    if output == 'json':
        output_data = json.dumps(results, indent=2)
        if output_file:
            Path(output_file).write_text(output_data)
            click.echo(f"Results saved to {output_file}")
        else:
            click.echo(output_data)
    else:
        if output_file:
            with open(output_file, 'w', newline='') as f:
                if results:
                    writer = csv.DictWriter(f, fieldnames=results[0].keys())
                    writer.writeheader()
                    writer.writerows(results)
            click.echo(f"Results saved to {output_file}")
        else:
            if results:
                keys = results[0].keys()
                click.echo(','.join(keys))
                for result in results:
                    click.echo(','.join(str(result.get(k, '')) for k in keys))


def main():
    cli()


if __name__ == "__main__":
    main()
