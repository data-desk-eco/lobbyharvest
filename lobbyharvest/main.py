import click
import csv
import json
from pathlib import Path
from typing import Optional, List, Dict
from src.scrapers import lobbyfacts, uk_lobbying, australia_lobbying


@click.group()
def cli():
    """Lobbyharvest CLI tool for aggregating lobbying firm client data"""
    pass


@cli.command()
@click.option('--firm-name', '-f', required=True, help='Name of the lobbying firm (e.g. "FTI Consulting Belgium")')
@click.option('--url', '-u', help='Direct URL to the firm\'s Lobbyfacts page')
@click.option('--output', '-o', default='output.csv', help='Output file path (default: output.csv)')
@click.option('--format', type=click.Choice(['csv', 'json']), default='csv', help='Output format')
def lobbyfacts_scrape(firm_name, url, output, format):
    """Scrape Lobbyfacts.eu for firm client data"""
    click.echo(f"Scraping Lobbyfacts for {firm_name}...")

    clients = lobbyfacts.scrape_lobbyfacts(firm_name, url)

    if not clients:
        click.echo("No clients found.")
        return

    click.echo(f"Found {len(clients)} clients")

    if format == 'csv':
        with open(output, 'w', newline='') as f:
            if clients:
                writer = csv.DictWriter(f, fieldnames=clients[0].keys())
                writer.writeheader()
                writer.writerows(clients)
    else:
        with open(output, 'w') as f:
            json.dump(clients, f, indent=2)

    click.echo(f"Results saved to {output}")


@cli.command()
@click.argument('firm_name')
@click.option('--format', '-f', type=click.Choice(['json', 'csv']), default='json', help='Output format')
@click.option('--output', '-o', type=click.Path(), help='Output file path')
def uk_lobbying_register(firm_name: str, format: str, output: Optional[str]):
    """Scrape UK Lobbying Register for firm client data"""
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
    cli()